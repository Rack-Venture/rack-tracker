from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from service.camera_calibration import CameraModel


DistortionState = Literal["distorted_pixel", "undistorted_normalized", "unknown"]


POSE_LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


@dataclass(slots=True)
class LandmarkObservation:
    name: str
    landmark_index: int
    normalized: tuple[float, float]
    pixel: tuple[float, float]
    visibility: float | None
    presence: float | None
    distortion_state: DistortionState = "distorted_pixel"


class LandmarkObservationError(Exception):
    pass


class LandmarkObservationBuilder:
    def build(
        self,
        frame: dict[str, Any],
        *,
        landmark_index: int,
        video_info: dict[str, Any],
        camera_model: CameraModel,
    ) -> LandmarkObservation:
        landmarks = frame.get("landmarks", [])
        if not isinstance(landmarks, list) or landmark_index >= len(landmarks):
            raise LandmarkObservationError(f"Missing landmark {landmark_index}.")
        landmark = landmarks[landmark_index]
        if not isinstance(landmark, dict):
            raise LandmarkObservationError(f"Invalid landmark {landmark_index}.")

        width = self._resolve_dimension(video_info, "width", camera_model.image_width)
        height = self._resolve_dimension(video_info, "height", camera_model.image_height)
        x = self._number(landmark.get("x"), f"landmark {landmark_index} x")
        y = self._number(landmark.get("y"), f"landmark {landmark_index} y")
        pixel_x = x * width
        pixel_y = y * height
        return LandmarkObservation(
            name=str(landmark.get("name") or POSE_LANDMARK_NAMES[landmark_index]),
            landmark_index=landmark_index,
            normalized=(x, y),
            pixel=(pixel_x, pixel_y),
            visibility=self._optional_number(landmark.get("visibility")),
            presence=self._optional_number(landmark.get("presence")),
        )

    def _resolve_dimension(
        self,
        video_info: dict[str, Any],
        key: str,
        fallback: int,
    ) -> float:
        value = video_info.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
        if fallback > 0:
            return float(fallback)
        raise LandmarkObservationError(f"videoInfo.{key} is required for 2D coordinate conversion.")

    def _number(self, value: Any, field_name: str) -> float:
        if not isinstance(value, int | float):
            raise LandmarkObservationError(f"{field_name} must be numeric.")
        return float(value)

    def _optional_number(self, value: Any) -> float | None:
        if value is None:
            return None
        if not isinstance(value, int | float):
            return None
        return float(value)
