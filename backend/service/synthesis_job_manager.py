from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from time import perf_counter
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import HTTPException

from config import DEFAULT_MODEL_ASSET_PATH, PRESET_ESTIMATION_DIR
from schema.frame import FrameChunk, FrameExtractionOptions
from schema.job import JobCreateResponse, JobError, JobProgress, JobStatusResponse
from schema.pose import AlignedPoseChunkPair, PoseChunk, PoseFrameResult, PoseLandmarkPoint, PoseInferenceOptions
from schema.synthesis import (
    StreamingPairManifest,
    StreamingSource,
    SynthesisInput,
    SynthesisJobCreateRequest,
)
from service.analysis_pipeline import AnalysisPipelineService
from service.dual_video_synthesis_coordinator import DualVideoSynthesisCoordinator
from service.pose_inference import PoseInferenceService
from service.skeleton_3d_evaluator import Skeleton3DEvaluator
from service.skeleton_3d_synthesizer import SynthesisChunkResult, Skeleton3DSynthesizer
from service.skeleton_artifact_repository import (
    SkeletonArtifactNotFoundError,
    SkeletonArtifactRepository,
)
from service.video_reader import VideoReaderService


DEFAULT_GT_REF = "171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json"

SYNTH_FRAME_CHUNK_SIZE = 32
SYNTH_FRAME_QUEUE_MAXSIZE = 2
SYNTH_POSE_QUEUE_MAXSIZE = 2
SYNTH_ALIGNED_QUEUE_MAXSIZE = 2
SYNTH_RESULT_QUEUE_MAXSIZE = 4
SYNTH_COORDINATOR_MAX_PENDING = 16
_SYNTH_PIPELINE_DONE = object()


@dataclass
class SynthesisJobRecord:
    job_id: str
    request: SynthesisJobCreateRequest
    status: str = "queued"
    progress: JobProgress | None = None
    error: dict[str, Any] | None = None
    result_summary: dict[str, Any] = field(default_factory=dict)
    artifact_refs: dict[str, Any] = field(default_factory=dict)


class SynthesisJobManager:
    def __init__(
        self,
        *,
        artifact_repository: SkeletonArtifactRepository,
        synthesizer: Skeleton3DSynthesizer | None = None,
        evaluator: Skeleton3DEvaluator | None = None,
        video_reader: VideoReaderService | None = None,
    ) -> None:
        self._jobs: dict[str, SynthesisJobRecord] = {}
        self._artifact_repository = artifact_repository
        self._synthesizer = synthesizer or Skeleton3DSynthesizer(
            artifact_repository=artifact_repository
        )
        self._evaluator = evaluator or Skeleton3DEvaluator()
        self._video_reader = video_reader or VideoReaderService()

    async def create_job(self, request: SynthesisJobCreateRequest) -> JobCreateResponse:
        job_id = f"synth_{uuid4().hex[:8]}"
        if request.streamingManifest is not None:
            m = request.streamingManifest
            initial_details: dict[str, Any] = {
                "mode": "streaming",
                "sourceVideoPaths": [
                    self._source_display_path(m.sources.A),
                    self._source_display_path(m.sources.B),
                ],
                "cameraPair": [m.sources.A.cameraId, m.sources.B.cameraId],
                "artifactRefs": {},
            }
        else:
            m_pair = request.pairManifest
            assert m_pair is not None
            initial_details = {
                "mode": "artifact",
                "sourceJobIds": [
                    m_pair.sources.A.sourceJobId,
                    m_pair.sources.B.sourceJobId,
                ],
                "cameraPair": [
                    m_pair.sources.A.cameraId,
                    m_pair.sources.B.cameraId,
                ],
                "artifactRefs": {},
            }
        job = SynthesisJobRecord(
            job_id=job_id,
            request=request,
            progress=JobProgress(
                stage="queued",
                currentStep=0,
                totalSteps=6,
                ratio=0.0,
                stageDetails={"synthesis": initial_details},
            ),
        )
        self._jobs[job_id] = job
        asyncio.create_task(self._run_job(job))
        return JobCreateResponse(jobId=job_id, status="queued")

    def get_status(self, job_id: str) -> JobStatusResponse:
        job = self._get_job(job_id)
        return JobStatusResponse(
            jobId=job.job_id,
            status=job.status,
            progress=job.progress,
            error=JobError.model_validate(job.error) if job.error else None,
        )

    def get_result(self, job_id: str) -> dict[str, Any]:
        job = self._get_completed_job(job_id)
        return job.result_summary

    def get_skeleton3d_all(self, job_id: str) -> dict[str, Any]:
        self._get_completed_job(job_id)
        return self._artifact_repository.get_skeleton3d_all(job_id)

    def get_skeleton3d_page(self, job_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        self._get_completed_job(job_id)
        return self._artifact_repository.get_skeleton3d_page(job_id, offset=offset, limit=limit)

    def get_skeleton_a_page(self, job_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        self._get_completed_job(job_id)
        try:
            return self._artifact_repository.get_skeleton_a_page(job_id, offset=offset, limit=limit)
        except SkeletonArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Camera A 2D skeleton not found.") from exc

    def get_skeleton_b_page(self, job_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        self._get_completed_job(job_id)
        try:
            return self._artifact_repository.get_skeleton_b_page(job_id, offset=offset, limit=limit)
        except SkeletonArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Camera B 2D skeleton not found.") from exc

    def get_evaluation(self, job_id: str) -> dict[str, Any]:
        self._get_completed_job(job_id)
        try:
            return self._artifact_repository.read_evaluation(job_id)
        except SkeletonArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Evaluation artifact not found.") from exc

    def get_debug_report(self, job_id: str) -> dict[str, Any]:
        self._get_completed_job(job_id)
        try:
            return self._artifact_repository.read_debug_report(job_id)
        except SkeletonArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Debug artifact not found.") from exc

    async def _run_job(self, job: SynthesisJobRecord) -> None:
        try:
            await asyncio.to_thread(self._execute_job, job)
        except Exception as exc:
            self._fail_job(job, exc)

    def _execute_job(self, job: SynthesisJobRecord) -> None:
        request = job.request
        if request.streamingManifest is not None:
            self._run_streaming_synthesis(job, request.streamingManifest)
        else:
            assert request.pairManifest is not None
            self._run_artifact_synthesis(job, request)

    # ------------------------------------------------------------------
    # Artifact-based synthesis (existing flow, renamed)
    # ------------------------------------------------------------------

    def _run_artifact_synthesis(self, job: SynthesisJobRecord, request: SynthesisJobCreateRequest) -> None:
        synthesis_input = SynthesisInput.from_manifest(request.pairManifest)
        self._set_progress(job, "validating_manifest", 1, 6, 0.1,
                           stage_details=self._artifact_stage_details(job, synthesis_input))

        self._artifact_repository.get_skeleton_summary(synthesis_input.sourceJobIdA)
        self._artifact_repository.get_skeleton_summary(synthesis_input.sourceJobIdB)
        self._set_progress(job, "loading_source_artifacts", 2, 6, 0.25,
                           stage_details=self._artifact_stage_details(job, synthesis_input))

        self._set_progress(job, "aligning_frames", 3, 6, 0.4,
                           stage_details=self._artifact_stage_details(job, synthesis_input))
        self._set_progress(job, "triangulating", 4, 6, 0.65,
                           stage_details=self._artifact_stage_details(job, synthesis_input))
        skeleton3d = self._synthesizer.synthesize(synthesis_input)

        self._set_progress(
            job, "writing_artifacts", 5, 6, 0.85,
            stage_details=self._artifact_stage_details(
                job, synthesis_input,
                extra={"pairedFrameCount": skeleton3d.get("qualitySummary", {}).get("pairedFrameCount", 0)},
            ),
        )
        self._write_artifacts_and_complete(job, skeleton3d, request)

    def _artifact_stage_details(
        self,
        job: SynthesisJobRecord,
        synthesis_input: SynthesisInput,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "synthesis": {
                "mode": "artifact",
                "sourceJobIds": [synthesis_input.sourceJobIdA, synthesis_input.sourceJobIdB],
                "cameraPair": [synthesis_input.cameraIdA, synthesis_input.cameraIdB],
                "artifactRefs": job.artifact_refs,
                **(extra or {}),
            }
        }

    # ------------------------------------------------------------------
    # Streaming synthesis (new chunk-based conveyor pipeline)
    # ------------------------------------------------------------------

    def _run_streaming_synthesis(self, job: SynthesisJobRecord, manifest: StreamingPairManifest) -> None:
        src_a = manifest.sources.A
        src_b = manifest.sources.B
        camera_id_a = src_a.cameraId
        camera_id_b = src_b.cameraId
        video_path_a: Path | None = Path(src_a.videoPath) if src_a.videoPath else None
        video_path_b: Path | None = Path(src_b.videoPath) if src_b.videoPath else None

        # --- Stage 1: initialize ---
        self._set_progress(
            job, "initializing", 1, 5, 0.05,
            stage_details=self._streaming_stage_details(job, manifest),
        )

        camera_a, camera_b = self._synthesizer._calibration_service.load_pair(
            manifest.calibrationRef, camera_id_a, camera_id_b,
        )
        max_delta_ms = self._synthesizer._alignment_service.resolve_max_delta_ms(
            manifest.sync.maxDeltaMs, fps_a=None, fps_b=None,
        )
        thresholds = manifest.thresholds
        inference_options = PoseInferenceOptions(model_asset_path=DEFAULT_MODEL_ASSET_PATH)

        # Load preset frames eagerly (needed for frame count and loader thread)
        preset_frames_a: list[dict[str, Any]] | None = None
        preset_frames_b: list[dict[str, Any]] | None = None
        if src_a.presetEstimationId:
            preset_path_a = PRESET_ESTIMATION_DIR / f"{src_a.presetEstimationId}.json"
            preset_frames_a = json.loads(preset_path_a.read_text(encoding="utf-8")).get("frames", [])
        if src_b.presetEstimationId:
            preset_path_b = PRESET_ESTIMATION_DIR / f"{src_b.presetEstimationId}.json"
            preset_frames_b = json.loads(preset_path_b.read_text(encoding="utf-8")).get("frames", [])

        # Estimate total frame count for progress display
        estimated_total_frames: int | None = None
        try:
            fc_a: int = 0
            fc_b: int = 0
            if video_path_a:
                probe_a = self._video_reader.probe_metadata(video_path_a)
                fc_a = int(probe_a.get("frame_count") or 0)
            elif preset_frames_a is not None:
                fc_a = len(preset_frames_a)
            if video_path_b:
                probe_b = self._video_reader.probe_metadata(video_path_b)
                fc_b = int(probe_b.get("frame_count") or 0)
            elif preset_frames_b is not None:
                fc_b = len(preset_frames_b)
            if fc_a > 0 and fc_b > 0:
                estimated_total_frames = min(fc_a, fc_b)
        except Exception:
            pass

        extraction_opts_a: FrameExtractionOptions | None = None
        extraction_opts_b: FrameExtractionOptions | None = None
        if video_path_a:
            extraction_opts_a = FrameExtractionOptions(
                video_path=video_path_a, sampling_mode="all", save_images=False, convert_bgr_to_rgb=True,
            )
        if video_path_b:
            extraction_opts_b = FrameExtractionOptions(
                video_path=video_path_b, sampling_mode="all", save_images=False, convert_bgr_to_rgb=True,
            )

        # --- Stage 2: streaming conveyor ---
        frame_queue_a: Queue[Any] = Queue(maxsize=SYNTH_FRAME_QUEUE_MAXSIZE)
        frame_queue_b: Queue[Any] = Queue(maxsize=SYNTH_FRAME_QUEUE_MAXSIZE)
        pose_queue_a: Queue[Any] = Queue(maxsize=SYNTH_POSE_QUEUE_MAXSIZE)
        pose_queue_b: Queue[Any] = Queue(maxsize=SYNTH_POSE_QUEUE_MAXSIZE)
        aligned_pair_queue: Queue[Any] = Queue(maxsize=SYNTH_ALIGNED_QUEUE_MAXSIZE)
        result_queue: Queue[Any] = Queue(maxsize=SYNTH_RESULT_QUEUE_MAXSIZE)

        stop_event = Event()
        error_lock = Lock()
        metrics_lock = Lock()
        assembler_lock = Lock()
        worker_error: dict[str, Exception | None] = {"value": None}
        pipeline_metrics: dict[str, int] = {
            "pairedChunks": 0, "triangulatedChunks": 0, "triangulatedFrames": 0,
            "inferredChunksA": 0, "inferredChunksB": 0,
        }
        triangulate_timings: list[float] = []
        assembled_frames_a: list[dict[str, Any]] = []
        assembled_frames_b: list[dict[str, Any]] = []

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

        def put_item(q: Queue[Any], item: Any) -> None:
            while not stop_event.is_set():
                try:
                    q.put(item, timeout=0.1)
                    return
                except Full:
                    raise_if_worker_failed()
            raise_if_worker_failed()

        def get_item(q: Queue[Any], upstream: Thread | None = None) -> Any:
            while True:
                raise_if_worker_failed()
                try:
                    return q.get(timeout=0.1)
                except Empty:
                    if upstream is not None and not upstream.is_alive() and q.empty():
                        return _SYNTH_PIPELINE_DONE
                    if stop_event.is_set() and q.empty():
                        raise_if_worker_failed()
                        return _SYNTH_PIPELINE_DONE
                    continue

        source_display_a = self._source_display_path(src_a)
        source_display_b = self._source_display_path(src_b)

        def build_stage_details(processed: int | None = None) -> dict[str, Any]:
            with metrics_lock:
                snap = dict(pipeline_metrics)
            details: dict[str, Any] = {
                "mode": "streaming",
                "sourceVideoPaths": [source_display_a, source_display_b],
                "cameraPair": [camera_id_a, camera_id_b],
                "artifactRefs": job.artifact_refs,
                **snap,
            }
            if triangulate_timings:
                sv = sorted(triangulate_timings)
                idx95 = int(0.95 * (len(sv) - 1))
                details["avgTriangulateMs"] = round(sum(sv) / len(sv), 1)
                details["p95TriangulateMs"] = round(sv[idx95], 1)
            return {"synthesis": details}

        def produce_frames(opts: FrameExtractionOptions, out_queue: Queue[Any], label: str) -> None:
            try:
                for chunk in self._video_reader.iter_frame_chunks(
                    opts, chunk_size=SYNTH_FRAME_CHUNK_SIZE,
                ):
                    if stop_event.is_set():
                        return
                    put_item(out_queue, chunk)
            except Exception as exc:
                set_worker_error(exc)
            finally:
                if not stop_event.is_set():
                    put_item(out_queue, _SYNTH_PIPELINE_DONE)

        def infer_poses(
            in_queue: Queue[Any], out_queue: Queue[Any],
            producer: Thread, label: str,
        ) -> None:
            pose_svc = PoseInferenceService()
            pose_svc.open_session(inference_options)
            try:
                while True:
                    item = get_item(in_queue, producer)
                    if item is _SYNTH_PIPELINE_DONE:
                        put_item(out_queue, _SYNTH_PIPELINE_DONE)
                        break
                    if not isinstance(item, FrameChunk):
                        continue
                    chunk = pose_svc.infer_chunk(item, inference_options)
                    put_item(out_queue, chunk)
            except Exception as exc:
                set_worker_error(exc)
            finally:
                pose_svc.close_session()
                if stop_event.is_set():
                    try:
                        out_queue.put_nowait(_SYNTH_PIPELINE_DONE)
                    except Full:
                        pass

        def load_preset_poses(
            frames_raw: list[dict[str, Any]], out_queue: Queue[Any], label: str,
        ) -> None:
            """Push preset estimation frames directly as PoseChunks (skips MediaPipe inference)."""
            try:
                chunk_index = 0
                for i in range(0, len(frames_raw), SYNTH_FRAME_CHUNK_SIZE):
                    if stop_event.is_set():
                        return
                    raw_chunk = frames_raw[i : i + SYNTH_FRAME_CHUNK_SIZE]
                    frames = [
                        PoseFrameResult(
                            frame_index=int(f.get("frameIndex", i + j)),
                            timestamp_ms=float(f.get("timestampMs", 0.0)),
                            pose_detected=bool(f.get("poseDetected", True)),
                            landmarks=[
                                PoseLandmarkPoint(
                                    name=lm.get("name", f"lm_{k}"),
                                    x=float(lm.get("x", 0.0)),
                                    y=float(lm.get("y", 0.0)),
                                    z=float(lm.get("z", 0.0)),
                                    visibility=lm.get("visibility"),
                                    presence=lm.get("presence"),
                                )
                                for k, lm in enumerate(f.get("landmarks", []))
                            ],
                        )
                        for j, f in enumerate(raw_chunk)
                    ]
                    chunk = PoseChunk(
                        chunk_index=chunk_index,
                        start_frame_index=frames[0].frame_index if frames else i,
                        end_frame_index=frames[-1].frame_index if frames else i + len(raw_chunk) - 1,
                        frames=frames,
                    )
                    put_item(out_queue, chunk)
                    chunk_index += 1
            except Exception as exc:
                set_worker_error(exc)
            finally:
                if not stop_event.is_set():
                    put_item(out_queue, _SYNTH_PIPELINE_DONE)

        def coordinate(pose_source_a: Thread, pose_source_b: Thread) -> None:
            coordinator = DualVideoSynthesisCoordinator(
                primary_stream_id="video_a",
                secondary_stream_id="video_b",
                max_pending_chunks=SYNTH_COORDINATOR_MAX_PENDING,
            )
            try:
                done_a = done_b = False
                while not (done_a and done_b) and not stop_event.is_set():
                    if not done_a:
                        try:
                            item = pose_queue_a.get(timeout=0.05)
                            if item is _SYNTH_PIPELINE_DONE:
                                done_a = True
                            else:
                                # Fan-out: accumulate 2D skeleton frames from camera A
                                with assembler_lock:
                                    for frame in item.frames:
                                        assembled_frames_a.append(frame.to_dict())
                                with metrics_lock:
                                    pipeline_metrics["inferredChunksA"] += 1
                                pair = coordinator.ingest("video_a", item)
                                if pair is not None:
                                    with metrics_lock:
                                        pipeline_metrics["pairedChunks"] += 1
                                    put_item(aligned_pair_queue, pair)
                        except Empty:
                            if not pose_source_a.is_alive() and pose_queue_a.empty():
                                done_a = True
                    if not done_b:
                        try:
                            item = pose_queue_b.get(timeout=0.05)
                            if item is _SYNTH_PIPELINE_DONE:
                                done_b = True
                            else:
                                # Fan-out: accumulate 2D skeleton frames from camera B
                                with assembler_lock:
                                    for frame in item.frames:
                                        assembled_frames_b.append(frame.to_dict())
                                with metrics_lock:
                                    pipeline_metrics["inferredChunksB"] += 1
                                pair = coordinator.ingest("video_b", item)
                                if pair is not None:
                                    with metrics_lock:
                                        pipeline_metrics["pairedChunks"] += 1
                                    put_item(aligned_pair_queue, pair)
                        except Empty:
                            if not pose_source_b.is_alive() and pose_queue_b.empty():
                                done_b = True
                put_item(aligned_pair_queue, _SYNTH_PIPELINE_DONE)
            except Exception as exc:
                set_worker_error(exc)
            finally:
                if stop_event.is_set():
                    try:
                        aligned_pair_queue.put_nowait(_SYNTH_PIPELINE_DONE)
                    except Full:
                        pass

        def triangulate(coordinator_thread: Thread) -> None:
            pair_index_offset = 0
            try:
                while True:
                    item = get_item(aligned_pair_queue, coordinator_thread)
                    if item is _SYNTH_PIPELINE_DONE:
                        put_item(result_queue, _SYNTH_PIPELINE_DONE)
                        break
                    if not isinstance(item, AlignedPoseChunkPair):
                        continue
                    t_start = perf_counter()
                    chunk_result = self._synthesizer.synthesize_chunk(
                        item,
                        camera_a=camera_a,
                        camera_b=camera_b,
                        camera_id_a=camera_id_a,
                        camera_id_b=camera_id_b,
                        max_delta_ms=max_delta_ms,
                        thresholds=thresholds,
                        pair_index_offset=pair_index_offset,
                    )
                    pair_index_offset += len(chunk_result.frames)
                    triangulate_timings.append(round((perf_counter() - t_start) * 1000.0, 3))
                    with metrics_lock:
                        pipeline_metrics["triangulatedChunks"] += 1
                        pipeline_metrics["triangulatedFrames"] += len(chunk_result.frames)
                    put_item(result_queue, chunk_result)
            except Exception as exc:
                set_worker_error(exc)
            finally:
                if stop_event.is_set():
                    try:
                        result_queue.put_nowait(_SYNTH_PIPELINE_DONE)
                    except Full:
                        pass

        # Build thread sets for each camera source
        all_threads: list[Thread] = []

        if extraction_opts_a is not None:
            producer_a = Thread(target=produce_frames, args=(extraction_opts_a, frame_queue_a, "A"), daemon=True)
            pose_source_a = Thread(target=infer_poses, args=(frame_queue_a, pose_queue_a, producer_a, "A"), daemon=True)
            all_threads.extend([producer_a, pose_source_a])
        else:
            assert preset_frames_a is not None
            pose_source_a = Thread(target=load_preset_poses, args=(preset_frames_a, pose_queue_a, "A"), daemon=True)
            all_threads.append(pose_source_a)

        if extraction_opts_b is not None:
            producer_b = Thread(target=produce_frames, args=(extraction_opts_b, frame_queue_b, "B"), daemon=True)
            pose_source_b = Thread(target=infer_poses, args=(frame_queue_b, pose_queue_b, producer_b, "B"), daemon=True)
            all_threads.extend([producer_b, pose_source_b])
        else:
            assert preset_frames_b is not None
            pose_source_b = Thread(target=load_preset_poses, args=(preset_frames_b, pose_queue_b, "B"), daemon=True)
            all_threads.append(pose_source_b)

        for t in all_threads:
            t.start()

        coordinator_thread = Thread(target=coordinate, args=(pose_source_a, pose_source_b), daemon=True)
        coordinator_thread.start()
        triangulator_thread = Thread(target=triangulate, args=(coordinator_thread,), daemon=True)
        triangulator_thread.start()

        # Main collector loop
        output_frames: list[dict[str, Any]] = []
        all_failure_counts: Counter[str] = Counter()
        all_reprojection_errors: list[float] = []
        total_success_joints = 0
        total_joints = 0
        chunk_alignment_summaries: list[dict[str, Any]] = []

        try:
            while True:
                item = get_item(result_queue, triangulator_thread)
                if item is _SYNTH_PIPELINE_DONE:
                    break
                if not isinstance(item, SynthesisChunkResult):
                    continue
                output_frames.extend(item.frames)
                all_failure_counts.update(item.failure_counts)
                all_reprojection_errors.extend(item.reprojection_errors)
                total_success_joints += item.success_joint_count
                total_joints += item.total_joint_count
                chunk_alignment_summaries.append(item.alignment_summary)
                processed = len(output_frames)
                ratio = 0.05 + 0.8 * (processed / estimated_total_frames) if estimated_total_frames else 0.5
                self._set_progress(
                    job, "streaming", 2, 5, min(ratio, 0.85),
                    stage_details=build_stage_details(processed),
                    processed_frames=processed,
                    total_frames=estimated_total_frames,
                )
        except Exception:
            stop_event.set()
            raise
        finally:
            stop_event.set()
            for t in all_threads + [coordinator_thread, triangulator_thread]:
                t.join()
            raise_if_worker_failed()

        # --- Stage 3: assemble and write artifact ---
        self._set_progress(job, "writing_artifacts", 4, 5, 0.9,
                           stage_details=build_stage_details())

        paired_frame_count = len(output_frames)
        total_unmatched_primary = sum(s.get("unmatchedPrimaryFrameCount", 0) for s in chunk_alignment_summaries)
        total_unmatched_secondary = sum(s.get("unmatchedSecondaryFrameCount", 0) for s in chunk_alignment_summaries)
        mean_ts_delta: float | None = None
        if chunk_alignment_summaries:
            deltas = [s["meanTimestampDeltaMs"] for s in chunk_alignment_summaries if s.get("meanTimestampDeltaMs") is not None]
            mean_ts_delta = round(sum(deltas) / len(deltas), 3) if deltas else None

        usable_frame_count = sum(
            1 for f in output_frames if int(f.get("quality", {}).get("successfulJointCount", 0)) > 0
        )
        mean_reproj = (
            round(sum(all_reprojection_errors) / len(all_reprojection_errors), 4)
            if all_reprojection_errors else None
        )
        quality_summary: dict[str, Any] = {
            "pairedFrameCount": paired_frame_count,
            "unmatchedPrimaryFrameCount": total_unmatched_primary,
            "unmatchedSecondaryFrameCount": total_unmatched_secondary,
            "maxTimestampDeltaMs": max_delta_ms,
            "meanTimestampDeltaMs": mean_ts_delta,
            "usableFrameCount": usable_frame_count,
            "validFrameRatio": round(usable_frame_count / paired_frame_count, 4) if paired_frame_count else 0.0,
            "usableJointRatio": round(total_success_joints / total_joints, 4) if total_joints else 0.0,
            "successfulJointCount": total_success_joints,
            "totalJointCount": total_joints,
            "meanReprojectionErrorPx": mean_reproj,
            "failureReasonCounts": dict(sorted(all_failure_counts.items())),
        }

        fps = self._synthesizer._fps_from_video_info({}) or 30.0
        try:
            if video_path_a:
                probe_a = self._video_reader.probe_metadata(video_path_a)
                fps = float(probe_a.get("fps") or probe_a.get("source_fps") or 30.0)
        except Exception:
            pass
        duration_ms = output_frames[-1]["timestampMs"] + 1000.0 / fps if output_frames else 0.0
        timeline = {
            "durationMs": round(duration_ms, 3),
            "fps": round(fps, 3),
            "totalFrames": paired_frame_count,
        }

        view_hint: dict[str, Any] = {
            "upAxis": "y",
            "upAxisDirection": "negative",
            "groundPlaneValue": 0.0,
            "frontView": self._synthesizer._front_view_hint(camera_a, camera_b),
        }
        skeleton3d: dict[str, Any] = {
            "schemaVersion": "skeleton3d.v1",
            "synthesisInfo": {
                "mode": "streaming",
                "sourceVideoPaths": [source_display_a, source_display_b],
                "cameraPair": [camera_id_a, camera_id_b],
                "calibrationRef": manifest.calibrationRef,
                "landmarkSet": manifest.landmarkSet,
                "coordinateSystem": manifest.outputCoordinateSystem,
                "viewHint": view_hint,
                "sync": {
                    "mode": manifest.sync.mode,
                    "timestampDomain": manifest.sync.timestampDomain,
                    "maxDeltaMs": max_delta_ms,
                    "fallback": manifest.sync.fallback,
                },
                "thresholds": manifest.thresholds.model_dump(),
            },
            "timeline": timeline,
            "frames": output_frames,
            "qualitySummary": quality_summary,
        }

        # Build 2D skeleton artifacts from assembled frames
        timeline_2d = {
            "fps": round(fps, 3),
            "totalFrames": len(assembled_frames_a),
            "durationMs": round(assembled_frames_a[-1]["timestampMs"], 3) if assembled_frames_a else 0.0,
        }
        skeleton_2d_a: dict[str, Any] = {
            "schemaVersion": "skeleton2d.v1",
            "cameraId": camera_id_a,
            "frames": assembled_frames_a,
            "timeline": {**timeline_2d, "totalFrames": len(assembled_frames_a)},
            "videoInfo": {},
        }
        skeleton_2d_b: dict[str, Any] = {
            "schemaVersion": "skeleton2d.v1",
            "cameraId": camera_id_b,
            "frames": assembled_frames_b,
            "timeline": {**timeline_2d, "totalFrames": len(assembled_frames_b)},
            "videoInfo": {},
        }

        # Run 2D biomechanics analysis per camera (general_motion mode)
        analysis_pipeline = AnalysisPipelineService()
        analysis_a: dict[str, Any] | None = None
        analysis_b: dict[str, Any] | None = None
        try:
            analysis_a = analysis_pipeline.analyze(skeleton_2d_a, exercise_type=None)
        except Exception:
            logger.warning("2D analysis for camera A failed", exc_info=True)
        try:
            analysis_b = analysis_pipeline.analyze(skeleton_2d_b, exercise_type=None)
        except Exception:
            logger.warning("2D analysis for camera B failed", exc_info=True)

        self._write_artifacts_and_complete(
            job, skeleton3d, job.request, total_steps=5,
            skeleton_2d_a=skeleton_2d_a,
            skeleton_2d_b=skeleton_2d_b,
            analysis_a=analysis_a,
            analysis_b=analysis_b,
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _write_artifacts_and_complete(
        self,
        job: SynthesisJobRecord,
        skeleton3d: dict[str, Any],
        request: SynthesisJobCreateRequest,
        *,
        total_steps: int = 6,
        skeleton_2d_a: dict[str, Any] | None = None,
        skeleton_2d_b: dict[str, Any] | None = None,
        analysis_a: dict[str, Any] | None = None,
        analysis_b: dict[str, Any] | None = None,
    ) -> None:
        skeleton3d_ref = self._artifact_repository.write_skeleton3d(job.job_id, skeleton3d)
        job.artifact_refs["skeleton3d"] = skeleton3d_ref

        skeleton_a_ref: dict[str, Any] | None = None
        if skeleton_2d_a is not None:
            skeleton_a_ref = self._artifact_repository.write_skeleton_a(job.job_id, skeleton_2d_a)
            job.artifact_refs["skeleton_a"] = skeleton_a_ref

        skeleton_b_ref: dict[str, Any] | None = None
        if skeleton_2d_b is not None:
            skeleton_b_ref = self._artifact_repository.write_skeleton_b(job.job_id, skeleton_2d_b)
            job.artifact_refs["skeleton_b"] = skeleton_b_ref

        debug_report = skeleton3d.get("debugReport")
        debug_ref: dict[str, Any] | None = None
        if isinstance(debug_report, dict):
            debug_ref = self._artifact_repository.write_debug_report(job.job_id, debug_report)
            job.artifact_refs["debugReport"] = debug_ref

        evaluation_ref: dict[str, Any] | None = None
        if request.options.runEvaluation:
            evaluation = self._evaluator.evaluate(
                skeleton3d=skeleton3d,
                gt_ref=request.options.gtRef or DEFAULT_GT_REF,
            )
            evaluation_ref = self._artifact_repository.write_evaluation(job.job_id, evaluation)
            job.artifact_refs["evaluation"] = evaluation_ref

        paired_frame_count = skeleton3d.get("qualitySummary", {}).get("pairedFrameCount", 0)
        job.result_summary = {
            "jobId": job.job_id,
            "schemaVersion": "synthesis_result_summary.v1",
            "skeleton3d": skeleton3d_ref["summary"],
            "skeletonA": skeleton_a_ref["summary"] if skeleton_a_ref else None,
            "skeletonB": skeleton_b_ref["summary"] if skeleton_b_ref else None,
            "analysisA": analysis_a,
            "analysisB": analysis_b,
            "debugReport": debug_ref["summary"] if debug_ref else None,
            "evaluation": evaluation_ref["summary"] if evaluation_ref else None,
            "artifactRefs": job.artifact_refs,
        }
        self._set_progress(
            job, "completed", total_steps, total_steps, 1.0,
            stage_details={
                "synthesis": {
                    "artifactRefs": job.artifact_refs,
                    "pairedFrameCount": paired_frame_count,
                }
            },
        )
        job.status = "completed"

    def _streaming_stage_details(self, job: SynthesisJobRecord, manifest: StreamingPairManifest) -> dict[str, Any]:
        return {
            "synthesis": {
                "mode": "streaming",
                "sourceVideoPaths": [
                    self._source_display_path(manifest.sources.A),
                    self._source_display_path(manifest.sources.B),
                ],
                "cameraPair": [manifest.sources.A.cameraId, manifest.sources.B.cameraId],
                "artifactRefs": job.artifact_refs,
            }
        }

    @staticmethod
    def _source_display_path(src: StreamingSource) -> str:
        return src.videoPath or f"preset:{src.presetEstimationId}" or "unknown"

    def _set_progress(
        self,
        job: SynthesisJobRecord,
        stage: str,
        current_step: int,
        total_steps: int,
        ratio: float,
        *,
        stage_details: dict[str, Any] | None = None,
        processed_frames: int | None = None,
        total_frames: int | None = None,
    ) -> None:
        job.status = stage
        job.progress = JobProgress(
            stage=stage,
            currentStep=current_step,
            totalSteps=total_steps,
            ratio=ratio,
            stageDetails=stage_details or {},
            processedFrames=processed_frames,
            totalFrames=total_frames,
        )

    def _fail_job(self, job: SynthesisJobRecord, exc: Exception) -> None:
        logger.error("Synthesis job %s failed: %s", job.job_id, exc, exc_info=True)
        job.status = "failed"
        job.progress = JobProgress(
            stage="failed",
            currentStep=0,
            totalSteps=6,
            ratio=0.0,
            stageDetails=job.progress.stageDetails if job.progress else {},
        )
        job.error = {
            "code": f"synthesis_{exc.__class__.__name__}",
            "message": str(exc),
        }

    def _get_job(self, job_id: str) -> SynthesisJobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Synthesis job not found.")
        return job

    def _get_completed_job(self, job_id: str) -> SynthesisJobRecord:
        job = self._get_job(job_id)
        if job.status != "completed":
            raise HTTPException(status_code=409, detail="Synthesis job result is not ready.")
        return job
