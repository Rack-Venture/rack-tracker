from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


class Skeleton3DEvaluationError(Exception):
    pass


PANOPTIC_COCO19_TO_MEDIAPIPE33 = {
    "nose": 1,
    "left_shoulder": 3,
    "left_elbow": 4,
    "left_wrist": 5,
    "left_hip": 6,
    "left_knee": 7,
    "left_ankle": 8,
    "right_shoulder": 9,
    "right_elbow": 10,
    "right_wrist": 11,
    "right_hip": 12,
    "right_knee": 13,
    "right_ankle": 14,
    "left_eye": 15,
    "left_ear": 16,
    "right_eye": 17,
    "right_ear": 18,
}


class Skeleton3DEvaluator:
    def __init__(self, *, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[2]

    def evaluate(
        self,
        *,
        skeleton3d: dict[str, Any],
        gt_ref: str | Path,
    ) -> dict[str, Any]:
        gt_path = self._resolve_path(gt_ref)
        gt_payload = json.loads(gt_path.read_text(encoding="utf-8"))
        gt_frames = self._index_gt_frames(gt_payload)
        frames = skeleton3d.get("frames", [])
        if not isinstance(frames, list):
            raise Skeleton3DEvaluationError("skeleton3d frames must be a list.")

        frame_offset = self._infer_frame_offset(frames, gt_frames)
        by_frame: list[dict[str, Any]] = []
        by_joint_errors: dict[str, list[float]] = defaultdict(list)
        all_errors: list[float] = []
        valid_joint_count = 0
        total_joint_count = 0
        reprojection_errors: list[float] = []

        for frame in frames:
            synth_frame_index = self._frame_index(frame)
            gt_frame = gt_frames.get(synth_frame_index) or gt_frames.get(synth_frame_index + frame_offset)
            if gt_frame is None:
                by_frame.append(
                    {
                        "frameIndex": synth_frame_index,
                        "gtFrameIndex": synth_frame_index + frame_offset,
                        "validJointCount": 0,
                        "totalJointCount": 0,
                        "mpjpeCm": None,
                        "joints": [],
                        "failureReason": "missing_gt_frame",
                    }
                )
                continue

            frame_errors: list[float] = []
            frame_joints: list[dict[str, Any]] = []
            synth_joints = self._index_synth_joints(frame)
            for joint_name, gt_joint_index in PANOPTIC_COCO19_TO_MEDIAPIPE33.items():
                total_joint_count += 1
                synth_joint = synth_joints.get(joint_name)
                if synth_joint is None or synth_joint.get("success") is not True:
                    frame_joints.append(
                        {
                            "name": joint_name,
                            "errorCm": None,
                            "failureReason": "missing_or_failed_synthesis_joint",
                        }
                    )
                    continue
                gt_point = self._gt_joint_point(gt_frame, gt_joint_index)
                if gt_point is None:
                    frame_joints.append(
                        {
                            "name": joint_name,
                            "errorCm": None,
                            "failureReason": "missing_gt_joint",
                        }
                    )
                    continue
                synth_point = self._synth_joint_point(synth_joint)
                if synth_point is None:
                    frame_joints.append(
                        {
                            "name": joint_name,
                            "errorCm": None,
                            "failureReason": "invalid_synthesis_position",
                        }
                    )
                    continue

                error_cm = self._distance(synth_point, gt_point)
                valid_joint_count += 1
                frame_errors.append(error_cm)
                all_errors.append(error_cm)
                by_joint_errors[joint_name].append(error_cm)
                reprojection_error = synth_joint.get("reprojectionErrorPx")
                if isinstance(reprojection_error, int | float):
                    reprojection_errors.append(float(reprojection_error))
                frame_joints.append(
                    {
                        "name": joint_name,
                        "errorCm": round(error_cm, 4),
                        "failureReason": None,
                    }
                )

            by_frame.append(
                {
                    "frameIndex": synth_frame_index,
                    "gtFrameIndex": int(gt_frame.get("frame", synth_frame_index + frame_offset)),
                    "validJointCount": len(frame_errors),
                    "totalJointCount": len(PANOPTIC_COCO19_TO_MEDIAPIPE33),
                    "validJointRatio": round(
                        len(frame_errors) / len(PANOPTIC_COCO19_TO_MEDIAPIPE33),
                        4,
                    ),
                    "mpjpeCm": self._mean(frame_errors),
                    "joints": frame_joints,
                }
            )

        return {
            "schemaVersion": "skeleton3d_evaluation.v1",
            "evaluationInfo": {
                "gtRef": str(gt_ref),
                "mappingVersion": "mediapipe33_to_coco19_subset.v1",
                "unit": "cm",
                "cameraPair": skeleton3d.get("synthesisInfo", {}).get("cameraPair", []),
                "frameRange": gt_payload.get("frame_range"),
                "frameIndexOffset": frame_offset,
            },
            "metrics": {
                "mpjpeMeanCm": self._mean(all_errors),
                "mpjpeMedianCm": self._median(all_errors),
                "mpjpeP95Cm": self._p95(all_errors),
                "validJointRatio": round(valid_joint_count / total_joint_count, 4)
                if total_joint_count
                else 0.0,
                "validFrameRatio": round(
                    sum(1 for item in by_frame if item.get("validJointCount", 0) > 0) / len(by_frame),
                    4,
                )
                if by_frame
                else 0.0,
                "meanReprojectionErrorPx": self._mean(reprojection_errors),
            },
            "byJoint": [
                {
                    "name": joint_name,
                    "mpjpeMeanCm": self._mean(errors),
                    "mpjpeMedianCm": self._median(errors),
                    "sampleCount": len(errors),
                }
                for joint_name, errors in sorted(by_joint_errors.items())
            ],
            "frames": by_frame,
        }

    def _resolve_path(self, path_or_ref: str | Path) -> Path:
        path = Path(path_or_ref)
        if not path.is_absolute():
            path = self._repo_root / path
        if not path.exists():
            raise Skeleton3DEvaluationError(f"GT file not found: {path}")
        return path

    def _index_gt_frames(self, payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
        frames = payload.get("frames", [])
        if not isinstance(frames, list):
            raise Skeleton3DEvaluationError("GT frames must be a list.")
        return {
            int(frame["frame"]): frame
            for frame in frames
            if isinstance(frame, dict) and isinstance(frame.get("frame"), int | float)
        }

    def _index_synth_joints(self, frame: dict[str, Any]) -> dict[str, dict[str, Any]]:
        joints = frame.get("joints", frame.get("joints3d", []))
        if not isinstance(joints, list):
            return {}
        return {
            str(joint.get("name")): joint
            for joint in joints
            if isinstance(joint, dict) and joint.get("name")
        }

    def _infer_frame_offset(
        self,
        frames: list[dict[str, Any]],
        gt_frames: dict[int, dict[str, Any]],
    ) -> int:
        if not frames or not gt_frames:
            return 0
        first_synth = self._frame_index(frames[0])
        if first_synth in gt_frames:
            return 0
        return min(gt_frames) - first_synth

    def _frame_index(self, frame: dict[str, Any]) -> int:
        value = frame.get("frameIndex")
        return int(value) if isinstance(value, int | float) else 0

    def _gt_joint_point(self, gt_frame: dict[str, Any], joint_index: int) -> tuple[float, float, float] | None:
        bodies = gt_frame.get("bodies", [])
        if not bodies:
            return None
        joints = bodies[0].get("joints19", [])
        start = joint_index * 4
        if start + 2 >= len(joints):
            return None
        return (
            float(joints[start]),
            float(joints[start + 1]),
            float(joints[start + 2]),
        )

    def _synth_joint_point(self, joint: dict[str, Any]) -> tuple[float, float, float] | None:
        position = joint.get("position")
        if not isinstance(position, dict):
            return None
        try:
            return (
                float(position["x"]),
                float(position["y"]),
                float(position["z"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _distance(self, point_a: tuple[float, float, float], point_b: tuple[float, float, float]) -> float:
        return sum((point_a[index] - point_b[index]) ** 2 for index in range(3)) ** 0.5

    def _mean(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _median(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(float(median(values)), 4)

    def _p95(self, values: list[float]) -> float | None:
        if not values:
            return None
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * 0.95
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        return round(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight, 4)
