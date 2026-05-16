from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from schema.frame import FrameExtractionResult
from schema.pose import PoseChunk, PoseInferenceResult


PANOPTIC_CAMERA_ID_RE = re.compile(r"(?:^|[_\\/.-])(\d{2}_\d{2})(?=[_\\/.-]|$)")
DEFAULT_PANOPTIC_CALIBRATION_REF = "171204_pose1/171204_pose1/calibration_171204_pose1.json"


class SkeletonAssembler:
    def __init__(
        self,
        *,
        source_path: str,
        display_name: str,
        source_fps: float,
        frame_count: int | None,
        width: int | None,
        height: int | None,
        backend: str,
        requested_sampling_fps: float | None,
        effective_sampling_fps: float | None,
        running_mode: str,
        model_name: str,
        camera_binding: dict | None = None,
        image_coordinate_space: dict | None = None,
        spool_path: Path | None = None,
        retain_frames_in_memory: bool = True,
    ) -> None:
        self._retain_frames_in_memory = retain_frames_in_memory
        self._frames: list[dict] = []
        self._spool_path = spool_path
        self._spool_handle = spool_path.open("w", encoding="utf-8") if spool_path is not None else None
        self._last_timestamp_ms = 0.0
        self._frame_count = 0
        self._camera_binding = dict(camera_binding or {})
        self._image_coordinate_space = dict(image_coordinate_space or {})
        self._video_info = {
            "videoSrc": source_path,
            "displayName": display_name,
            "cameraId": self._camera_binding.get("sourceCameraId"),
            "cameraBinding": self._camera_binding or None,
            "sourceFps": source_fps,
            "frameCount": frame_count,
            "width": width,
            "height": height,
            "imageCoordinateSpace": self._image_coordinate_space or None,
            "backend": backend,
            "extractedCount": 0,
            "requestedSamplingFps": requested_sampling_fps,
            "effectiveSamplingFps": effective_sampling_fps or source_fps,
            "runningMode": running_mode,
            "modelName": model_name,
            "detectedFrameCount": 0,
        }

    def add_pose_chunk(self, pose_chunk: PoseChunk) -> None:
        detected_count = 0
        for frame in pose_chunk.frames:
            frame_payload = frame.to_dict()
            self._last_timestamp_ms = frame.timestamp_ms
            self._frame_count += 1
            if self._retain_frames_in_memory:
                self._frames.append(frame_payload)
            if self._spool_handle is not None:
                self._spool_handle.write(json.dumps(frame_payload, ensure_ascii=False))
                self._spool_handle.write("\n")
            if frame.pose_detected:
                detected_count += 1
        self._video_info["extractedCount"] = int(self._video_info["extractedCount"]) + len(pose_chunk.frames)
        self._video_info["detectedFrameCount"] = int(self._video_info["detectedFrameCount"]) + detected_count

    def finalize(self, *, include_frames: bool = True) -> dict:
        self._close_spool()
        frames = self._load_frames() if include_frames else []
        if frames:
            next_timestamp_cursor_ms = frames[-1]["timestampMs"] + 1
        elif self._frame_count > 0:
            next_timestamp_cursor_ms = self._last_timestamp_ms + 1
        else:
            next_timestamp_cursor_ms = 0
        payload = {
            "frames": frames,
            "videoInfo": dict(self._video_info),
            "nextTimestampCursorMs": next_timestamp_cursor_ms,
        }
        if self._camera_binding:
            payload["cameraBinding"] = dict(self._camera_binding)
        if self._image_coordinate_space:
            payload["imageCoordinateSpace"] = dict(self._image_coordinate_space)
        return payload

    def build_summary(self) -> dict:
        self._close_spool()
        next_timestamp_cursor_ms = self._last_timestamp_ms + 1 if self._frame_count > 0 else 0
        payload = {
            "frames": [],
            "videoInfo": dict(self._video_info),
            "nextTimestampCursorMs": next_timestamp_cursor_ms,
        }
        if self._camera_binding:
            payload["cameraBinding"] = dict(self._camera_binding)
        if self._image_coordinate_space:
            payload["imageCoordinateSpace"] = dict(self._image_coordinate_space)
        return payload

    def _load_frames(self) -> list[dict]:
        if self._retain_frames_in_memory:
            return list(self._frames)
        if self._spool_path is None or not self._spool_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._spool_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _close_spool(self) -> None:
        if self._spool_handle is None:
            return
        self._spool_handle.flush()
        self._spool_handle.close()
        self._spool_handle = None


class SkeletonMapperService:
    def __init__(self, *, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[2]
        self._calibration_hash_cache: dict[Path, str] = {}

    def create_assembler(
        self,
        extraction_result: FrameExtractionResult,
        inference_result: PoseInferenceResult,
        display_name: str | None = None,
        requested_sampling_fps: float | None = None,
        effective_sampling_fps: float | None = None,
        spool_path: Path | None = None,
        retain_frames_in_memory: bool = True,
    ) -> SkeletonAssembler:
        resolved_display_name = display_name or extraction_result.source_path.name
        camera_binding = self._build_camera_binding(
            source_path=str(extraction_result.source_path),
            display_name=resolved_display_name,
        )
        image_coordinate_space = self._build_image_coordinate_space(
            width=extraction_result.width,
            height=extraction_result.height,
        )
        return SkeletonAssembler(
            source_path=str(extraction_result.source_path),
            display_name=resolved_display_name,
            source_fps=extraction_result.source_fps,
            frame_count=extraction_result.frame_count,
            width=extraction_result.width,
            height=extraction_result.height,
            backend=extraction_result.backend,
            requested_sampling_fps=requested_sampling_fps,
            effective_sampling_fps=effective_sampling_fps,
            running_mode=inference_result.running_mode,
            model_name=inference_result.model_name,
            camera_binding=camera_binding,
            image_coordinate_space=image_coordinate_space,
            spool_path=spool_path,
            retain_frames_in_memory=retain_frames_in_memory,
        )

    def map_landmarks(
        self,
        extraction_result: FrameExtractionResult,
        inference_result: PoseInferenceResult,
        display_name: str | None = None,
        requested_sampling_fps: float | None = None,
        effective_sampling_fps: float | None = None,
    ) -> dict:
        assembler = self.create_assembler(
            extraction_result,
            inference_result,
            display_name,
            requested_sampling_fps,
            effective_sampling_fps,
        )
        assembler.add_pose_chunk(
            PoseChunk(
                chunk_index=0,
                start_frame_index=inference_result.frames[0].frame_index if inference_result.frames else 0,
                end_frame_index=inference_result.frames[-1].frame_index if inference_result.frames else 0,
                frames=inference_result.frames,
            )
        )
        skeleton = assembler.finalize()
        skeleton["videoInfo"]["extractedCount"] = extraction_result.extracted_count
        skeleton["videoInfo"]["detectedFrameCount"] = inference_result.detected_frame_count
        return skeleton

    def _build_camera_binding(self, *, source_path: str, display_name: str) -> dict | None:
        camera_id = self._infer_camera_id(display_name, source_path)
        if camera_id is None:
            return None

        binding = {
            "sourceCameraId": camera_id,
            "calibrationCameraId": camera_id,
            "bindingSource": "filename_inferred",
        }
        if self._is_panoptic_camera_id(camera_id):
            binding["calibrationRef"] = DEFAULT_PANOPTIC_CALIBRATION_REF
            calibration_version = self._calibration_version(DEFAULT_PANOPTIC_CALIBRATION_REF)
            if calibration_version is not None:
                binding["calibrationVersion"] = calibration_version
        return binding

    def _build_image_coordinate_space(self, *, width: int | None, height: int | None) -> dict:
        return {
            "landmarkSpace": "mediapipe_normalized_image",
            "pixelBasis": {
                "width": width,
                "height": height,
            },
            "preprocessTransform": None,
        }

    def _infer_camera_id(self, *values: str | None) -> str | None:
        for value in values:
            if not value:
                continue
            match = PANOPTIC_CAMERA_ID_RE.search(str(value))
            if match:
                return match.group(1)
        return None

    def _is_panoptic_camera_id(self, camera_id: str) -> bool:
        return bool(re.fullmatch(r"\d{2}_\d{2}", camera_id))

    def _calibration_version(self, calibration_ref: str) -> str | None:
        path = (self._repo_root / calibration_ref).resolve()
        if not path.exists():
            return None
        cached = self._calibration_hash_cache.get(path)
        if cached is not None:
            return cached
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        version = f"sha256:{digest}"
        self._calibration_hash_cache[path] = version
        return version
