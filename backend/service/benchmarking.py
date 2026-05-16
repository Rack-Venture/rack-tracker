from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from config.config import BENCHMARK_DIR
from schema.benchmark import (
    BenchmarkFrameMetric,
    BenchmarkLlmCallResult,
    BenchmarkLlmPromptDiagnostics,
    BenchmarkPipelineSummary,
    BenchmarkQualitySummary,
    BenchmarkResult,
    BenchmarkRunMetadata,
    BenchmarkStageStats,
    BenchmarkStartupSummary,
    BenchmarkStorageRefs,
    BenchmarkTimingSummary,
)
from schema.frame import FrameExtractionOptions, FrameExtractionResult
from schema.pose import PoseChunk, PoseInferenceResult


class PoseChunkBenchmarkCollector:
    def __init__(self, *, spool_path: Path | None = None) -> None:
        self._spool_path = spool_path
        self._spool_handle = spool_path.open("w", encoding="utf-8") if spool_path is not None else None

    @property
    def spool_path(self) -> Path | None:
        return self._spool_path

    def add_pose_chunk(self, pose_chunk: PoseChunk) -> None:
        for frame in pose_chunk.frames:
            if frame.benchmark is None:
                continue
            metric = BenchmarkFrameMetric.model_validate(frame.benchmark.to_dict())
            if self._spool_handle is not None:
                self._spool_handle.write(json.dumps(metric.model_dump(), ensure_ascii=False))
                self._spool_handle.write("\n")

    def finalize(self) -> str | None:
        if self._spool_handle is not None:
            self._spool_handle.flush()
            self._spool_handle.close()
            self._spool_handle = None
        return str(self._spool_path) if self._spool_path is not None else None


class BenchmarkService:
    def build_result(
        self,
        *,
        benchmark_run_id: str,
        source_video_path: str,
        job_metadata: dict[str, Any],
        extraction_options: FrameExtractionOptions,
        extraction_result: FrameExtractionResult,
        inference_result: PoseInferenceResult,
        analysis_result: dict[str, Any],
        llm_prompt_diagnostics: dict[str, Any] | None,
        llm_call_result: dict[str, Any] | None,
        frame_extraction_ms: float,
        analysis_ms: float,
        llm_feedback_ms: float | None,
        startup_summary: dict[str, Any] | None,
        pipeline_summary: dict[str, Any] | None,
        total_elapsed_ms: float,
        started_at: datetime,
        completed_at: datetime,
        frame_metrics: list[BenchmarkFrameMetric] | None = None,
        frame_metrics_path: str | Path | None = None,
    ) -> BenchmarkResult:
        resolved_frame_metrics = frame_metrics
        if resolved_frame_metrics is None and frame_metrics_path is not None:
            resolved_frame_metrics = self.load_frame_metrics(frame_metrics_path)
        if resolved_frame_metrics is None:
            resolved_frame_metrics = [
                BenchmarkFrameMetric.model_validate(frame.benchmark.to_dict())
                for frame in inference_result.frames
                if frame.benchmark is not None
            ]

        mp_image_creation_total_ms = round(
            sum(frame.mpImageCreationMs for frame in resolved_frame_metrics),
            3,
        )
        inference_total_ms = round(sum(frame.inferenceMs for frame in resolved_frame_metrics), 3)
        serialization_total_ms = round(sum(frame.serializationMs for frame in resolved_frame_metrics), 3)

        stage_stats = self._build_stage_stats(
            frame_metrics=resolved_frame_metrics,
            frame_extraction_ms=frame_extraction_ms,
            analysis_ms=analysis_ms,
            llm_feedback_ms=llm_feedback_ms,
            pipeline_summary=pipeline_summary,
            total_elapsed_ms=total_elapsed_ms,
        )
        quality_summary = self._build_quality_summary(
            frame_metrics=resolved_frame_metrics,
            frame_count=inference_result.frame_count,
            detected_frame_count=inference_result.detected_frame_count,
            analysis_result=analysis_result,
        )

        effective_sampling_fps = self._resolve_effective_sampling_fps(
            extraction_options=extraction_options,
            extraction_result=extraction_result,
        )
        sample_interval_ms = self._resolve_sample_interval_ms(effective_sampling_fps)
        result = BenchmarkResult(
            run=BenchmarkRunMetadata(
                benchmarkRunId=benchmark_run_id,
                sourceVideoPath=source_video_path,
                videoFingerprint=self._fingerprint(
                    source_video_path,
                    extraction_result.frame_count,
                    extraction_result.source_fps,
                ),
                sourceVideoFps=round(extraction_result.source_fps, 3),
                inferenceBackend=inference_result.inference_backend,
                requestedSamplingFps=job_metadata.get("requestedSamplingFps"),
                effectiveSamplingFps=round(effective_sampling_fps, 3),
                requestedDelegate=inference_result.requested_delegate,
                actualDelegate=inference_result.actual_delegate,
                delegateFallbackApplied=inference_result.delegate_fallback_applied,
                delegateErrors=inference_result.delegate_errors,
                modelVariant=Path(inference_result.model_name).stem.replace("pose_landmarker_", ""),
                runningMode=inference_result.running_mode,
                frameCount=inference_result.frame_count,
                sampleIntervalMs=sample_interval_ms,
                startedAt=self._to_iso(started_at),
                completedAt=self._to_iso(completed_at),
            ),
            timingSummary=BenchmarkTimingSummary(
                frameExtractionMs=round(frame_extraction_ms, 3),
                mpImageCreationMs=mp_image_creation_total_ms,
                inferenceMs=round(inference_total_ms, 3),
                serializationMs=round(serialization_total_ms, 3),
                analysisMs=round(analysis_ms, 3),
                llmFeedbackMs=round(llm_feedback_ms, 3) if llm_feedback_ms is not None else None,
                startupSummary=(
                    BenchmarkStartupSummary.model_validate(startup_summary)
                    if startup_summary
                    else None
                ),
                pipelineSummary=(
                    BenchmarkPipelineSummary.model_validate(pipeline_summary)
                    if pipeline_summary
                    else None
                ),
                totalElapsedMs=round(total_elapsed_ms, 3),
                stageStats=stage_stats,
            ),
            qualitySummary=quality_summary,
            comparisonTags=self._build_comparison_tags(
                model_variant=Path(inference_result.model_name).stem.replace("pose_landmarker_", ""),
                requested_delegate=inference_result.requested_delegate,
                actual_delegate=inference_result.actual_delegate,
                delegate_fallback_applied=inference_result.delegate_fallback_applied,
                sample_interval_ms=sample_interval_ms,
            ),
            frameMetrics=resolved_frame_metrics,
            llmPromptDiagnostics=(
                BenchmarkLlmPromptDiagnostics.model_validate(llm_prompt_diagnostics)
                if llm_prompt_diagnostics
                else None
            ),
            llmCallResult=(
                BenchmarkLlmCallResult.model_validate(llm_call_result)
                if llm_call_result
                else None
            ),
        )
        return self.save_result(result)

    def save_result(self, result: BenchmarkResult) -> BenchmarkResult:
        summary_path = BENCHMARK_DIR / f"{result.run.benchmarkRunId}.summary.json"
        frame_metrics_path = BENCHMARK_DIR / f"{result.run.benchmarkRunId}.frames.json"

        summary_payload = {
            "run": result.run.model_dump(),
            "timingSummary": result.timingSummary.model_dump(),
            "qualitySummary": result.qualitySummary.model_dump(),
            "comparisonTags": result.comparisonTags,
            "llmPromptDiagnostics": (
                result.llmPromptDiagnostics.model_dump()
                if result.llmPromptDiagnostics is not None
                else None
            ),
            "llmCallResult": (
                result.llmCallResult.model_dump()
                if result.llmCallResult is not None
                else None
            ),
        }
        frame_payload = {
            "benchmarkRunId": result.run.benchmarkRunId,
            "frameMetrics": [metric.model_dump() for metric in result.frameMetrics],
        }

        summary_path.write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        frame_metrics_path.write_text(
            json.dumps(frame_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result.storage = BenchmarkStorageRefs(
            summaryPath=str(summary_path),
            frameMetricsPath=str(frame_metrics_path),
        )
        return result

    def load_frame_metrics(self, frame_metrics_path: str | Path) -> list[BenchmarkFrameMetric]:
        path = Path(frame_metrics_path)
        if not path.exists():
            return []

        if path.suffix == ".jsonl":
            return [
                BenchmarkFrameMetric.model_validate(json.loads(line))
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        payload = json.loads(path.read_text(encoding="utf-8"))
        frame_metrics_payload = payload.get("frameMetrics", payload if isinstance(payload, list) else [])
        return [
            BenchmarkFrameMetric.model_validate(metric)
            for metric in frame_metrics_payload
        ]

    def load_saved_frame_metrics_payload(self, frame_metrics_path: str | Path) -> list[dict[str, Any]]:
        return [
            metric.model_dump()
            for metric in self.load_frame_metrics(frame_metrics_path)
        ]

    def _build_stage_stats(
        self,
        *,
        frame_metrics: list[BenchmarkFrameMetric],
        frame_extraction_ms: float,
        analysis_ms: float,
        llm_feedback_ms: float | None,
        pipeline_summary: dict[str, Any] | None,
        total_elapsed_ms: float,
    ) -> list[BenchmarkStageStats]:
        stages = [
            self._fixed_stage_stats(
                key="frame_extraction",
                label="Frame Extraction",
                total_ms=frame_extraction_ms,
                total_elapsed_ms=total_elapsed_ms,
            ),
            self._variable_stage_stats(
                key="mp_image_creation",
                label="MP Image Creation",
                values=[metric.mpImageCreationMs for metric in frame_metrics],
                total_elapsed_ms=total_elapsed_ms,
            ),
            self._variable_stage_stats(
                key="inference",
                label="Inference",
                values=[metric.inferenceMs for metric in frame_metrics],
                total_elapsed_ms=total_elapsed_ms,
            ),
            self._variable_stage_stats(
                key="serialization",
                label="Serialization",
                values=[metric.serializationMs for metric in frame_metrics],
                total_elapsed_ms=total_elapsed_ms,
            ),
            self._fixed_stage_stats(
                key="analysis",
                label="Analysis",
                total_ms=analysis_ms,
                total_elapsed_ms=total_elapsed_ms,
            ),
        ]
        if pipeline_summary:
            pipeline_stages = [
                self._pipeline_stage_stats(
                    key="frame_read",
                    label="Frame read",
                    total_ms=pipeline_summary.get("totalChunkReadMs"),
                    average_ms=pipeline_summary.get("avgChunkReadMs"),
                    p95_ms=pipeline_summary.get("p95ChunkReadMs"),
                    total_elapsed_ms=total_elapsed_ms,
                ),
                self._pipeline_stage_stats(
                    key="pose_infer",
                    label="Pose infer",
                    total_ms=pipeline_summary.get("totalChunkInferenceMs"),
                    average_ms=pipeline_summary.get("avgChunkInferenceMs"),
                    p95_ms=pipeline_summary.get("p95ChunkInferenceMs"),
                    total_elapsed_ms=total_elapsed_ms,
                ),
                self._pipeline_stage_stats(
                    key="skeleton_collect",
                    label="Skeleton collect",
                    total_ms=pipeline_summary.get("totalSkeletonChunkMs"),
                    average_ms=pipeline_summary.get("avgSkeletonChunkMs"),
                    p95_ms=pipeline_summary.get("p95SkeletonChunkMs"),
                    total_elapsed_ms=total_elapsed_ms,
                ),
                self._pipeline_stage_stats(
                    key="benchmark_collect",
                    label="Benchmark collect",
                    total_ms=pipeline_summary.get("totalBenchmarkChunkMs"),
                    average_ms=pipeline_summary.get("avgBenchmarkChunkMs"),
                    p95_ms=pipeline_summary.get("p95BenchmarkChunkMs"),
                    total_elapsed_ms=total_elapsed_ms,
                ),
            ]
            stages.extend(stage for stage in pipeline_stages if stage is not None)
        if llm_feedback_ms is not None:
            stages.append(
                self._fixed_stage_stats(
                    key="llm_feedback",
                    label="LLM Feedback",
                    total_ms=llm_feedback_ms,
                    total_elapsed_ms=total_elapsed_ms,
                )
            )
        return stages

    def _build_quality_summary(
        self,
        *,
        frame_metrics: list[BenchmarkFrameMetric],
        frame_count: int,
        detected_frame_count: int,
        analysis_result: dict[str, Any],
    ) -> BenchmarkQualitySummary:
        visibility_values = [
            metric.avgVisibility for metric in frame_metrics if metric.avgVisibility is not None
        ]
        min_visibility_values = [
            metric.minVisibility for metric in frame_metrics if metric.minVisibility is not None
        ]
        low_visibility_count = sum(
            1 for metric in frame_metrics if metric.avgVisibility is not None and metric.avgVisibility < 0.8
        )

        consecutive_missed_pose_max = 0
        current_missed_pose = 0
        for metric in frame_metrics:
            if metric.poseDetected:
                consecutive_missed_pose_max = max(consecutive_missed_pose_max, current_missed_pose)
                current_missed_pose = 0
                continue
            current_missed_pose += 1
        consecutive_missed_pose_max = max(consecutive_missed_pose_max, current_missed_pose)

        return BenchmarkQualitySummary(
            poseDetectedRatio=round(detected_frame_count / max(frame_count, 1), 4),
            detectedFrameCount=detected_frame_count,
            avgVisibility=round(sum(visibility_values) / len(visibility_values), 4)
            if visibility_values
            else None,
            minVisibility=round(min(min_visibility_values), 4) if min_visibility_values else None,
            lowVisibilityFrameRatio=round(low_visibility_count / max(frame_count, 1), 4),
            consecutiveMissedPoseMax=consecutive_missed_pose_max,
            analysisSuccess=bool(analysis_result),
        )

    def _build_comparison_tags(
        self,
        *,
        model_variant: str,
        requested_delegate: str,
        actual_delegate: str,
        delegate_fallback_applied: bool,
        sample_interval_ms: float,
    ) -> list[str]:
        tags = [
            f"model:{model_variant}",
            f"delegate-requested:{requested_delegate}",
            f"delegate-actual:{actual_delegate}",
            f"sampling-ms:{round(sample_interval_ms, 2)}",
        ]
        tags.append("delegate:fallback" if delegate_fallback_applied else "delegate:direct")
        return tags

    def _variable_stage_stats(
        self,
        *,
        key: str,
        label: str,
        values: list[float],
        total_elapsed_ms: float,
    ) -> BenchmarkStageStats:
        total_ms = round(sum(values), 3)
        return BenchmarkStageStats(
            key=key,
            label=label,
            totalMs=total_ms,
            averageMs=round(sum(values) / len(values), 3) if values else 0.0,
            medianMs=round(float(median(values)), 3) if values else 0.0,
            p95Ms=round(self._percentile(values, 95), 3) if values else 0.0,
            shareRatio=round(total_ms / max(total_elapsed_ms, 0.001), 4),
        )

    def _fixed_stage_stats(
        self,
        *,
        key: str,
        label: str,
        total_ms: float,
        total_elapsed_ms: float,
    ) -> BenchmarkStageStats:
        rounded_total = round(total_ms, 3)
        return BenchmarkStageStats(
            key=key,
            label=label,
            totalMs=rounded_total,
            averageMs=None,
            medianMs=None,
            p95Ms=None,
            shareRatio=round(rounded_total / max(total_elapsed_ms, 0.001), 4),
        )

    def _pipeline_stage_stats(
        self,
        *,
        key: str,
        label: str,
        total_ms: float | None,
        average_ms: float | None,
        p95_ms: float | None,
        total_elapsed_ms: float,
    ) -> BenchmarkStageStats | None:
        if total_ms is None:
            return None
        rounded_total = round(float(total_ms), 3)
        return BenchmarkStageStats(
            key=key,
            label=label,
            totalMs=rounded_total,
            averageMs=round(float(average_ms), 3) if average_ms is not None else None,
            medianMs=None,
            p95Ms=round(float(p95_ms), 3) if p95_ms is not None else None,
            shareRatio=round(rounded_total / max(total_elapsed_ms, 0.001), 4),
        )

    def _resolve_effective_sampling_fps(
        self,
        *,
        extraction_options: FrameExtractionOptions,
        extraction_result: FrameExtractionResult,
    ) -> float:
        return float(extraction_options.target_fps or extraction_result.source_fps)

    def _resolve_sample_interval_ms(self, effective_sampling_fps: float) -> float:
        return round(1000.0 / max(effective_sampling_fps, 0.001), 3)

    def _fingerprint(
        self,
        source_video_path: str,
        frame_count: int | None,
        source_fps: float,
    ) -> str:
        payload = f"{source_video_path}|{frame_count}|{source_fps}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _percentile(self, values: list[float], percentile_value: int) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return float(sorted_values[0])
        index = (len(sorted_values) - 1) * (percentile_value / 100.0)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        weight = index - lower_index
        lower = float(sorted_values[lower_index])
        upper = float(sorted_values[upper_index])
        return lower + (upper - lower) * weight

    def _to_iso(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
