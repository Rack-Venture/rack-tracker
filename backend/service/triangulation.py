from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any

import cv2
import numpy as np

from schema.synthesis import SynthesisThresholds
from service.camera_calibration import CameraModel
from service.landmark_observation import LandmarkObservation


class TriangulationError(Exception):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


@dataclass(slots=True)
class TriangulatedJoint:
    name: str
    landmark_index: int
    position: tuple[float, float, float] | None
    success: bool
    failure_reason: str | None
    diagnostic_position: tuple[float, float, float] | None = None
    reprojection_error_a_px: float | None = None
    reprojection_error_b_px: float | None = None
    camera_depth_a: float | None = None
    camera_depth_b: float | None = None
    homogeneous_w: float | None = None
    epipolar_sampson_error_px: float | None = None

    @property
    def mean_reprojection_error_px(self) -> float | None:
        if self.reprojection_error_a_px is None or self.reprojection_error_b_px is None:
            return None
        return (self.reprojection_error_a_px + self.reprojection_error_b_px) / 2.0


class ReprojectionScorer:
    def score(
        self,
        *,
        point_world: np.ndarray,
        camera_model: CameraModel,
        observed_pixel: tuple[float, float],
    ) -> float:
        projected_x, projected_y = camera_model.project_world_point(point_world)
        return sqrt(
            (projected_x - observed_pixel[0]) ** 2
            + (projected_y - observed_pixel[1]) ** 2
        )


class TriangulationService:
    def __init__(self, *, reprojection_scorer: ReprojectionScorer | None = None) -> None:
        self._reprojection_scorer = reprojection_scorer or ReprojectionScorer()

    def triangulate_joint(
        self,
        *,
        observation_a: LandmarkObservation,
        observation_b: LandmarkObservation,
        camera_a: CameraModel,
        camera_b: CameraModel,
        thresholds: SynthesisThresholds,
    ) -> TriangulatedJoint:
        epipolar_sampson_error_px = self._sampson_distance_px(
            observation_a=observation_a,
            observation_b=observation_b,
            camera_a=camera_a,
            camera_b=camera_b,
        )
        failure_reason = self._validate_observations(
            observation_a,
            observation_b,
            thresholds=thresholds,
        )
        if failure_reason is not None:
            return TriangulatedJoint(
                name=observation_a.name,
                landmark_index=observation_a.landmark_index,
                position=None,
                success=False,
                failure_reason=failure_reason,
                epipolar_sampson_error_px=self._round_optional(epipolar_sampson_error_px),
            )

        try:
            point_world, homogeneous_w = self._triangulate_world_point(
                observation_a=observation_a,
                observation_b=observation_b,
                camera_a=camera_a,
                camera_b=camera_b,
            )
        except TriangulationError as exc:
            return TriangulatedJoint(
                name=observation_a.name,
                landmark_index=observation_a.landmark_index,
                position=None,
                success=False,
                failure_reason=exc.reason,
                epipolar_sampson_error_px=self._round_optional(epipolar_sampson_error_px),
            )

        diagnostic_position = (
            float(point_world[0]),
            float(point_world[1]),
            float(point_world[2]),
        )
        camera_depth_a = self._camera_depth(point_world, camera_a)
        camera_depth_b = self._camera_depth(point_world, camera_b)
        if camera_depth_a <= 0 or camera_depth_b <= 0:
            return TriangulatedJoint(
                name=observation_a.name,
                landmark_index=observation_a.landmark_index,
                position=None,
                success=False,
                failure_reason="behind_camera",
                diagnostic_position=diagnostic_position,
                camera_depth_a=round(camera_depth_a, 6),
                camera_depth_b=round(camera_depth_b, 6),
                homogeneous_w=round(homogeneous_w, 12),
                epipolar_sampson_error_px=self._round_optional(epipolar_sampson_error_px),
            )

        error_a = self._reprojection_scorer.score(
            point_world=point_world,
            camera_model=camera_a,
            observed_pixel=observation_a.pixel,
        )
        error_b = self._reprojection_scorer.score(
            point_world=point_world,
            camera_model=camera_b,
            observed_pixel=observation_b.pixel,
        )
        mean_error = (error_a + error_b) / 2.0
        success = mean_error <= thresholds.maxReprojectionErrorPx
        position = (
            diagnostic_position
            if success
            else None
        )
        return TriangulatedJoint(
            name=observation_a.name,
            landmark_index=observation_a.landmark_index,
            position=position,
            success=success,
            failure_reason=None if success else "high_reprojection_error",
            diagnostic_position=diagnostic_position,
            reprojection_error_a_px=round(error_a, 4),
            reprojection_error_b_px=round(error_b, 4),
            camera_depth_a=round(camera_depth_a, 6),
            camera_depth_b=round(camera_depth_b, 6),
            homogeneous_w=round(homogeneous_w, 12),
            epipolar_sampson_error_px=self._round_optional(epipolar_sampson_error_px),
        )

    def joint_to_payload(
        self,
        *,
        joint: TriangulatedJoint,
        observation_a: LandmarkObservation | None,
        observation_b: LandmarkObservation | None,
        camera_id_a: str,
        camera_id_b: str,
    ) -> dict[str, Any]:
        return {
            "name": joint.name,
            "landmarkIndex": joint.landmark_index,
            "position": (
                {
                    "x": round(joint.position[0], 6),
                    "y": round(joint.position[1], 6),
                    "z": round(joint.position[2], 6),
                }
                if joint.position is not None
                else None
            ),
            "diagnosticPosition": (
                {
                    "x": round(joint.diagnostic_position[0], 6),
                    "y": round(joint.diagnostic_position[1], 6),
                    "z": round(joint.diagnostic_position[2], 6),
                }
                if joint.diagnostic_position is not None
                else None
            ),
            "success": joint.success,
            "failureReason": joint.failure_reason,
            "reprojectionErrorPx": (
                round(joint.mean_reprojection_error_px, 4)
                if joint.mean_reprojection_error_px is not None
                else None
            ),
            "epipolarSampsonErrorPx": joint.epipolar_sampson_error_px,
            "cameraDepths": {
                camera_id_a: joint.camera_depth_a,
                camera_id_b: joint.camera_depth_b,
            },
            "homogeneousW": joint.homogeneous_w,
            "observations": {
                camera_id_a: self._observation_payload(
                    observation_a,
                    joint.reprojection_error_a_px,
                ),
                camera_id_b: self._observation_payload(
                    observation_b,
                    joint.reprojection_error_b_px,
                ),
            },
        }

    def _triangulate_world_point(
        self,
        *,
        observation_a: LandmarkObservation,
        observation_b: LandmarkObservation,
        camera_a: CameraModel,
        camera_b: CameraModel,
    ) -> tuple[np.ndarray, float]:
        point_a = camera_a.undistort_pixel_to_normalized(observation_a.pixel)
        point_b = camera_b.undistort_pixel_to_normalized(observation_b.pixel)
        points_4d = cv2.triangulatePoints(
            camera_a.normalized_projection_matrix,
            camera_b.normalized_projection_matrix,
            np.asarray(point_a, dtype=np.float64).reshape(2, 1),
            np.asarray(point_b, dtype=np.float64).reshape(2, 1),
        )
        w = points_4d[3, 0]
        if not np.isfinite(w) or abs(w) < 1e-12:
            raise TriangulationError(
                "degenerate_homogeneous_point",
                "Triangulation produced a point at infinity.",
            )
        point_world = (points_4d[:3, 0] / w).astype(np.float64)
        if not np.all(np.isfinite(point_world)):
            raise TriangulationError(
                "degenerate_homogeneous_point",
                "Triangulation produced a non-finite point.",
            )
        return point_world, float(w)

    def _validate_observations(
        self,
        observation_a: LandmarkObservation,
        observation_b: LandmarkObservation,
        *,
        thresholds: SynthesisThresholds,
    ) -> str | None:
        if not self._in_normalized_bounds(observation_a) or not self._in_normalized_bounds(observation_b):
            return "out_of_bounds"
        if observation_a.visibility is not None and observation_a.visibility < thresholds.minVisibility:
            return "low_visibility"
        if observation_b.visibility is not None and observation_b.visibility < thresholds.minVisibility:
            return "low_visibility"
        if observation_a.presence is not None and observation_a.presence < thresholds.minPresence:
            return "low_visibility"
        if observation_b.presence is not None and observation_b.presence < thresholds.minPresence:
            return "low_visibility"
        return None

    def _in_normalized_bounds(self, observation: LandmarkObservation) -> bool:
        x, y = observation.normalized
        return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0

    def _camera_depth(self, point_world: np.ndarray, camera_model: CameraModel) -> float:
        point = np.asarray(point_world, dtype=np.float64).reshape(3, 1)
        point_camera = camera_model.R @ point + camera_model.t
        return float(point_camera[2, 0])

    def _sampson_distance_px(
        self,
        *,
        observation_a: LandmarkObservation,
        observation_b: LandmarkObservation,
        camera_a: CameraModel,
        camera_b: CameraModel,
    ) -> float | None:
        try:
            fundamental = self._fundamental_matrix(camera_a, camera_b)
            point_a = np.asarray(
                [observation_a.pixel[0], observation_a.pixel[1], 1.0],
                dtype=np.float64,
            )
            point_b = np.asarray(
                [observation_b.pixel[0], observation_b.pixel[1], 1.0],
                dtype=np.float64,
            )
            f_x_a = fundamental @ point_a
            f_t_x_b = fundamental.T @ point_b
            numerator = float(point_b.T @ fundamental @ point_a)
            denominator = (
                f_x_a[0] ** 2
                + f_x_a[1] ** 2
                + f_t_x_b[0] ** 2
                + f_t_x_b[1] ** 2
            )
            if denominator <= 1e-12:
                return None
            return sqrt((numerator * numerator) / denominator)
        except Exception:
            return None

    def _fundamental_matrix(self, camera_a: CameraModel, camera_b: CameraModel) -> np.ndarray:
        rotation_ba = camera_b.R @ camera_a.R.T
        translation_ba = camera_b.t - rotation_ba @ camera_a.t
        essential = self._skew(translation_ba.reshape(3)) @ rotation_ba
        return np.linalg.inv(camera_b.K).T @ essential @ np.linalg.inv(camera_a.K)

    def _skew(self, vector: np.ndarray) -> np.ndarray:
        x, y, z = vector
        return np.asarray(
            [
                [0.0, -z, y],
                [z, 0.0, -x],
                [-y, x, 0.0],
            ],
            dtype=np.float64,
        )

    def _round_optional(self, value: float | None, digits: int = 4) -> float | None:
        return round(value, digits) if value is not None else None

    def _observation_payload(
        self,
        observation: LandmarkObservation | None,
        reprojection_error_px: float | None,
    ) -> dict[str, Any] | None:
        if observation is None:
            return None
        return {
            "normalized": {
                "x": round(observation.normalized[0], 6),
                "y": round(observation.normalized[1], 6),
            },
            "pixel": {
                "x": round(observation.pixel[0], 3),
                "y": round(observation.pixel[1], 3),
            },
            "visibility": observation.visibility,
            "presence": observation.presence,
            "distortionState": observation.distortion_state,
            "reprojectionErrorPx": reprojection_error_px,
        }
