from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class CameraCalibrationError(Exception):
    pass


class CameraNotFoundError(CameraCalibrationError):
    pass


@dataclass(slots=True)
class CameraModel:
    camera_id: str
    image_width: int
    image_height: int
    K: np.ndarray
    dist_coeffs: np.ndarray
    R: np.ndarray
    t: np.ndarray
    projection_matrix: np.ndarray
    coordinate_system: str = "panoptic_world_cm"

    def undistort_pixel_to_normalized(self, point_px: tuple[float, float]) -> tuple[float, float]:
        points = np.array([[[point_px[0], point_px[1]]]], dtype=np.float64)
        undistorted = cv2.undistortPoints(points, self.K, self.dist_coeffs)
        x, y = undistorted.reshape(2)
        return float(x), float(y)

    def project_world_point(self, point_world: np.ndarray) -> tuple[float, float]:
        point = np.asarray(point_world, dtype=np.float64).reshape(1, 1, 3)
        rvec, _ = cv2.Rodrigues(self.R)
        image_points, _ = cv2.projectPoints(point, rvec, self.t, self.K, self.dist_coeffs)
        x, y = image_points.reshape(2)
        return float(x), float(y)

    @property
    def normalized_projection_matrix(self) -> np.ndarray:
        return np.hstack([self.R, self.t])


class CameraCalibrationService:
    def __init__(self, *, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[2]
        self._cache: dict[Path, dict[str, Any]] = {}

    def load_camera(self, calibration_ref: str | Path, camera_id: str) -> CameraModel:
        calibration_path = self._resolve_calibration_path(calibration_ref)
        payload = self._load_payload(calibration_path)
        for camera in payload.get("cameras", []):
            if str(camera.get("name")) == camera_id:
                return self._to_camera_model(camera)
        raise CameraNotFoundError(f"Camera '{camera_id}' not found in {calibration_path}.")

    def load_pair(
        self,
        calibration_ref: str | Path,
        camera_id_a: str,
        camera_id_b: str,
    ) -> tuple[CameraModel, CameraModel]:
        return (
            self.load_camera(calibration_ref, camera_id_a),
            self.load_camera(calibration_ref, camera_id_b),
        )

    def _resolve_calibration_path(self, calibration_ref: str | Path) -> Path:
        path = Path(calibration_ref)
        if not path.is_absolute():
            path = self._repo_root / path
        path = path.resolve()
        if not path.exists():
            raise CameraCalibrationError(f"Calibration file not found: {path}")
        return path

    def _load_payload(self, path: Path) -> dict[str, Any]:
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._cache[path] = payload
        return payload

    def _to_camera_model(self, camera: dict[str, Any]) -> CameraModel:
        resolution = camera.get("resolution") or [0, 0]
        image_width = int(resolution[0])
        image_height = int(resolution[1])
        K = np.asarray(camera.get("K"), dtype=np.float64).reshape(3, 3)
        dist_coeffs = np.asarray(camera.get("distCoef", []), dtype=np.float64).reshape(-1, 1)
        R = np.asarray(camera.get("R"), dtype=np.float64).reshape(3, 3)
        t = np.asarray(camera.get("t"), dtype=np.float64).reshape(3, 1)
        projection_matrix = K @ np.hstack([R, t])
        return CameraModel(
            camera_id=str(camera.get("name")),
            image_width=image_width,
            image_height=image_height,
            K=K,
            dist_coeffs=dist_coeffs,
            R=R,
            t=t,
            projection_matrix=projection_matrix,
        )
