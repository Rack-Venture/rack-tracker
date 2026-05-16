from __future__ import annotations

import asyncio
import json
import os
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from config import (
    DEFAULT_MODEL_ASSET_PATH,
    DEFAULT_MODEL_VARIANT,
    BENCHMARK_DIR,
    EXTRACTED_FRAME_DIR,
    MODEL_ASSET_PATHS,
    PRESET_ESTIMATION_DIR,
    SKELETON_DIR,
    UPLOAD_DIR,
)
from schema.frame import FrameChunk, FrameExtractionOptions, FrameExtractionResult
from schema.job import JobCreateResponse, JobProgress, JobStatusResponse
from schema.pose import PoseChunk, PoseFrameResult, PoseLandmarkPoint, PoseInferenceOptions, PoseInferenceResult
from schema.result import (
    AnalysisResult,
    AnalysisSummary,
    LlmFeedbackResult,
    MotionAnalysisResult,
    MotionAnalysisSummary,
    SkeletonPageResponse,
)
from service.analysis_pipeline import AnalysisPipelineService
from service.benchmarking import BenchmarkService, PoseChunkBenchmarkCollector
from service.llm_feedback import LlmFeedbackService
from service.pose_inference import PoseInferenceService
from service.skeleton_mapper import SkeletonMapperService
from service.video_reader import VideoReaderService

VALID_MODEL_VARIANTS = {"lite", "full", "heavy"}
VALID_DELEGATES = {"CPU", "GPU"}
VALID_BAR_PLACEMENT_MODES = {"auto", "high_bar", "low_bar"}
PIPELINE_QUEUE_DONE = object()


def _env_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    parsed = int(raw_value)
    if parsed < 1:
        raise ValueError(f"{name} must be >= 1.")
    return parsed


FRAME_CHUNK_SIZE = _env_positive_int("STREAMING_FRAME_CHUNK_SIZE", 32)
FRAME_CHUNK_QUEUE_MAXSIZE = _env_positive_int("STREAMING_FRAME_QUEUE_MAXSIZE", 2)
POSE_CHUNK_QUEUE_MAXSIZE = _env_positive_int("STREAMING_POSE_QUEUE_MAXSIZE", 2)
COLLECTOR_QUEUE_MAXSIZE = _env_positive_int("STREAMING_COLLECTOR_QUEUE_MAXSIZE", 2)


@dataclass
class JobRecord:
    job_id: str
    status: str
    progress: JobProgress | None = None
    error: dict[str, Any] | None = None
    result: MotionAnalysisResult | None = None
    benchmark: dict[str, Any] | None = None
    benchmark_frame_metrics: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    skeleton_path: str | None = None
    _pipeline_ctx: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StreamingPipelineArtifacts:
    extraction_result: FrameExtractionResult
    inference_result: PoseInferenceResult
    skeleton: dict[str, Any]
    skeleton_summary: dict[str, Any]
    processed_frame_count: int
    detected_frame_count: int
    frame_extraction_ms: float
    startup_summary: dict[str, Any]
    pipeline_summary: dict[str, Any]
    benchmark_frame_metrics_path: str | None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._video_reader = VideoReaderService()
        self._skeleton_mapper = SkeletonMapperService()
        self._analysis_pipeline = AnalysisPipelineService()
        self._llm_feedback = LlmFeedbackService()
        self._benchmark_service = BenchmarkService()
        self._sse_queues: dict[str, list[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    async def create_job(
        self,
        filename: str,
        source_path: str,
        requested_sampling_fps: float | None,
        exercise_type: str | None,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
        bar_placement_mode: str | None,
        model_asset_path: str | None = None,
        model_variant: str | None = None,
        delegate: str | None = None,
        preset_estimation_id: str | None = None,
    ) -> JobCreateResponse:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        job_id = f"job_{uuid4().hex[:8]}"
        metadata = self._build_metadata(
            filename=filename,
            source_path=source_path,
            requested_sampling_fps=requested_sampling_fps,
            exercise_type=exercise_type,
            bodyweight_kg=bodyweight_kg,
            external_load_kg=external_load_kg,
            bar_placement_mode=bar_placement_mode,
            model_asset_path=model_asset_path,
            model_variant=model_variant,
            delegate=delegate,
        )
        if preset_estimation_id is not None:
            metadata["sourceType"] = "preset_estimation"
            metadata["presetEstimationId"] = preset_estimation_id
        # Validate user-provided inference overrides before enqueuing the job.
        # Preset mode skips inference, so validation is only needed for video mode.
        if preset_estimation_id is None:
            self._build_inference_options_from_metadata(metadata)
        progress = JobProgress(
            stage="queued",
            currentStep=0,
            totalSteps=6,
            ratio=0.0,
        )
        result = self._build_initial_result(metadata)
        self._jobs[job_id] = JobRecord(
            job_id=job_id,
            status="queued",
            progress=progress,
            result=result,
            metadata=metadata,
        )
        asyncio.create_task(self._run_job(job_id))
        return JobCreateResponse(jobId=job_id, status="queued", videoPath=source_path)

    async def preview(
        self,
        filename: str,
        source_path: str,
        requested_sampling_fps: float | None,
        exercise_type: str | None,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
        bar_placement_mode: str | None,
        model_asset_path: str | None = None,
        model_variant: str | None = None,
        delegate: str | None = None,
    ) -> MotionAnalysisSummary:
        metadata = self._build_metadata(
            filename=filename,
            source_path=source_path,
            requested_sampling_fps=requested_sampling_fps,
            exercise_type=exercise_type,
            bodyweight_kg=bodyweight_kg,
            external_load_kg=external_load_kg,
            bar_placement_mode=bar_placement_mode,
            model_asset_path=model_asset_path,
            model_variant=model_variant,
            delegate=delegate,
        )
        self._build_inference_options_from_metadata(metadata)
        preview_id = f"preview_{uuid4().hex[:8]}"
        preview_record = JobRecord(
            job_id=preview_id,
            status="processing",
            result=self._build_initial_result(metadata),
            metadata=metadata,
        )
        await asyncio.to_thread(self._execute_pipeline, preview_record, persist_skeleton=False)
        if preview_record.status == "failed":
            error_message = (
                str(preview_record.error.get("message"))
                if isinstance(preview_record.error, dict) and preview_record.error.get("message")
                else "Preview analysis failed."
            )
            raise HTTPException(status_code=500, detail=error_message)
        if preview_record.result is None:
            raise HTTPException(status_code=500, detail="Preview result is empty.")
        skeleton = preview_record.result.skeleton
        return MotionAnalysisSummary(
            skeleton={
                "videoInfo": skeleton.get("videoInfo", {}),
                "nextTimestampCursorMs": skeleton.get("nextTimestampCursorMs", 0),
            },
            analysis=preview_record.result.analysis,
            llmFeedback=preview_record.result.llmFeedback,
            benchmark=preview_record.result.benchmark,
        )

    def get_status(self, job_id: str) -> JobStatusResponse:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return JobStatusResponse(
            jobId=job.job_id,
            status=job.status,
            progress=job.progress,
            error=job.error,
        )

    def get_result(self, job_id: str) -> MotionAnalysisSummary:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed" or job.result is None:
            raise HTTPException(status_code=409, detail="Job result is not ready.")
        skeleton = job.result.skeleton
        return MotionAnalysisSummary(
            skeleton={
                "videoInfo": skeleton.get("videoInfo", {}),
                "nextTimestampCursorMs": skeleton.get("nextTimestampCursorMs", 0),
            },
            analysis=job.result.analysis,
            llmFeedback=job.result.llmFeedback,
            benchmark=job.result.benchmark,
        )

    def get_skeleton_page(self, job_id: str, offset: int, limit: int) -> SkeletonPageResponse:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed" or job.result is None:
            raise HTTPException(status_code=409, detail="Skeleton result is not ready.")

        skeleton = self._load_skeleton(job)
        frames = skeleton.get("frames", [])
        total_frames = len(frames)
        bounded_offset = min(offset, total_frames)
        bounded_limit = min(limit, max(total_frames - bounded_offset, 0))
        page_frames = frames[bounded_offset : bounded_offset + bounded_limit]
        next_cursor = (
            page_frames[-1].get("timestampMs", 0) + 1 if page_frames else skeleton.get("nextTimestampCursorMs", 0)
        )
        return SkeletonPageResponse(
            frames=page_frames,
            videoInfo=skeleton.get("videoInfo", {}),
            cameraBinding=skeleton.get("cameraBinding"),
            imageCoordinateSpace=skeleton.get("imageCoordinateSpace"),
            nextTimestampCursorMs=next_cursor,
            offset=bounded_offset,
            limit=bounded_limit,
            totalFrames=total_frames,
        )

    def get_skeleton_download_path(self, job_id: str) -> str:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed" or not job.skeleton_path:
            raise HTTPException(status_code=409, detail="Skeleton download is not ready.")
        return job.skeleton_path

    def load_skeleton_artifact(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is not None:
            if job.status != "completed":
                raise RuntimeError(f"Source job {job_id} is not completed.")
            return self._load_skeleton(job)

        skeleton_path = SKELETON_DIR / f"{job_id}.json"
        if skeleton_path.exists():
            return json.loads(skeleton_path.read_text(encoding="utf-8"))
        raise KeyError(job_id)

    def get_benchmark(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.benchmark is None:
            raise HTTPException(status_code=409, detail="Benchmark result is not ready.")
        return job.benchmark

    def _try_build_partial_benchmark(self, job: JobRecord) -> None:
        ctx = job._pipeline_ctx
        if not ctx.get("inference_result"):
            return
        try:
            benchmark_result = self._benchmark_service.build_result(
                benchmark_run_id=f"benchmark_{job.job_id}",
                source_video_path=str(ctx["extraction_result"].source_path),
                job_metadata=job.metadata,
                extraction_options=ctx["extraction_options"],
                extraction_result=ctx["extraction_result"],
                inference_result=ctx["inference_result"],
                analysis_result=ctx.get("analysis_result") or {},
                llm_prompt_diagnostics=ctx.get("llm_prompt_diagnostics"),
                llm_call_result=ctx.get("llm_call_metrics"),
                frame_extraction_ms=ctx["frame_extraction_ms"],
                analysis_ms=ctx.get("analysis_ms") or 0.0,
                llm_feedback_ms=ctx.get("llm_feedback_ms"),
                startup_summary=ctx.get("startup_summary"),
                pipeline_summary=ctx.get("pipeline_summary"),
                total_elapsed_ms=(perf_counter() - ctx["total_started"]) * 1000.0,
                started_at=ctx["started_at"],
                completed_at=datetime.now(timezone.utc),
                frame_metrics=ctx.get("benchmark_frame_metrics"),
                frame_metrics_path=ctx.get("benchmark_frame_metrics_path"),
            )
            job.benchmark = benchmark_result.model_dump(exclude={"frameMetrics"})
            job.benchmark_frame_metrics = []
        except Exception as e:
            import traceback
            print(f"[benchmark] partial build failed for {job.job_id}: {e}")
            traceback.print_exc()

    def get_benchmark_frame_metrics(self, job_id: str) -> list[dict[str, Any]]:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed":
            raise HTTPException(status_code=409, detail="Benchmark frame metrics are not ready.")
        storage = job.benchmark.get("storage") if isinstance(job.benchmark, dict) else None
        frame_metrics_path = storage.get("frameMetricsPath") if isinstance(storage, dict) else None
        if frame_metrics_path:
            return self._benchmark_service.load_saved_frame_metrics_payload(frame_metrics_path)
        return job.benchmark_frame_metrics

    async def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        try:
            await asyncio.to_thread(self._execute_pipeline, job, True)
        except Exception as exc:
            import traceback
            print(f"[job {job.job_id}] pipeline failed: {exc}")
            traceback.print_exc()
            self._try_build_partial_benchmark(job)
            self._fail_job(job, exc)
        finally:
            self._cleanup_transient_upload(job)

    def _execute_pipeline(self, job: JobRecord, persist_skeleton: bool) -> None:
        started_at = datetime.now(timezone.utc)
        total_started = perf_counter()
        source_type = str(job.metadata.get("sourceType") or "video")
        self._set_progress(
            job,
            "initializing_landmarker",
            1,
            6,
            0.1,
            stage_details={
                "frameChunkSize": FRAME_CHUNK_SIZE,
                "requestedDelegate": str(job.metadata.get("delegate") or ""),
                "modelVariant": str(job.metadata.get("modelVariant") or ""),
            },
        )
        inference_started = perf_counter()
        if source_type == "preset_estimation":
            streaming_artifacts = self._run_preset_pipeline(job)
            preset_path = PRESET_ESTIMATION_DIR / f"{job.metadata['presetEstimationId']}.json"
            extraction_options = FrameExtractionOptions(video_path=preset_path)
        else:
            extraction_options = self._build_extraction_options(job)
            source_path = Path(str(job.metadata["sourcePath"]))
            requested_sampling_fps = job.metadata.get("requestedSamplingFps")
            inference_options = self._build_inference_options(job)
            pose_service = PoseInferenceService()
            resolved_inference_options = inference_options or pose_service.default_options()
            extraction_started = perf_counter()
            inference_started = perf_counter()
            streaming_artifacts = self._run_streaming_pipeline(
                job=job,
                extraction_options=extraction_options,
                source_path=source_path,
                requested_sampling_fps=requested_sampling_fps,
                resolved_inference_options=resolved_inference_options,
                extraction_started=extraction_started,
            )
        extraction_result = streaming_artifacts.extraction_result
        inference_result = streaming_artifacts.inference_result
        skeleton = streaming_artifacts.skeleton
        processed_frame_count = streaming_artifacts.processed_frame_count
        frame_extraction_ms = streaming_artifacts.frame_extraction_ms
        inference_ms = (perf_counter() - inference_started) * 1000.0

        if persist_skeleton:
            job.skeleton_path = self._persist_skeleton(job.job_id, skeleton)
        job.result = MotionAnalysisResult(
            skeleton=streaming_artifacts.skeleton_summary,
            analysis=AnalysisResult(),
            llmFeedback=LlmFeedbackResult(),
            benchmark={},
        )

        # Save inference-complete context so benchmark can be built even on later failure
        job._pipeline_ctx = {
            "extraction_options": extraction_options,
            "extraction_result": extraction_result,
            "inference_result": inference_result,
            "frame_extraction_ms": frame_extraction_ms,
            "analysis_result": {},
            "analysis_ms": 0.0,
            "llm_prompt_diagnostics": None,
            "llm_call_metrics": None,
            "llm_feedback_ms": None,
            "benchmark_frame_metrics": None,
            "benchmark_frame_metrics_path": streaming_artifacts.benchmark_frame_metrics_path,
            "startup_summary": streaming_artifacts.startup_summary,
            "pipeline_summary": streaming_artifacts.pipeline_summary,
            "started_at": started_at,
            "total_started": total_started,
        }

        self._set_progress(
            job,
            "computing",
            3,
            6,
            0.6,
            {"analyzing": inference_ms},
            processed_frames=processed_frame_count,
            total_frames=processed_frame_count,
        )
        analysis_started = perf_counter()
        analysis = self._analysis_pipeline.analyze(
            skeleton,
            job.metadata.get("exerciseType"),
            job.metadata.get("bodyweightKg"),
            job.metadata.get("externalLoadKg"),
            job.metadata.get("barPlacementMode"),
        )
        analysis_ms = (perf_counter() - analysis_started) * 1000.0
        job.result.analysis = analysis
        job._pipeline_ctx["analysis_result"] = analysis
        job._pipeline_ctx["analysis_ms"] = analysis_ms

        # LLM feedback is exercise-specific; skip in general motion experiment mode
        is_general_motion = (
            isinstance(analysis, dict)
            and analysis.get("summary", {}).get("exerciseType") == "general_motion"
        )

        if is_general_motion:
            coach_prompt_payload = None
            llm_prompt_diagnostics = None
            llm_feedback = LlmFeedbackResult()
            llm_call_metrics = None
            llm_feedback_ms = 0.0
        else:
            coach_prompt_payload = self._llm_feedback.build_prompt_payload(analysis)
            llm_prompt_diagnostics = self._llm_feedback.estimate_prompt_tokens(
                analysis,
                coach_prompt_payload,
            )

            self._set_progress(
                job,
                "generating_feedback",
                4,
                6,
                0.85,
                {"computing": analysis_ms},
                processed_frames=processed_frame_count,
                total_frames=processed_frame_count,
            )
            llm_started = perf_counter()
            llm_feedback, llm_call_metrics = self._llm_feedback.generate(
                analysis,
                coach_prompt_payload,
            )
            llm_feedback_ms = (perf_counter() - llm_started) * 1000.0

        job.result.llmFeedback = llm_feedback
        job._pipeline_ctx["llm_prompt_diagnostics"] = llm_prompt_diagnostics
        job._pipeline_ctx["llm_call_metrics"] = llm_call_metrics
        job._pipeline_ctx["llm_feedback_ms"] = llm_feedback_ms

        benchmark_result = self._benchmark_service.build_result(
            benchmark_run_id=f"benchmark_{job.job_id}",
            source_video_path=str(extraction_result.source_path),
            job_metadata=job.metadata,
            extraction_options=extraction_options,
            extraction_result=extraction_result,
            inference_result=inference_result,
            analysis_result=analysis,
            llm_prompt_diagnostics=llm_prompt_diagnostics,
            llm_call_result=llm_call_metrics,
            frame_extraction_ms=frame_extraction_ms,
            analysis_ms=analysis_ms,
            llm_feedback_ms=llm_feedback_ms,
            startup_summary=streaming_artifacts.startup_summary,
            pipeline_summary=streaming_artifacts.pipeline_summary,
            total_elapsed_ms=(perf_counter() - total_started) * 1000.0,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            frame_metrics_path=streaming_artifacts.benchmark_frame_metrics_path,
        )
        job.benchmark = benchmark_result.model_dump(exclude={"frameMetrics"})
        job.benchmark_frame_metrics = []
        job.result.benchmark = job.benchmark

        self._set_progress(
            job,
            "completed",
            6,
            6,
            1.0,
            {"generating_feedback": llm_feedback_ms},
            processed_frames=processed_frame_count,
            total_frames=processed_frame_count,
        )
        job.status = "completed"

    def _run_preset_pipeline(self, job: JobRecord) -> StreamingPipelineArtifacts:
        preset_id = str(job.metadata["presetEstimationId"])
        preset_path = PRESET_ESTIMATION_DIR / f"{preset_id}.json"
        if not preset_path.exists():
            raise FileNotFoundError(f"Preset estimation JSON not found: {preset_id}")

        load_started = perf_counter()
        preset_data = json.loads(preset_path.read_text(encoding="utf-8"))

        video_info = preset_data.get("videoInfo", {})
        fps = max(1.0, float(video_info.get("fps", 30.0)))
        width = int(video_info.get("width", 0)) or None
        height = int(video_info.get("height", 0)) or None
        frame_count_hint = int(video_info.get("frameCount", 0)) or None

        raw_frames: list[dict[str, Any]] = preset_data.get("frames", [])
        total_frame_count = len(raw_frames)

        pose_frames: list[PoseFrameResult] = []
        for raw in raw_frames:
            landmarks = [
                PoseLandmarkPoint(
                    name=str(lm["name"]),
                    x=float(lm["x"]),
                    y=float(lm["y"]),
                    z=float(lm["z"]),
                    visibility=float(lm["visibility"]) if lm.get("visibility") is not None else None,
                    presence=float(lm["presence"]) if lm.get("presence") is not None else None,
                )
                for lm in raw.get("landmarks", [])
            ]
            pose_frames.append(PoseFrameResult(
                frame_index=int(raw["frameIndex"]),
                timestamp_ms=float(raw["timestampMs"]),
                pose_detected=bool(raw["poseDetected"]),
                landmarks=landmarks,
            ))

        frame_extraction_ms = (perf_counter() - load_started) * 1000.0

        chunks: list[PoseChunk] = []
        for chunk_idx, chunk_start in enumerate(range(0, len(pose_frames), FRAME_CHUNK_SIZE)):
            chunk_frames = pose_frames[chunk_start:chunk_start + FRAME_CHUNK_SIZE]
            if not chunk_frames:
                break
            chunks.append(PoseChunk(
                chunk_index=chunk_idx,
                start_frame_index=chunk_frames[0].frame_index,
                end_frame_index=chunk_frames[-1].frame_index,
                frames=chunk_frames,
            ))

        skeleton_spool_path = SKELETON_DIR / f"{job.job_id}.stream.jsonl"
        benchmark_spool_path = BENCHMARK_DIR / f"benchmark_{job.job_id}.stream.jsonl"
        benchmark_collector = PoseChunkBenchmarkCollector(spool_path=benchmark_spool_path)

        extraction_result = FrameExtractionResult(
            source_path=preset_path,
            backend="preset",
            source_fps=fps,
            frame_count=frame_count_hint,
            width=width,
            height=height,
            extracted_count=len(pose_frames),
            frames=[],
        )
        job.metadata["sourceFps"] = fps
        job.metadata["effectiveSamplingFps"] = fps

        inference_seed = PoseInferenceResult(
            source_path=str(preset_path),
            running_mode="VIDEO",
            model_name="preset_estimation",
            inference_backend="python",
            frame_count=0,
            detected_frame_count=0,
            requested_delegate="CPU",
            actual_delegate="CPU",
            delegate_fallback_applied=False,
            delegate_errors={},
            frames=[],
        )

        assembler = self._skeleton_mapper.create_assembler(
            extraction_result,
            inference_seed,
            str(job.metadata.get("filename") or preset_id),
            None,
            fps,
            spool_path=skeleton_spool_path,
            retain_frames_in_memory=False,
        )

        self._set_progress(
            job,
            "analyzing",
            2,
            6,
            0.4,
            {"extracting": frame_extraction_ms},
            stage_details={"presetMode": True, "presetId": preset_id},
            processed_frames=0,
            total_frames=total_frame_count,
        )

        processed_frame_count = 0
        detected_frame_count = 0
        for chunk in chunks:
            assembler.add_pose_chunk(chunk)
            benchmark_collector.add_pose_chunk(chunk)
            processed_frame_count += len(chunk.frames)
            detected_frame_count += sum(1 for f in chunk.frames if f.pose_detected)
            self._set_progress(
                job,
                "analyzing",
                2,
                6,
                0.4,
                stage_details={"presetMode": True, "presetId": preset_id},
                processed_frames=processed_frame_count,
                total_frames=total_frame_count,
            )

        skeleton_summary = assembler.build_summary()
        skeleton = assembler.finalize(include_frames=True)
        benchmark_frame_metrics_path = benchmark_collector.finalize()

        inference_result = PoseInferenceResult(
            source_path=str(preset_path),
            running_mode="VIDEO",
            model_name="preset_estimation",
            inference_backend="python",
            frame_count=processed_frame_count,
            detected_frame_count=detected_frame_count,
            requested_delegate="CPU",
            actual_delegate="CPU",
            delegate_fallback_applied=False,
            delegate_errors={},
            frames=[],
        )

        return StreamingPipelineArtifacts(
            extraction_result=extraction_result,
            inference_result=inference_result,
            skeleton=skeleton,
            skeleton_summary=skeleton_summary,
            processed_frame_count=processed_frame_count,
            detected_frame_count=detected_frame_count,
            frame_extraction_ms=frame_extraction_ms,
            startup_summary={"presetMode": True, "presetId": preset_id},
            pipeline_summary={
                "presetMode": True,
                "presetId": preset_id,
                "estimatedTotalFrames": total_frame_count,
                "producerFrames": processed_frame_count,
                "producerChunksProcessed": len(chunks),
                "poseChunksProcessed": len(chunks),
                "skeletonChunksCollected": len(chunks),
                "benchmarkChunksCollected": len(chunks),
            },
            benchmark_frame_metrics_path=benchmark_frame_metrics_path,
        )

    def _run_streaming_pipeline(
        self,
        *,
        job: JobRecord,
        extraction_options: FrameExtractionOptions,
        source_path: Path,
        requested_sampling_fps: float | None,
        resolved_inference_options: PoseInferenceOptions,
        extraction_started: float,
    ) -> StreamingPipelineArtifacts:
        extraction_metadata: dict[str, Any] = {}
        processed_frame_count = 0
        detected_frame_count = 0
        first_chunk_processed = False
        frame_extraction_ms = 0.0

        # Direction 1: pre-read total frame count before streaming starts
        estimated_total_frames: int | None = None
        try:
            probe = self._video_reader.probe_metadata(source_path)
            fc = int(probe.get("frame_count") or 0)
            if fc > 0:
                estimated_total_frames = fc
        except Exception:
            pass

        pipeline_metrics_lock = Lock()
        pipeline_metrics: dict[str, int] = {
            "producerFrames": 0,
            "producerChunksProcessed": 0,
            "poseChunksProcessed": 0,
            "skeletonChunksCollected": 0,
            "benchmarkChunksCollected": 0,
        }
        chunk_read_timings: list[float] = []
        pose_chunk_timings: list[float] = []
        skeleton_chunk_timings: list[float] = []
        benchmark_chunk_timings: list[float] = []

        frame_queue: Queue[FrameChunk | object] = Queue(maxsize=FRAME_CHUNK_QUEUE_MAXSIZE)
        pose_queue: Queue[Any] = Queue(maxsize=POSE_CHUNK_QUEUE_MAXSIZE)
        skeleton_queue: Queue[Any] = Queue(maxsize=COLLECTOR_QUEUE_MAXSIZE)
        benchmark_queue: Queue[Any] = Queue(maxsize=COLLECTOR_QUEUE_MAXSIZE)
        stop_event = Event()
        error_lock = Lock()
        worker_error: dict[str, Exception | None] = {"value": None}

        skeleton_spool_path = SKELETON_DIR / f"{job.job_id}.stream.jsonl"
        benchmark_spool_path = BENCHMARK_DIR / f"benchmark_{job.job_id}.stream.jsonl"
        benchmark_collector = PoseChunkBenchmarkCollector(spool_path=benchmark_spool_path)

        skeleton_state: dict[str, Any] = {
            "assembler": None,
            "summary": None,
            "skeleton": None,
        }
        startup_metrics_lock = Lock()
        startup_metrics: dict[str, Any] = {
            "frameChunkSize": FRAME_CHUNK_SIZE,
            "requestedDelegate": resolved_inference_options.delegate,
        }

        def update_startup_metrics(**values: Any) -> dict[str, Any]:
            with startup_metrics_lock:
                startup_metrics.update(
                    {
                        key: value
                        for key, value in values.items()
                        if value is not None
                    }
                )
                return dict(startup_metrics)

        def snapshot_startup_metrics() -> dict[str, Any]:
            with startup_metrics_lock:
                return dict(startup_metrics)

        def add_pipeline_metrics(**increments: int) -> dict[str, int]:
            with pipeline_metrics_lock:
                for key, value in increments.items():
                    pipeline_metrics[key] = pipeline_metrics.get(key, 0) + value
                return dict(pipeline_metrics)

        def snapshot_pipeline_metrics() -> dict[str, int]:
            with pipeline_metrics_lock:
                return dict(pipeline_metrics)

        def rounded_average(values: list[float]) -> float | None:
            if not values:
                return None
            return round(sum(values) / len(values), 1)

        def rounded_p95(values: list[float]) -> float | None:
            if not values:
                return None
            if len(values) == 1:
                return round(values[0], 1)
            sorted_values = sorted(values)
            index = (len(sorted_values) - 1) * 0.95
            lower_index = int(index)
            upper_index = min(lower_index + 1, len(sorted_values) - 1)
            weight = index - lower_index
            percentile_value = sorted_values[lower_index] + (
                (sorted_values[upper_index] - sorted_values[lower_index]) * weight
            )
            return round(percentile_value, 1)

        def build_stage_details() -> dict[str, Any]:
            return {
                **snapshot_startup_metrics(),
                **snapshot_pipeline_metrics(),
                "frameQueueDepth": frame_queue.qsize(),
                "frameQueueMax": FRAME_CHUNK_QUEUE_MAXSIZE,
                "poseQueueDepth": pose_queue.qsize(),
                "poseQueueMax": POSE_CHUNK_QUEUE_MAXSIZE,
                "skeletonQueueDepth": skeleton_queue.qsize(),
                "skeletonQueueMax": COLLECTOR_QUEUE_MAXSIZE,
                "benchmarkQueueDepth": benchmark_queue.qsize(),
                "benchmarkQueueMax": COLLECTOR_QUEUE_MAXSIZE,
                "avgChunkReadMs": rounded_average(chunk_read_timings),
                "p95ChunkReadMs": rounded_p95(chunk_read_timings),
                "avgChunkInferenceMs": rounded_average(pose_chunk_timings),
                "p95ChunkInferenceMs": rounded_p95(pose_chunk_timings),
                "avgSkeletonChunkMs": rounded_average(skeleton_chunk_timings),
                "p95SkeletonChunkMs": rounded_p95(skeleton_chunk_timings),
                "avgBenchmarkChunkMs": rounded_average(benchmark_chunk_timings),
                "p95BenchmarkChunkMs": rounded_p95(benchmark_chunk_timings),
            }

        def set_worker_error(exc: Exception) -> None:
            with error_lock:
                if worker_error["value"] is None:
                    worker_error["value"] = exc
            stop_event.set()

        def raise_if_worker_failed() -> None:
            with error_lock:
                exc = worker_error["value"]
            if exc is not None:
                raise exc

        def put_queue_item(target_queue: Queue[Any], item: Any) -> None:
            while not stop_event.is_set():
                try:
                    target_queue.put(item, timeout=0.1)
                    return
                except Full:
                    raise_if_worker_failed()
                    continue
            raise_if_worker_failed()

        def get_queue_item(source_queue: Queue[Any], worker_thread: Thread | None = None) -> Any:
            while True:
                raise_if_worker_failed()
                try:
                    return source_queue.get(timeout=0.1)
                except Empty:
                    if worker_thread is not None and not worker_thread.is_alive() and source_queue.empty():
                        return PIPELINE_QUEUE_DONE
                    if stop_event.is_set() and source_queue.empty():
                        raise_if_worker_failed()
                        return PIPELINE_QUEUE_DONE
                    continue

        def produce_frame_chunks() -> None:
            first_chunk_read_started = perf_counter()
            chunk_read_started = perf_counter()
            try:
                for frame_chunk in self._video_reader.iter_frame_chunks(
                    extraction_options,
                    chunk_size=FRAME_CHUNK_SIZE,
                    _out_metadata=extraction_metadata,
                ):
                    if stop_event.is_set():
                        return
                    if snapshot_startup_metrics().get("firstChunkReadMs") is None:
                        update_startup_metrics(
                            firstChunkReadMs=round((perf_counter() - first_chunk_read_started) * 1000.0, 3),
                            firstChunkSampleCount=len(frame_chunk.frames),
                            firstChunkStartFrameIndex=frame_chunk.start_frame_index,
                            firstChunkEndFrameIndex=frame_chunk.end_frame_index,
                            firstChunkSourceFrameSpan=(
                                frame_chunk.end_frame_index - frame_chunk.start_frame_index + 1
                            ),
                        )
                    chunk_read_timings.append(round((perf_counter() - chunk_read_started) * 1000.0, 3))
                    add_pipeline_metrics(
                        producerFrames=len(frame_chunk.frames),
                        producerChunksProcessed=1,
                    )
                    put_queue_item(frame_queue, frame_chunk)
                    chunk_read_started = perf_counter()
            except Exception as exc:
                set_worker_error(exc)
            finally:
                if not stop_event.is_set():
                    put_queue_item(frame_queue, PIPELINE_QUEUE_DONE)

        def infer_pose_chunks() -> None:
            pose_service = PoseInferenceService()
            init_started = perf_counter()
            pose_service.open_session(resolved_inference_options)
            init_metrics = update_startup_metrics(
                landmarkerInitMs=round((perf_counter() - init_started) * 1000.0, 3),
                actualDelegate=pose_service._adapter.active_delegate(),
            )
            self._set_progress(
                job,
                "initializing_landmarker",
                1,
                6,
                0.1,
                stage_details={**build_stage_details(), **init_metrics},
                total_frames=estimated_total_frames,
            )
            try:
                while True:
                    frame_chunk = get_queue_item(frame_queue, frame_producer)
                    if frame_chunk is PIPELINE_QUEUE_DONE:
                        put_queue_item(pose_queue, PIPELINE_QUEUE_DONE)
                        break
                    if not isinstance(frame_chunk, FrameChunk):
                        continue
                    chunk_inference_started = perf_counter()
                    pose_chunk = pose_service.infer_chunk(frame_chunk, resolved_inference_options)
                    chunk_ms = round((perf_counter() - chunk_inference_started) * 1000.0, 3)
                    pose_chunk_timings.append(chunk_ms)
                    add_pipeline_metrics(poseChunksProcessed=1)
                    if snapshot_startup_metrics().get("firstChunkInferenceMs") is None:
                        update_startup_metrics(firstChunkInferenceMs=chunk_ms)
                    put_queue_item(pose_queue, pose_chunk)
            except Exception as exc:
                set_worker_error(exc)
            finally:
                pose_service.close_session()
                if stop_event.is_set():
                    try:
                        pose_queue.put_nowait(PIPELINE_QUEUE_DONE)
                    except Full:
                        pass

        def collect_skeleton() -> None:
            try:
                while True:
                    pose_chunk = get_queue_item(skeleton_queue)
                    if pose_chunk is PIPELINE_QUEUE_DONE:
                        assembler = skeleton_state["assembler"]
                        if assembler is None:
                            extraction_result = self._build_streaming_extraction_result(
                                source_path=source_path,
                                metadata=extraction_metadata,
                                extracted_count=0,
                            )
                            inference_seed_result = PoseInferenceService().build_result(
                                frame_results=[],
                                frame_count=0,
                                options=resolved_inference_options,
                                source_path=str(source_path),
                            )
                            assembler = self._skeleton_mapper.create_assembler(
                                extraction_result,
                                inference_seed_result,
                                str(job.metadata.get("filename") or source_path.name),
                                requested_sampling_fps,
                                float(extraction_options.target_fps or extraction_result.source_fps),
                                spool_path=skeleton_spool_path,
                                retain_frames_in_memory=False,
                            )
                            skeleton_state["assembler"] = assembler
                        skeleton_state["summary"] = assembler.build_summary()
                        skeleton_state["skeleton"] = assembler.finalize(include_frames=True)
                        return
                    assembler = skeleton_state["assembler"]
                    if assembler is None:
                        extraction_result = self._build_streaming_extraction_result(
                            source_path=source_path,
                            metadata=extraction_metadata,
                            extracted_count=0,
                        )
                        job.metadata["sourceFps"] = extraction_result.source_fps
                        effective_sampling_fps = float(extraction_options.target_fps or extraction_result.source_fps)
                        job.metadata["effectiveSamplingFps"] = effective_sampling_fps
                        inference_seed_result = PoseInferenceService().build_result(
                            frame_results=[],
                            frame_count=0,
                            options=resolved_inference_options,
                            source_path=str(source_path),
                        )
                        assembler = self._skeleton_mapper.create_assembler(
                            extraction_result,
                            inference_seed_result,
                            str(job.metadata.get("filename") or source_path.name),
                            requested_sampling_fps,
                            effective_sampling_fps,
                            spool_path=skeleton_spool_path,
                            retain_frames_in_memory=False,
                        )
                        skeleton_state["assembler"] = assembler
                    collect_started = perf_counter()
                    assembler.add_pose_chunk(pose_chunk)
                    skeleton_chunk_timings.append(round((perf_counter() - collect_started) * 1000.0, 3))
                    add_pipeline_metrics(skeletonChunksCollected=1)
            except Exception as exc:
                set_worker_error(exc)

        def collect_benchmark() -> None:
            try:
                while True:
                    pose_chunk = get_queue_item(benchmark_queue)
                    if pose_chunk is PIPELINE_QUEUE_DONE:
                        benchmark_collector.finalize()
                        return
                    collect_started = perf_counter()
                    benchmark_collector.add_pose_chunk(pose_chunk)
                    benchmark_chunk_timings.append(round((perf_counter() - collect_started) * 1000.0, 3))
                    add_pipeline_metrics(benchmarkChunksCollected=1)
            except Exception as exc:
                set_worker_error(exc)

        frame_producer = Thread(
            target=produce_frame_chunks,
            name=f"frame-producer-{source_path.stem}",
            daemon=True,
        )
        pose_worker = Thread(
            target=infer_pose_chunks,
            name=f"pose-worker-{source_path.stem}",
            daemon=True,
        )
        skeleton_collector_thread = Thread(
            target=collect_skeleton,
            name=f"skeleton-collector-{source_path.stem}",
            daemon=True,
        )
        benchmark_collector_thread = Thread(
            target=collect_benchmark,
            name=f"benchmark-collector-{source_path.stem}",
            daemon=True,
        )

        frame_producer.start()
        pose_worker.start()
        skeleton_collector_thread.start()
        benchmark_collector_thread.start()

        try:
            while True:
                pose_chunk = get_queue_item(pose_queue, pose_worker)
                if pose_chunk is PIPELINE_QUEUE_DONE:
                    break
                if not first_chunk_processed:
                    frame_extraction_ms = (perf_counter() - extraction_started) * 1000.0
                    startup_summary = update_startup_metrics(
                        startupWallMs=round(frame_extraction_ms, 3)
                    )
                    self._set_progress(
                        job,
                        "analyzing",
                        2,
                        6,
                        0.4,
                        {"extracting": frame_extraction_ms},
                        stage_details=build_stage_details(),
                        processed_frames=0,
                        total_frames=estimated_total_frames,
                    )
                    first_chunk_processed = True

                processed_frame_count += len(pose_chunk.frames)
                detected_frame_count += sum(1 for frame in pose_chunk.frames if frame.pose_detected)
                put_queue_item(skeleton_queue, pose_chunk)
                put_queue_item(benchmark_queue, pose_chunk)
                self._set_progress(
                    job,
                    "analyzing",
                    2,
                    6,
                    0.4,
                    stage_details=build_stage_details(),
                    processed_frames=processed_frame_count,
                    total_frames=estimated_total_frames,
                )
        except Exception:
            stop_event.set()
            raise
        finally:
            stop_event.set()
            for collector_queue in (skeleton_queue, benchmark_queue):
                try:
                    collector_queue.put_nowait(PIPELINE_QUEUE_DONE)
                except Full:
                    pass
            for worker in (
                frame_producer,
                pose_worker,
                skeleton_collector_thread,
                benchmark_collector_thread,
            ):
                worker.join()
            raise_if_worker_failed()

        if not first_chunk_processed:
            frame_extraction_ms = (perf_counter() - extraction_started) * 1000.0
            startup_summary = update_startup_metrics(startupWallMs=round(frame_extraction_ms, 3))
            self._set_progress(
                job,
                "analyzing",
                2,
                6,
                0.4,
                {"extracting": frame_extraction_ms},
                stage_details=build_stage_details(),
                processed_frames=processed_frame_count,
                total_frames=estimated_total_frames,
            )

        extraction_result = self._build_streaming_extraction_result(
            source_path=source_path,
            metadata=extraction_metadata,
            extracted_count=processed_frame_count,
        )
        job.metadata["sourceFps"] = extraction_result.source_fps
        job.metadata["effectiveSamplingFps"] = float(extraction_options.target_fps or extraction_result.source_fps)
        inference_result = PoseInferenceService().build_result(
            frame_results=[],
            frame_count=processed_frame_count,
            options=resolved_inference_options,
            source_path=str(extraction_result.source_path),
        )
        inference_result.detected_frame_count = detected_frame_count

        skeleton = skeleton_state["skeleton"]
        if skeleton is None:
            skeleton = self._skeleton_mapper.create_assembler(
                extraction_result,
                inference_result,
                str(job.metadata.get("filename") or extraction_result.source_path.name),
                requested_sampling_fps,
                job.metadata.get("effectiveSamplingFps"),
                spool_path=skeleton_spool_path,
                retain_frames_in_memory=False,
            ).finalize(include_frames=True)
        skeleton_summary = skeleton_state["summary"] or {
            "frames": [],
            "videoInfo": skeleton.get("videoInfo", {}),
            "nextTimestampCursorMs": skeleton.get("nextTimestampCursorMs", 0),
        }
        benchmark_frame_metrics_path = benchmark_collector.finalize()

        final_stage_details = build_stage_details()
        pipeline_summary: dict[str, Any] = {
            "estimatedTotalFrames": estimated_total_frames,
            "producerFrames": final_stage_details.get("producerFrames"),
            "producerChunksProcessed": final_stage_details.get("producerChunksProcessed"),
            "poseChunksProcessed": final_stage_details.get("poseChunksProcessed"),
            "skeletonChunksCollected": final_stage_details.get("skeletonChunksCollected"),
            "benchmarkChunksCollected": final_stage_details.get("benchmarkChunksCollected"),
            "totalChunkReadMs": round(sum(chunk_read_timings), 3) if chunk_read_timings else None,
            "avgChunkReadMs": final_stage_details.get("avgChunkReadMs"),
            "p95ChunkReadMs": final_stage_details.get("p95ChunkReadMs"),
            "totalChunkInferenceMs": round(sum(pose_chunk_timings), 3) if pose_chunk_timings else None,
            "avgChunkInferenceMs": final_stage_details.get("avgChunkInferenceMs"),
            "p95ChunkInferenceMs": final_stage_details.get("p95ChunkInferenceMs"),
            "totalSkeletonChunkMs": round(sum(skeleton_chunk_timings), 3) if skeleton_chunk_timings else None,
            "avgSkeletonChunkMs": final_stage_details.get("avgSkeletonChunkMs"),
            "p95SkeletonChunkMs": final_stage_details.get("p95SkeletonChunkMs"),
            "totalBenchmarkChunkMs": round(sum(benchmark_chunk_timings), 3) if benchmark_chunk_timings else None,
            "avgBenchmarkChunkMs": final_stage_details.get("avgBenchmarkChunkMs"),
            "p95BenchmarkChunkMs": final_stage_details.get("p95BenchmarkChunkMs"),
        }

        return StreamingPipelineArtifacts(
            extraction_result=extraction_result,
            inference_result=inference_result,
            skeleton=skeleton,
            skeleton_summary=skeleton_summary,
            processed_frame_count=processed_frame_count,
            detected_frame_count=detected_frame_count,
            frame_extraction_ms=frame_extraction_ms,
            startup_summary=snapshot_startup_metrics(),
            pipeline_summary=pipeline_summary,
            benchmark_frame_metrics_path=benchmark_frame_metrics_path,
        )

    def _load_skeleton(self, job: JobRecord) -> dict[str, Any]:
        if job.skeleton_path:
            return json.loads(Path(job.skeleton_path).read_text(encoding="utf-8"))
        if job.result is None:
            return {}
        return job.result.skeleton

    def _cleanup_transient_upload(self, job: JobRecord) -> None:
        source_path = Path(str(job.metadata.get("sourcePath") or ""))
        if not source_path:
            return

        try:
            resolved_source = source_path.resolve()
            resolved_upload_dir = UPLOAD_DIR.resolve()
        except OSError:
            return

        if resolved_source.parent != resolved_upload_dir or not resolved_source.is_file():
            return

        try:
            resolved_source.unlink()
        except OSError:
            pass

    def _build_extraction_options(self, job: JobRecord) -> FrameExtractionOptions:
        source_path = Path(str(job.metadata["sourcePath"]))
        requested_sampling_fps = job.metadata.get("requestedSamplingFps")
        return FrameExtractionOptions(
            video_path=source_path,
            sampling_mode="target_fps",
            target_fps=float(requested_sampling_fps) if requested_sampling_fps is not None else None,
            output_dir=EXTRACTED_FRAME_DIR / job.job_id,
            save_images=False,
            convert_bgr_to_rgb=True,
        )

    def _iter_bounded_frame_chunks(
        self,
        options: FrameExtractionOptions,
        *,
        chunk_size: int,
        queue_maxsize: int,
        _out_metadata: dict[str, Any],
    ):
        queue: Queue[tuple[str, FrameChunk | Exception | None]] = Queue(maxsize=queue_maxsize)
        stop_event = Event()

        def put_message(kind: str, payload: FrameChunk | Exception | None) -> None:
            while not stop_event.is_set():
                try:
                    queue.put((kind, payload), timeout=0.1)
                    return
                except Full:
                    continue

        def produce_chunks() -> None:
            try:
                for frame_chunk in self._video_reader.iter_frame_chunks(
                    options,
                    chunk_size=chunk_size,
                    _out_metadata=_out_metadata,
                ):
                    if stop_event.is_set():
                        return
                    put_message("chunk", frame_chunk)
            except Exception as exc:
                put_message("error", exc)
            finally:
                put_message("done", None)

        producer = Thread(
            target=produce_chunks,
            name=f"frame-producer-{Path(str(options.video_path)).stem}",
            daemon=True,
        )
        producer.start()

        try:
            while True:
                try:
                    kind, payload = queue.get(timeout=0.1)
                except Empty:
                    if not producer.is_alive() and queue.empty():
                        break
                    continue

                if kind == "chunk" and isinstance(payload, FrameChunk):
                    yield payload
                    continue
                if kind == "error" and isinstance(payload, Exception):
                    raise payload
                if kind == "done":
                    break
        finally:
            stop_event.set()
            producer.join(timeout=1.0)

    def _build_streaming_extraction_result(
        self,
        *,
        source_path: Path,
        metadata: dict[str, Any],
        extracted_count: int,
    ) -> FrameExtractionResult:
        source_fps = self._video_reader._normalize_source_fps(float(metadata.get("fps", 0.0)))
        return FrameExtractionResult(
            source_path=source_path,
            backend=str(metadata.get("backend", "unknown")),
            source_fps=source_fps,
            frame_count=int(metadata["frame_count"]) if metadata.get("frame_count") else None,
            width=int(metadata["width"]) if metadata.get("width") else None,
            height=int(metadata["height"]) if metadata.get("height") else None,
            extracted_count=extracted_count,
            frames=[],
        )

    def _normalize_requested_sampling_fps(self, value: float | None) -> float | None:
        if value is None:
            return None
        resolved = float(value)
        if resolved <= 0:
            raise HTTPException(status_code=400, detail="samplingFps must be > 0.")
        return resolved

    def _build_metadata(
        self,
        *,
        filename: str,
        source_path: str,
        requested_sampling_fps: float | None,
        exercise_type: str | None,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
        bar_placement_mode: str | None,
        model_asset_path: str | None,
        model_variant: str | None,
        delegate: str | None,
    ) -> dict[str, Any]:
        resolved_requested_sampling_fps = self._normalize_requested_sampling_fps(requested_sampling_fps)
        resolved_bodyweight_kg = self._normalize_optional_mass_kg(bodyweight_kg, "bodyweightKg")
        resolved_external_load_kg = self._normalize_optional_mass_kg(external_load_kg, "externalLoadKg")
        resolved_bar_placement_mode = self._normalize_bar_placement_mode(bar_placement_mode)
        return {
            "filename": filename,
            "sourcePath": source_path,
            "requestedSamplingFps": resolved_requested_sampling_fps,
            "exerciseType": exercise_type,
            "bodyweightKg": resolved_bodyweight_kg,
            "externalLoadKg": resolved_external_load_kg,
            "barPlacementMode": resolved_bar_placement_mode,
            "modelAssetPath": model_asset_path,
            "modelVariant": model_variant,
            "delegate": delegate,
        }

    def _build_initial_result(self, metadata: dict[str, Any]) -> MotionAnalysisResult:
        return MotionAnalysisResult(
            skeleton={
                "frames": [],
                "videoInfo": {
                    "videoSrc": metadata.get("sourcePath"),
                    "displayName": metadata.get("filename"),
                    "requestedSamplingFps": metadata.get("requestedSamplingFps"),
                },
                "nextTimestampCursorMs": 0,
            },
            analysis=AnalysisResult(
                summary=AnalysisSummary(
                    exerciseType=str(metadata.get("exerciseType") or "unknown"),
                    bodyweightKg=metadata.get("bodyweightKg"),
                    externalLoadKg=metadata.get("externalLoadKg"),
                    barPlacementMode=metadata.get("barPlacementMode"),
                )
            ),
            llmFeedback=LlmFeedbackResult(),
            benchmark={},
        )

    def _normalize_optional_mass_kg(self, value: float | None, field_name: str) -> float | None:
        if value is None:
            return None
        resolved = float(value)
        if resolved <= 0:
            raise HTTPException(status_code=400, detail=f"{field_name} must be > 0.")
        return resolved

    def _normalize_bar_placement_mode(self, value: str | None) -> str:
        normalized = (value or "high_bar").strip().lower()
        if normalized not in VALID_BAR_PLACEMENT_MODES:
            raise HTTPException(
                status_code=400,
                detail="barPlacementMode must be one of: auto, high_bar, low_bar.",
            )
        return normalized

    def _persist_skeleton(self, job_id: str, skeleton: dict[str, Any]) -> str:
        skeleton_path = SKELETON_DIR / f"{job_id}.json"
        skeleton_path.write_text(
            json.dumps(skeleton, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        return str(skeleton_path)

    def _build_inference_options(self, job: JobRecord) -> PoseInferenceOptions | None:
        return self._build_inference_options_from_metadata(job.metadata)

    def _build_inference_options_from_metadata(
        self,
        metadata: dict[str, Any],
    ) -> PoseInferenceOptions | None:
        raw_model_asset_path = self._normalize_optional_text(metadata.get("modelAssetPath"))
        raw_model_variant = self._normalize_optional_text(metadata.get("modelVariant"))
        raw_delegate = self._normalize_optional_text(metadata.get("delegate"))
        if not raw_model_asset_path and not raw_model_variant and not raw_delegate:
            return None

        model_variant = str(raw_model_variant or DEFAULT_MODEL_VARIANT).lower()
        if model_variant not in VALID_MODEL_VARIANTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid modelVariant '{model_variant}'. Use one of: lite, full, heavy.",
            )

        resolved_model_path = (
            Path(str(raw_model_asset_path))
            if raw_model_asset_path
            else MODEL_ASSET_PATHS.get(model_variant, DEFAULT_MODEL_ASSET_PATH)
        )
        options = PoseInferenceOptions(
            model_asset_path=resolved_model_path,
            model_variant=model_variant,  # type: ignore[arg-type]
        )
        if raw_delegate:
            delegate = str(raw_delegate).upper()
            if delegate not in VALID_DELEGATES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid delegate '{raw_delegate}'. Use CPU or GPU.",
                )
            options.delegate = delegate  # type: ignore[assignment]
        return options

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if normalized.lower() == "string":
            return None
        return normalized

    def _set_progress(
        self,
        job: JobRecord,
        stage: str,
        current_step: int,
        total_steps: int,
        ratio: float,
        stage_durations_ms: dict[str, float] | None = None,
        stage_details: dict[str, Any] | None = None,
        processed_frames: int | None = None,
        total_frames: int | None = None,
    ) -> None:
        existing = job.progress.stageDurationsMs if job.progress else {}
        existing_details = (
            dict(job.progress.stageDetails)
            if job.progress is not None and job.progress.stage == stage
            else {}
        )
        job.status = stage
        job.progress = JobProgress(
            stage=stage,
            currentStep=current_step,
            totalSteps=total_steps,
            ratio=ratio,
            stageDurationsMs={**existing, **(stage_durations_ms or {})},
            stageDetails={**existing_details, **(stage_details or {})},
            processedFrames=processed_frames,
            totalFrames=total_frames,
        )
        self._notify_subscribers(job.job_id)

    def _fail_job(self, job: JobRecord, exc: Exception) -> None:
        job.status = "failed"
        job.progress = JobProgress(
            stage="failed",
            currentStep=0,
            totalSteps=6,
            ratio=0.0,
            stageDetails=job.progress.stageDetails if job.progress else {},
            processedFrames=job.progress.processedFrames if job.progress else None,
            totalFrames=job.progress.totalFrames if job.progress else None,
        )
        job.error = {
            "code": exc.__class__.__name__,
            "message": str(exc),
        }
        self._notify_subscribers(job.job_id)

    def _notify_subscribers(self, job_id: str) -> None:
        queues = self._sse_queues.get(job_id)
        if not queues or self._loop is None:
            return
        try:
            status = self.get_status(job_id)
            payload = status.model_dump()
        except Exception:
            return
        for queue in list(queues):
            self._loop.call_soon_threadsafe(queue.put_nowait, payload)

    async def stream_status(self, job_id: str) -> AsyncGenerator[str, None]:
        if job_id not in self._jobs:
            yield f"event: error\ndata: {json.dumps({'code': 'not_found', 'message': 'Job not found.'})}\n\n"
            return

        current = self.get_status(job_id)
        yield f"data: {json.dumps(current.model_dump())}\n\n"

        terminal = {"completed", "failed"}
        if current.status in terminal:
            return

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._sse_queues.setdefault(job_id, []).append(queue)

        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                yield f"data: {json.dumps(payload)}\n\n"

                if payload.get("status") in terminal:
                    break
        finally:
            queues = self._sse_queues.get(job_id, [])
            if queue in queues:
                queues.remove(queue)
            if not queues:
                self._sse_queues.pop(job_id, None)


job_manager = JobManager()
