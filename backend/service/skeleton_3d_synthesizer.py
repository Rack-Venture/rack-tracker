from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from schema.pose import AlignedPoseChunkPair
from schema.synthesis import SynthesisInput, SynthesisThresholds
from service.camera_calibration import CameraCalibrationService
from service.frame_alignment import FrameAlignmentService
from service.landmark_observation import (
    LandmarkObservation,
    LandmarkObservationBuilder,
    LandmarkObservationError,
    POSE_LANDMARK_NAMES,
)
from service.skeleton_artifact_repository import SkeletonArtifactRepository
from service.triangulation import TriangulatedJoint, TriangulationService


DEBUG_SAMPLE_FRAME_LIMIT = 10
DEBUG_LANDMARK_INDICES = {0, 11, 12, 23, 24, 27, 28}


@dataclass(slots=True)
class SynthesisChunkResult:
    chunk_index: int
    frames: list[dict[str, Any]]
    success_joint_count: int
    total_joint_count: int
    reprojection_errors: list[float]
    failure_counts: Counter[str]
    alignment_summary: dict[str, Any]


class Skeleton3DSynthesisError(Exception):
    pass


class Skeleton3DSynthesizer:
    def __init__(
        self,
        *,
        artifact_repository: SkeletonArtifactRepository,
        calibration_service: CameraCalibrationService | None = None,
        alignment_service: FrameAlignmentService | None = None,
        observation_builder: LandmarkObservationBuilder | None = None,
        triangulation_service: TriangulationService | None = None,
    ) -> None:
        self._artifact_repository = artifact_repository
        self._calibration_service = calibration_service or CameraCalibrationService()
        self._alignment_service = alignment_service or FrameAlignmentService()
        self._observation_builder = observation_builder or LandmarkObservationBuilder()
        self._triangulation_service = triangulation_service or TriangulationService()

    def synthesize(self, synthesis_input: SynthesisInput) -> dict[str, Any]:
        skeleton_a = self._artifact_repository.read_skeleton(synthesis_input.sourceJobIdA)
        skeleton_b = self._artifact_repository.read_skeleton(synthesis_input.sourceJobIdB)
        video_info_a = dict(skeleton_a.get("videoInfo", {}))
        video_info_b = dict(skeleton_b.get("videoInfo", {}))
        source_bindings = self._validate_source_bindings(
            skeleton_a=skeleton_a,
            skeleton_b=skeleton_b,
            video_info_a=video_info_a,
            video_info_b=video_info_b,
            synthesis_input=synthesis_input,
        )
        frames_a = self._frames(skeleton_a, synthesis_input.sourceJobIdA)
        frames_b = self._frames(skeleton_b, synthesis_input.sourceJobIdB)
        camera_a, camera_b = self._calibration_service.load_pair(
            synthesis_input.calibrationRef,
            synthesis_input.cameraIdA,
            synthesis_input.cameraIdB,
        )
        max_delta_ms = self._alignment_service.resolve_max_delta_ms(
            synthesis_input.sync.maxDeltaMs,
            fps_a=self._fps_from_video_info(video_info_a),
            fps_b=self._fps_from_video_info(video_info_b),
        )
        pairs, alignment_summary = self._alignment_service.align(
            frames_a,
            frames_b,
            max_delta_ms=max_delta_ms,
        )
        debug_report = self._build_debug_report(
            synthesis_input=synthesis_input,
            source_bindings=source_bindings,
            pairs=pairs,
            alignment_summary=alignment_summary,
            max_delta_ms=max_delta_ms,
        )

        failure_counts: Counter[str] = Counter()
        reprojection_errors: list[float] = []
        output_frames: list[dict[str, Any]] = []
        success_joint_count = 0
        total_joint_count = 0

        for pair in pairs:
            frame_payload, frame_success_count, frame_total_count, frame_errors = self._synthesize_frame(
                pair.primary_frame,
                pair.secondary_frame,
                pair_index=len(output_frames),
                video_info_a=video_info_a,
                video_info_b=video_info_b,
                camera_a=camera_a,
                camera_b=camera_b,
                camera_id_a=synthesis_input.cameraIdA,
                camera_id_b=synthesis_input.cameraIdB,
                thresholds=synthesis_input.thresholds,
                timestamp_delta_ms=pair.timestamp_delta_ms,
                failure_counts=failure_counts,
                debug_report=debug_report,
            )
            success_joint_count += frame_success_count
            total_joint_count += frame_total_count
            reprojection_errors.extend(frame_errors)
            output_frames.append(frame_payload)

        quality_summary = self._build_quality_summary(
            output_frames=output_frames,
            alignment_summary=alignment_summary,
            success_joint_count=success_joint_count,
            total_joint_count=total_joint_count,
            reprojection_errors=reprojection_errors,
            failure_counts=failure_counts,
        )
        self._finalize_debug_report(debug_report, quality_summary)
        return {
            "schemaVersion": "skeleton3d.v1",
            "synthesisInfo": {
                "sourceJobIds": [
                    synthesis_input.sourceJobIdA,
                    synthesis_input.sourceJobIdB,
                ],
                "cameraPair": [
                    synthesis_input.cameraIdA,
                    synthesis_input.cameraIdB,
                ],
                "sourceBindings": source_bindings,
                "calibrationRef": synthesis_input.calibrationRef,
                "landmarkSet": synthesis_input.landmarkSet,
                "coordinateSystem": synthesis_input.outputCoordinateSystem,
                "viewHint": {
                    "upAxis": "y",
                    "upAxisDirection": "negative",
                    "groundPlaneValue": 0.0,
                    "frontView": self._front_view_hint(camera_a, camera_b),
                },
                "sync": {
                    "mode": synthesis_input.sync.mode,
                    "timestampDomain": synthesis_input.sync.timestampDomain,
                    "maxDeltaMs": max_delta_ms,
                    "fallback": synthesis_input.sync.fallback,
                },
                "thresholds": synthesis_input.thresholds.model_dump(),
            },
            "timeline": self._build_timeline(output_frames, video_info_a, video_info_b),
            "frames": output_frames,
            "qualitySummary": quality_summary,
            "debugReport": debug_report,
        }

    def _validate_source_bindings(
        self,
        *,
        skeleton_a: dict[str, Any],
        skeleton_b: dict[str, Any],
        video_info_a: dict[str, Any],
        video_info_b: dict[str, Any],
        synthesis_input: SynthesisInput,
    ) -> list[dict[str, Any]]:
        binding_a = self._source_binding_summary(
            slot="A",
            skeleton=skeleton_a,
            video_info=video_info_a,
            source_job_id=synthesis_input.sourceJobIdA,
            request_camera_id=synthesis_input.cameraIdA,
            request_calibration_ref=synthesis_input.calibrationRef,
        )
        binding_b = self._source_binding_summary(
            slot="B",
            skeleton=skeleton_b,
            video_info=video_info_b,
            source_job_id=synthesis_input.sourceJobIdB,
            request_camera_id=synthesis_input.cameraIdB,
            request_calibration_ref=synthesis_input.calibrationRef,
        )
        return [binding_a, binding_b]

    def _source_binding_summary(
        self,
        *,
        slot: str,
        skeleton: dict[str, Any],
        video_info: dict[str, Any],
        source_job_id: str,
        request_camera_id: str,
        request_calibration_ref: str,
    ) -> dict[str, Any]:
        binding = self._coerce_dict(skeleton.get("cameraBinding")) or self._coerce_dict(
            video_info.get("cameraBinding")
        )
        artifact_camera_id = self._first_text(
            binding.get("sourceCameraId") if binding else None,
            video_info.get("cameraId"),
        )
        calibration_camera_id = self._first_text(
            binding.get("calibrationCameraId") if binding else None,
            artifact_camera_id,
        )
        calibration_ref = self._first_text(binding.get("calibrationRef") if binding else None)
        binding_source = self._first_text(binding.get("bindingSource") if binding else None) or (
            "declared" if artifact_camera_id else "legacy_missing"
        )

        mismatches: list[dict[str, Any]] = []
        self._append_mismatch(
            mismatches,
            field="sourceCameraId",
            expected=request_camera_id,
            actual=artifact_camera_id,
        )
        self._append_mismatch(
            mismatches,
            field="calibrationCameraId",
            expected=request_camera_id,
            actual=calibration_camera_id,
        )
        if calibration_ref is not None:
            self._append_mismatch(
                mismatches,
                field="calibrationRef",
                expected=self._normalize_ref(request_calibration_ref),
                actual=self._normalize_ref(calibration_ref),
            )

        summary = {
            "slot": slot,
            "sourceJobId": source_job_id,
            "sourceVideoName": video_info.get("displayName"),
            "sourceVideoPath": video_info.get("videoSrc"),
            "artifactCameraId": artifact_camera_id,
            "requestCameraId": request_camera_id,
            "calibrationCameraId": calibration_camera_id,
            "calibrationRef": calibration_ref,
            "bindingSource": binding_source,
            "mismatch": bool(mismatches),
            "mismatches": mismatches,
        }
        if mismatches:
            details = ", ".join(
                f"{item['field']} expected {item['expected']} got {item['actual']}"
                for item in mismatches
            )
            raise Skeleton3DSynthesisError(
                f"camera_binding_mismatch for source {slot} ({source_job_id}): {details}"
            )
        return summary

    def _append_mismatch(
        self,
        mismatches: list[dict[str, Any]],
        *,
        field: str,
        expected: str | None,
        actual: str | None,
    ) -> None:
        if expected is None or actual is None:
            return
        if expected != actual:
            mismatches.append({"field": field, "expected": expected, "actual": actual})

    def _front_view_hint(self, camera_a: Any, camera_b: Any) -> dict[str, Any]:
        center_a = (-camera_a.R.T @ camera_a.t).reshape(3)
        center_b = (-camera_b.R.T @ camera_b.t).reshape(3)
        mid_x = float((center_a[0] + center_b[0]) / 2)
        mid_z = float((center_a[2] + center_b[2]) / 2)
        return {
            "cameraMidpointXZ": [round(mid_x, 1), round(mid_z, 1)],
            "eyeHeightWorld": -150.0,
        }

    def _coerce_dict(self, value: Any) -> dict[str, Any] | None:
        return value if isinstance(value, dict) else None

    def _first_text(self, *values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _normalize_ref(self, value: str) -> str:
        stripped = value.strip()
        path = Path(stripped)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        try:
            return str(path.resolve()).replace("\\", "/")
        except OSError:
            return stripped.replace("\\", "/")

    def _synthesize_frame(
        self,
        frame_a: dict[str, Any],
        frame_b: dict[str, Any],
        *,
        pair_index: int,
        video_info_a: dict[str, Any],
        video_info_b: dict[str, Any],
        camera_a: Any,
        camera_b: Any,
        camera_id_a: str,
        camera_id_b: str,
        thresholds: SynthesisThresholds,
        timestamp_delta_ms: float,
        failure_counts: Counter[str],
        debug_report: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], int, int, list[float]]:
        joints: list[dict[str, Any]] = []
        frame_errors: list[float] = []
        frame_success_count = 0

        for landmark_index, landmark_name in enumerate(POSE_LANDMARK_NAMES):
            if not frame_a.get("poseDetected", False) or not frame_b.get("poseDetected", False):
                failure_counts["pose_not_detected"] += 1
                joints.append(
                    self._failed_joint_payload(
                        landmark_name,
                        landmark_index,
                        "pose_not_detected",
                        camera_id_a=camera_id_a,
                        camera_id_b=camera_id_b,
                    )
                )
                continue

            observation_a: LandmarkObservation | None = None
            observation_b: LandmarkObservation | None = None
            try:
                observation_a = self._observation_builder.build(
                    frame_a,
                    landmark_index=landmark_index,
                    video_info=video_info_a,
                    camera_model=camera_a,
                )
                observation_b = self._observation_builder.build(
                    frame_b,
                    landmark_index=landmark_index,
                    video_info=video_info_b,
                    camera_model=camera_b,
                )
                joint = self._triangulation_service.triangulate_joint(
                    observation_a=observation_a,
                    observation_b=observation_b,
                    camera_a=camera_a,
                    camera_b=camera_b,
                    thresholds=thresholds,
                )
            except LandmarkObservationError:
                failure_counts["missing_landmark"] += 1
                joints.append(
                    self._failed_joint_payload(
                        landmark_name,
                        landmark_index,
                        "missing_landmark",
                        camera_id_a=camera_id_a,
                        camera_id_b=camera_id_b,
                    )
                )
                continue
            except Exception:
                failure_counts["triangulation_error"] += 1
                joints.append(
                    self._failed_joint_payload(
                        landmark_name,
                        landmark_index,
                        "triangulation_error",
                        camera_id_a=camera_id_a,
                        camera_id_b=camera_id_b,
                    )
                )
                continue

            if joint.success:
                frame_success_count += 1
            elif joint.failure_reason:
                failure_counts[joint.failure_reason] += 1
            error = joint.mean_reprojection_error_px
            if error is not None:
                frame_errors.append(error)
            if debug_report is not None:
                self._append_debug_samples(
                    debug_report=debug_report,
                    pair_index=pair_index,
                    frame_a=frame_a,
                    frame_b=frame_b,
                    landmark_index=landmark_index,
                    landmark_name=landmark_name,
                    joint=joint,
                    observation_a=observation_a,
                    observation_b=observation_b,
                    camera_a=camera_a,
                    camera_b=camera_b,
                    camera_id_a=camera_id_a,
                    camera_id_b=camera_id_b,
                )
            joints.append(
                self._triangulation_service.joint_to_payload(
                    joint=joint,
                    observation_a=observation_a,
                    observation_b=observation_b,
                    camera_id_a=camera_id_a,
                    camera_id_b=camera_id_b,
                )
            )

        frame_total_count = len(POSE_LANDMARK_NAMES)
        return (
            {
                "frameIndex": self._frame_index(frame_a),
                "timestampMs": self._timestamp(frame_a),
                "timestampDeltaMs": round(timestamp_delta_ms, 4),
                "source": {
                    camera_id_a: self._source_frame_payload(frame_a),
                    camera_id_b: self._source_frame_payload(frame_b),
                },
                "joints": joints,
                "quality": {
                    "successfulJointCount": frame_success_count,
                    "failedJointCount": frame_total_count - frame_success_count,
                    "usableJointRatio": round(frame_success_count / frame_total_count, 4)
                    if frame_total_count
                    else 0.0,
                    "meanReprojectionErrorPx": self._mean(frame_errors),
                },
            },
            frame_success_count,
            frame_total_count,
            frame_errors,
        )

    def synthesize_chunk(
        self,
        aligned_pair: AlignedPoseChunkPair,
        *,
        camera_a: Any,
        camera_b: Any,
        camera_id_a: str,
        camera_id_b: str,
        max_delta_ms: float,
        thresholds: SynthesisThresholds,
        pair_index_offset: int = 0,
        video_info_a: dict[str, Any] | None = None,
        video_info_b: dict[str, Any] | None = None,
        debug_report: dict[str, Any] | None = None,
    ) -> SynthesisChunkResult:
        frames_a = [f.to_dict() for f in aligned_pair.primary.chunk.frames]
        frames_b = [f.to_dict() for f in aligned_pair.secondary.chunk.frames]
        video_info_a = video_info_a or {}
        video_info_b = video_info_b or {}

        pairs, alignment_summary = self._alignment_service.align(
            frames_a,
            frames_b,
            max_delta_ms=max_delta_ms,
        )

        failure_counts: Counter[str] = Counter()
        reprojection_errors: list[float] = []
        output_frames: list[dict[str, Any]] = []
        success_joint_count = 0
        total_joint_count = 0

        for pair in pairs:
            pair_index = pair_index_offset + len(output_frames)
            frame_payload, frame_success_count, frame_total_count, frame_errors = self._synthesize_frame(
                pair.primary_frame,
                pair.secondary_frame,
                pair_index=pair_index,
                video_info_a=video_info_a,
                video_info_b=video_info_b,
                camera_a=camera_a,
                camera_b=camera_b,
                camera_id_a=camera_id_a,
                camera_id_b=camera_id_b,
                thresholds=thresholds,
                timestamp_delta_ms=pair.timestamp_delta_ms,
                failure_counts=failure_counts,
                debug_report=debug_report,
            )
            success_joint_count += frame_success_count
            total_joint_count += frame_total_count
            reprojection_errors.extend(frame_errors)
            output_frames.append(frame_payload)

        return SynthesisChunkResult(
            chunk_index=aligned_pair.chunk_index,
            frames=output_frames,
            success_joint_count=success_joint_count,
            total_joint_count=total_joint_count,
            reprojection_errors=reprojection_errors,
            failure_counts=failure_counts,
            alignment_summary=alignment_summary,
        )

    def _frames(self, skeleton: dict[str, Any], source_job_id: str) -> list[dict[str, Any]]:
        frames = skeleton.get("frames", [])
        if not isinstance(frames, list):
            raise Skeleton3DSynthesisError(f"Skeleton frames are invalid for {source_job_id}.")
        return frames

    def _build_quality_summary(
        self,
        *,
        output_frames: list[dict[str, Any]],
        alignment_summary: dict[str, Any],
        success_joint_count: int,
        total_joint_count: int,
        reprojection_errors: list[float],
        failure_counts: Counter[str],
    ) -> dict[str, Any]:
        usable_frame_count = sum(
            1
            for frame in output_frames
            if int(frame.get("quality", {}).get("successfulJointCount", 0)) > 0
        )
        return {
            **alignment_summary,
            "usableFrameCount": usable_frame_count,
            "validFrameRatio": round(usable_frame_count / len(output_frames), 4)
            if output_frames
            else 0.0,
            "usableJointRatio": round(success_joint_count / total_joint_count, 4)
            if total_joint_count
            else 0.0,
            "successfulJointCount": success_joint_count,
            "totalJointCount": total_joint_count,
            "meanReprojectionErrorPx": self._mean(reprojection_errors),
            "failureReasonCounts": dict(sorted(failure_counts.items())),
        }

    def _build_debug_report(
        self,
        *,
        synthesis_input: SynthesisInput,
        source_bindings: list[dict[str, Any]],
        pairs: list[Any],
        alignment_summary: dict[str, Any],
        max_delta_ms: float,
    ) -> dict[str, Any]:
        return {
            "schemaVersion": "synthesis_debug_report.v1",
            "synthesisPairManifestDebug": {
                "schemaVersion": "synthesis_pair_manifest_debug.v1",
                "sourceJobIds": [
                    synthesis_input.sourceJobIdA,
                    synthesis_input.sourceJobIdB,
                ],
                "cameraPair": [
                    synthesis_input.cameraIdA,
                    synthesis_input.cameraIdB,
                ],
                "calibrationRef": synthesis_input.calibrationRef,
                "sourceBindings": source_bindings,
            },
            "frameAlignmentDebug": {
                "schemaVersion": "frame_alignment_debug.v1",
                "summary": {
                    **alignment_summary,
                    "maxDeltaMs": max_delta_ms,
                },
                "samples": self._frame_alignment_samples(pairs),
            },
            "observationTraceDebug": {
                "schemaVersion": "observation_trace_debug.v1",
                "sampledLandmarkIndices": sorted(DEBUG_LANDMARK_INDICES),
                "samples": [],
            },
            "crossViewValidationDebug": {
                "schemaVersion": "cross_view_validation_debug.v1",
                "samples": [],
                "summary": {},
            },
            "triangulationTraceDebug": {
                "schemaVersion": "triangulation_trace_debug.v1",
                "projectionConvention": "x = K * (R * X + t)",
                "extrinsicsConvention": "panoptic_world_cm",
                "samples": [],
                "summary": {},
            },
        }

    def _frame_alignment_samples(self, pairs: list[Any]) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        for pair_index, pair in enumerate(pairs[:DEBUG_SAMPLE_FRAME_LIMIT]):
            primary = pair.primary_frame
            secondary = pair.secondary_frame
            samples.append(
                {
                    "pairIndex": pair_index,
                    "A": {
                        "frameIndex": self._frame_index(primary),
                        "timestampMs": self._timestamp(primary),
                        "position": pair.primary_position,
                    },
                    "B": {
                        "frameIndex": self._frame_index(secondary),
                        "timestampMs": self._timestamp(secondary),
                        "position": pair.secondary_position,
                    },
                    "timestampDeltaMs": round(pair.timestamp_delta_ms, 4),
                    "frameIndexDelta": self._frame_index(primary) - self._frame_index(secondary),
                }
            )
        return samples

    def _append_debug_samples(
        self,
        *,
        debug_report: dict[str, Any],
        pair_index: int,
        frame_a: dict[str, Any],
        frame_b: dict[str, Any],
        landmark_index: int,
        landmark_name: str,
        joint: TriangulatedJoint,
        observation_a: LandmarkObservation,
        observation_b: LandmarkObservation,
        camera_a: Any,
        camera_b: Any,
        camera_id_a: str,
        camera_id_b: str,
    ) -> None:
        if pair_index >= DEBUG_SAMPLE_FRAME_LIMIT or landmark_index not in DEBUG_LANDMARK_INDICES:
            return

        sample_base = {
            "pairIndex": pair_index,
            "landmarkIndex": landmark_index,
            "landmarkName": landmark_name,
            "A": {
                "frameIndex": self._frame_index(frame_a),
                "timestampMs": self._timestamp(frame_a),
            },
            "B": {
                "frameIndex": self._frame_index(frame_b),
                "timestampMs": self._timestamp(frame_b),
            },
        }
        debug_report["observationTraceDebug"]["samples"].append(
            {
                **sample_base,
                "cameras": {
                    camera_id_a: self._observation_debug_payload(observation_a, camera_a),
                    camera_id_b: self._observation_debug_payload(observation_b, camera_b),
                },
            }
        )
        debug_report["crossViewValidationDebug"]["samples"].append(
            {
                **sample_base,
                "epipolarSampsonErrorPx": joint.epipolar_sampson_error_px,
                "visibility": {
                    camera_id_a: observation_a.visibility,
                    camera_id_b: observation_b.visibility,
                },
                "presence": {
                    camera_id_a: observation_a.presence,
                    camera_id_b: observation_b.presence,
                },
                "outOfBounds": {
                    camera_id_a: not self._in_normalized_bounds(observation_a),
                    camera_id_b: not self._in_normalized_bounds(observation_b),
                },
                "failureReason": joint.failure_reason,
            }
        )
        debug_report["triangulationTraceDebug"]["samples"].append(
            {
                **sample_base,
                "success": joint.success,
                "failureReason": joint.failure_reason,
                "diagnosticPosition": self._position_payload(joint.diagnostic_position),
                "renderablePosition": self._position_payload(joint.position),
                "cameraDepths": {
                    camera_id_a: joint.camera_depth_a,
                    camera_id_b: joint.camera_depth_b,
                },
                "homogeneousW": joint.homogeneous_w,
                "reprojectionErrorPx": joint.mean_reprojection_error_px,
                "reprojectionErrorByCameraPx": {
                    camera_id_a: joint.reprojection_error_a_px,
                    camera_id_b: joint.reprojection_error_b_px,
                },
                "epipolarSampsonErrorPx": joint.epipolar_sampson_error_px,
            }
        )

    def _observation_debug_payload(
        self,
        observation: LandmarkObservation,
        camera_model: Any,
    ) -> dict[str, Any]:
        undistorted = camera_model.undistort_pixel_to_normalized(observation.pixel)
        camera_ray = np.asarray([undistorted[0], undistorted[1], 1.0], dtype=np.float64)
        camera_ray /= np.linalg.norm(camera_ray)
        world_ray = camera_model.R.T @ camera_ray.reshape(3, 1)
        world_ray = world_ray.reshape(3)
        world_ray /= np.linalg.norm(world_ray)
        camera_center = (-camera_model.R.T @ camera_model.t).reshape(3)
        return {
            "cameraId": camera_model.camera_id,
            "imageSize": {
                "width": camera_model.image_width,
                "height": camera_model.image_height,
            },
            "normalized": {
                "x": round(observation.normalized[0], 6),
                "y": round(observation.normalized[1], 6),
            },
            "pixel": {
                "x": round(observation.pixel[0], 3),
                "y": round(observation.pixel[1], 3),
            },
            "undistortedNormalized": {
                "x": round(undistorted[0], 8),
                "y": round(undistorted[1], 8),
            },
            "cameraCenterWorld": self._vector_payload(camera_center, digits=6),
            "worldRayDirection": self._vector_payload(world_ray, digits=8),
            "visibility": observation.visibility,
            "presence": observation.presence,
            "distortionState": observation.distortion_state,
        }

    def _finalize_debug_report(
        self,
        debug_report: dict[str, Any],
        quality_summary: dict[str, Any],
    ) -> None:
        cross_samples = debug_report["crossViewValidationDebug"]["samples"]
        epipolar_values = [
            float(sample["epipolarSampsonErrorPx"])
            for sample in cross_samples
            if isinstance(sample.get("epipolarSampsonErrorPx"), int | float)
        ]
        debug_report["crossViewValidationDebug"]["summary"] = {
            "sampleCount": len(cross_samples),
            "epipolarSampsonErrorPx": self._distribution(epipolar_values),
        }
        trace_samples = debug_report["triangulationTraceDebug"]["samples"]
        debug_report["triangulationTraceDebug"]["summary"] = {
            "sampleCount": len(trace_samples),
            "failureReasonCounts": quality_summary.get("failureReasonCounts", {}),
        }

    def _distribution(self, values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"p50": None, "p95": None, "p99": None, "max": None}
        sorted_values = sorted(values)
        return {
            "p50": self._percentile(sorted_values, 0.5),
            "p95": self._percentile(sorted_values, 0.95),
            "p99": self._percentile(sorted_values, 0.99),
            "max": round(sorted_values[-1], 4),
        }

    def _percentile(self, sorted_values: list[float], percentile: float) -> float:
        if len(sorted_values) == 1:
            return round(sorted_values[0], 4)
        index = percentile * (len(sorted_values) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
        return round(value, 4)

    def _in_normalized_bounds(self, observation: LandmarkObservation) -> bool:
        x, y = observation.normalized
        return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0

    def _position_payload(
        self,
        position: tuple[float, float, float] | None,
    ) -> dict[str, float] | None:
        if position is None:
            return None
        return {
            "x": round(position[0], 6),
            "y": round(position[1], 6),
            "z": round(position[2], 6),
        }

    def _vector_payload(self, vector: np.ndarray, *, digits: int) -> dict[str, float]:
        return {
            "x": round(float(vector[0]), digits),
            "y": round(float(vector[1]), digits),
            "z": round(float(vector[2]), digits),
        }

    def _build_timeline(
        self,
        output_frames: list[dict[str, Any]],
        video_info_a: dict[str, Any],
        video_info_b: dict[str, Any],
    ) -> dict[str, Any]:
        fps = self._fps_from_video_info(video_info_a) or self._fps_from_video_info(video_info_b) or 30.0
        duration_ms = output_frames[-1]["timestampMs"] if output_frames else 0.0
        if output_frames:
            duration_ms += 1000.0 / fps
        return {
            "durationMs": round(duration_ms, 3),
            "fps": round(fps, 3),
            "totalFrames": len(output_frames),
        }

    def _failed_joint_payload(
        self,
        name: str,
        landmark_index: int,
        failure_reason: str,
        *,
        camera_id_a: str,
        camera_id_b: str,
    ) -> dict[str, Any]:
        joint = TriangulatedJoint(
            name=name,
            landmark_index=landmark_index,
            position=None,
            success=False,
            failure_reason=failure_reason,
        )
        return self._triangulation_service.joint_to_payload(
            joint=joint,
            observation_a=None,
            observation_b=None,
            camera_id_a=camera_id_a,
            camera_id_b=camera_id_b,
        )

    def _source_frame_payload(self, frame: dict[str, Any]) -> dict[str, Any]:
        return {
            "frameIndex": self._frame_index(frame),
            "timestampMs": self._timestamp(frame),
            "poseDetected": bool(frame.get("poseDetected", False)),
        }

    def _frame_index(self, frame: dict[str, Any]) -> int:
        value = frame.get("frameIndex")
        return int(value) if isinstance(value, int | float) else 0

    def _timestamp(self, frame: dict[str, Any]) -> float:
        value = frame.get("timestampMs")
        return float(value) if isinstance(value, int | float) else 0.0

    def _fps_from_video_info(self, video_info: dict[str, Any]) -> float | None:
        for key in ("effectiveSamplingFps", "sourceFps", "fps"):
            value = video_info.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None

    def _mean(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)
