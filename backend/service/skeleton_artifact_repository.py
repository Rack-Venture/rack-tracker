from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from config.config import SKELETON_DIR, SYNTHESIS_DIR


class SkeletonArtifactRepositoryError(Exception):
    pass


class SkeletonArtifactNotFoundError(SkeletonArtifactRepositoryError):
    pass


class SkeletonArtifactNotReadyError(SkeletonArtifactRepositoryError):
    pass


class SkeletonArtifactRepository:
    def __init__(
        self,
        *,
        skeleton_dir: Path = SKELETON_DIR,
        synthesis_dir: Path = SYNTHESIS_DIR,
        source_loader: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._skeleton_dir = skeleton_dir
        self._synthesis_dir = synthesis_dir
        self._source_loader = source_loader
        self._skeleton3d_dir = synthesis_dir / "skeleton3d"
        self._skeleton2d_dir = synthesis_dir / "skeleton2d"
        self._evaluation_dir = synthesis_dir / "evaluation"
        self._debug_dir = synthesis_dir / "debug"
        self._skeleton3d_dir.mkdir(parents=True, exist_ok=True)
        self._skeleton2d_dir.mkdir(parents=True, exist_ok=True)
        self._evaluation_dir.mkdir(parents=True, exist_ok=True)
        self._debug_dir.mkdir(parents=True, exist_ok=True)

    def get_skeleton_summary(self, job_id: str) -> dict[str, Any]:
        skeleton = self.read_skeleton(job_id)
        return {
            "frames": [],
            "videoInfo": dict(skeleton.get("videoInfo", {})),
            "nextTimestampCursorMs": skeleton.get("nextTimestampCursorMs", 0),
        }

    def iter_skeleton_frames(self, job_id: str) -> Iterator[dict[str, Any]]:
        skeleton = self.read_skeleton(job_id)
        frames = skeleton.get("frames", [])
        if not isinstance(frames, list):
            raise SkeletonArtifactNotReadyError(f"Skeleton frames are invalid for {job_id}.")
        yield from frames

    def read_skeleton(self, job_id: str) -> dict[str, Any]:
        if self._source_loader is not None:
            try:
                payload = self._source_loader(job_id)
            except KeyError:
                payload = None
            if payload is not None:
                return payload

        path = self._skeleton_dir / f"{job_id}.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(f"Skeleton artifact not found for {job_id}.")
        return self._read_json(path)

    def write_skeleton3d(self, synthesis_job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._skeleton3d_dir / f"{synthesis_job_id}.json"
        self._write_json(path, payload)
        return {
            "path": str(path),
            "schemaVersion": str(payload.get("schemaVersion", "skeleton3d.v1")),
            "summary": self._build_skeleton3d_summary(payload),
        }

    def read_skeleton3d(self, synthesis_job_id: str) -> dict[str, Any]:
        path = self._skeleton3d_dir / f"{synthesis_job_id}.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(
                f"3D skeleton artifact not found for {synthesis_job_id}."
            )
        return self._read_json(path)

    def get_skeleton3d_all(self, synthesis_job_id: str) -> dict[str, Any]:
        payload = self.read_skeleton3d(synthesis_job_id)
        frames = payload.get("frames", [])
        if not isinstance(frames, list):
            raise SkeletonArtifactNotReadyError(
                f"3D skeleton frames are invalid for {synthesis_job_id}."
            )
        total_frames = len(frames)
        timeline = dict(payload.get("timeline", {}))
        if "durationMs" not in timeline:
            timeline["durationMs"] = self._infer_duration_ms(frames)
        return {
            "schemaVersion": payload.get("schemaVersion", "skeleton3d.v1"),
            "page": {
                "startFrame": 0,
                "limit": total_frames,
                "totalFrames": total_frames,
                "nextStartFrame": None,
            },
            "timeline": timeline,
            "synthesisInfo": payload.get("synthesisInfo", {}),
            "qualitySummary": payload.get("qualitySummary", {}),
            "frames": frames,
        }

    def get_skeleton3d_page(
        self,
        synthesis_job_id: str,
        *,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        payload = self.read_skeleton3d(synthesis_job_id)
        frames = payload.get("frames", [])
        if not isinstance(frames, list):
            raise SkeletonArtifactNotReadyError(
                f"3D skeleton frames are invalid for {synthesis_job_id}."
            )
        total_frames = len(frames)
        bounded_offset = min(max(offset, 0), total_frames)
        bounded_limit = min(max(limit, 1), max(total_frames - bounded_offset, 0))
        page_frames = frames[bounded_offset : bounded_offset + bounded_limit]
        next_start_frame = (
            bounded_offset + len(page_frames)
            if bounded_offset + len(page_frames) < total_frames
            else None
        )
        timeline = dict(payload.get("timeline", {}))
        if "durationMs" not in timeline:
            timeline["durationMs"] = self._infer_duration_ms(frames)
        return {
            "schemaVersion": payload.get("schemaVersion", "skeleton3d.v1"),
            "page": {
                "startFrame": bounded_offset,
                "limit": bounded_limit,
                "totalFrames": total_frames,
                "nextStartFrame": next_start_frame,
            },
            "timeline": timeline,
            "synthesisInfo": payload.get("synthesisInfo", {}),
            "qualitySummary": payload.get("qualitySummary", {}),
            "frames": page_frames,
        }

    def write_skeleton_a(self, synthesis_job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._skeleton2d_dir / f"{synthesis_job_id}_a.json"
        self._write_json(path, payload)
        frames = payload.get("frames", [])
        return {
            "path": str(path),
            "schemaVersion": str(payload.get("schemaVersion", "skeleton2d.v1")),
            "summary": {
                "cameraId": payload.get("cameraId"),
                "frameCount": len(frames) if isinstance(frames, list) else 0,
                "timeline": payload.get("timeline", {}),
            },
        }

    def write_skeleton_b(self, synthesis_job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._skeleton2d_dir / f"{synthesis_job_id}_b.json"
        self._write_json(path, payload)
        frames = payload.get("frames", [])
        return {
            "path": str(path),
            "schemaVersion": str(payload.get("schemaVersion", "skeleton2d.v1")),
            "summary": {
                "cameraId": payload.get("cameraId"),
                "frameCount": len(frames) if isinstance(frames, list) else 0,
                "timeline": payload.get("timeline", {}),
            },
        }

    def get_skeleton_a_page(self, synthesis_job_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        path = self._skeleton2d_dir / f"{synthesis_job_id}_a.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(
                f"Camera A 2D skeleton not found for {synthesis_job_id}."
            )
        return self._get_skeleton2d_page(path, offset=offset, limit=limit)

    def get_skeleton_b_page(self, synthesis_job_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        path = self._skeleton2d_dir / f"{synthesis_job_id}_b.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(
                f"Camera B 2D skeleton not found for {synthesis_job_id}."
            )
        return self._get_skeleton2d_page(path, offset=offset, limit=limit)

    def _get_skeleton2d_page(self, path: Path, *, offset: int, limit: int) -> dict[str, Any]:
        payload = self._read_json(path)
        frames = payload.get("frames", [])
        if not isinstance(frames, list):
            raise SkeletonArtifactNotReadyError(f"2D skeleton frames are invalid for {path.stem}.")
        total_frames = len(frames)
        bounded_offset = min(max(offset, 0), total_frames)
        bounded_limit = min(max(limit, 1), max(total_frames - bounded_offset, 0))
        page_frames = frames[bounded_offset : bounded_offset + bounded_limit]
        next_start_frame = (
            bounded_offset + len(page_frames)
            if bounded_offset + len(page_frames) < total_frames
            else None
        )
        return {
            "schemaVersion": payload.get("schemaVersion", "skeleton2d.v1"),
            "cameraId": payload.get("cameraId"),
            "page": {
                "startFrame": bounded_offset,
                "limit": bounded_limit,
                "totalFrames": total_frames,
                "nextStartFrame": next_start_frame,
            },
            "timeline": payload.get("timeline", {}),
            "frames": page_frames,
        }

    def write_evaluation(self, synthesis_job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._evaluation_dir / f"{synthesis_job_id}.json"
        self._write_json(path, payload)
        return {
            "path": str(path),
            "schemaVersion": str(payload.get("schemaVersion", "skeleton3d_evaluation.v1")),
            "summary": dict(payload.get("metrics", {})),
        }

    def read_evaluation(self, synthesis_job_id: str) -> dict[str, Any]:
        path = self._evaluation_dir / f"{synthesis_job_id}.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(
                f"3D evaluation artifact not found for {synthesis_job_id}."
            )
        return self._read_json(path)

    def write_debug_report(self, synthesis_job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._debug_dir / f"{synthesis_job_id}.json"
        self._write_json(path, payload)
        return {
            "path": str(path),
            "schemaVersion": str(payload.get("schemaVersion", "synthesis_debug_report.v1")),
            "summary": self._build_debug_summary(payload),
        }

    def read_debug_report(self, synthesis_job_id: str) -> dict[str, Any]:
        path = self._debug_dir / f"{synthesis_job_id}.json"
        if not path.exists():
            raise SkeletonArtifactNotFoundError(
                f"3D synthesis debug artifact not found for {synthesis_job_id}."
            )
        return self._read_json(path)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    def _build_skeleton3d_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        frames = payload.get("frames", [])
        return {
            "schemaVersion": payload.get("schemaVersion", "skeleton3d.v1"),
            "frameCount": len(frames) if isinstance(frames, list) else 0,
            "synthesisInfo": payload.get("synthesisInfo", {}),
            "qualitySummary": payload.get("qualitySummary", {}),
            "timeline": payload.get("timeline", {}),
        }

    def _build_debug_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        alignment = payload.get("frameAlignmentDebug", {})
        observation = payload.get("observationTraceDebug", {})
        cross_view = payload.get("crossViewValidationDebug", {})
        triangulation = payload.get("triangulationTraceDebug", {})
        return {
            "frameAlignment": alignment.get("summary", {}),
            "observationSampleCount": len(observation.get("samples", []))
            if isinstance(observation.get("samples"), list)
            else 0,
            "crossView": cross_view.get("summary", {}),
            "triangulation": triangulation.get("summary", {}),
        }

    def _infer_duration_ms(self, frames: list[dict[str, Any]]) -> float:
        if not frames:
            return 0.0
        value = frames[-1].get("timestampMs")
        return float(value) if isinstance(value, int | float) else 0.0
