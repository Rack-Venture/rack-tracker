from __future__ import annotations

from typing import Any

from schema.rack_motion import QualityMetric, ReconstructionTarget3D

# Full MediaPipe Pose 33-landmark set mapped to rack-domain person.* targetIds
RACK_PERSON_TARGETS: dict[str, str] = {
    # Head
    "nose": "person.nose",
    "left_eye_inner": "person.left_eye_inner",
    "left_eye": "person.left_eye",
    "left_eye_outer": "person.left_eye_outer",
    "right_eye_inner": "person.right_eye_inner",
    "right_eye": "person.right_eye",
    "right_eye_outer": "person.right_eye_outer",
    "left_ear": "person.left_ear",
    "right_ear": "person.right_ear",
    "mouth_left": "person.mouth_left",
    "mouth_right": "person.mouth_right",
    # Torso
    "left_shoulder": "person.left_shoulder",
    "right_shoulder": "person.right_shoulder",
    # Arms
    "left_elbow": "person.left_elbow",
    "right_elbow": "person.right_elbow",
    "left_wrist": "person.left_wrist",
    "right_wrist": "person.right_wrist",
    # Hands (wrist-level tips from MediaPipe Pose)
    "left_pinky": "person.left_pinky",
    "right_pinky": "person.right_pinky",
    "left_index": "person.left_index",
    "right_index": "person.right_index",
    "left_thumb": "person.left_thumb",
    "right_thumb": "person.right_thumb",
    # Hips & Legs
    "left_hip": "person.left_hip",
    "right_hip": "person.right_hip",
    "left_knee": "person.left_knee",
    "right_knee": "person.right_knee",
    # Feet
    "left_ankle": "person.left_ankle",
    "right_ankle": "person.right_ankle",
    "left_heel": "person.left_heel",
    "right_heel": "person.right_heel",
    "left_foot_index": "person.left_foot_index",
    "right_foot_index": "person.right_foot_index",
}

_CM_TO_M = 0.01
_REPROJECTION_THRESHOLD_PX = 8.0


def map_skeleton3d_frame(
    frame: dict[str, Any],
    *,
    calibration_id: str,
    camera_id_a: str,
    camera_id_b: str,
) -> list[ReconstructionTarget3D]:
    """Convert a skeleton3d.v1 frame to ReconstructionTarget3D records.

    Converts panoptic_world_cm → rack_world in meters using identity_assumed
    capture_to_rack for Stage 1 dev fixture.  Joints with no reprojection error
    (pose_not_detected, missing_landmark) are skipped since multi_camera mode
    requires reprojectionErrorPx.
    """
    joints = frame.get("joints", [])
    if not isinstance(joints, list):
        return []

    frame_index = int(frame.get("frameIndex", 0))
    result: list[ReconstructionTarget3D] = []

    for joint in joints:
        target_id = RACK_PERSON_TARGETS.get(joint.get("name", ""))
        if target_id is None:
            continue

        reproj_error = joint.get("reprojectionErrorPx")
        if reproj_error is None:
            continue
        reproj_error = float(reproj_error)

        success = bool(joint.get("success", False))
        failure_reason: str | None = joint.get("failureReason")
        position = joint.get("position") if success else None

        x: float | None = None
        y: float | None = None
        z: float | None = None
        if success and isinstance(position, dict):
            raw_x = position.get("x")
            raw_y = position.get("y")
            raw_z = position.get("z")
            if raw_x is not None and raw_y is not None and raw_z is not None:
                # panoptic_world_cm → rack_world (meters)
                # Cameras (00_11, 00_21) sit at large negative panoptic X, so the
                # "front of rack" direction is -panoptic X = +rack Z.
                # Lateral (left-right) is panoptic Z; lifter's right = panoptic -Z = +rack X.
                x = round(-float(raw_z) * _CM_TO_M, 6)
                y = round(-float(raw_y) * _CM_TO_M, 6)
                z = round(-float(raw_x) * _CM_TO_M, 6)

        has_point = x is not None and y is not None and z is not None
        status: str = "valid" if (success and has_point) else "invalid"
        if status == "invalid" and not failure_reason:
            failure_reason = "joint_reconstruction_failed"

        quality = (
            max(0.0, min(1.0, 1.0 - reproj_error / (2.0 * _REPROJECTION_THRESHOLD_PX)))
            if status == "valid"
            else 0.0
        )

        quality_metrics: list[QualityMetric] = [
            QualityMetric(
                metricName="reprojection_error_px",
                value=round(reproj_error, 4),
                status="ok" if success else "warning",
                unit="px",
                policyId="rack_motion.stage1.reprojection" if not success else None,
                detail={"source": "skeleton3d.v1"},
            ),
            QualityMetric(
                metricName="capture_to_rack_status",
                value="identity_assumed",
                status="warning",
                unit=None,
                policyId="rack_motion.stage1.dev_alignment",
                detail={"note": "panoptic_world_cm rotated to rack_world: rack_x=-panoptic_z, rack_z=-panoptic_x"},
            ),
        ]

        result.append(
            ReconstructionTarget3D(
                frameIndex=frame_index,
                targetId=target_id,
                spaceId="rack_world",
                unit="meter",
                x=x,
                y=y,
                z=z,
                quality=round(quality, 4),
                mode="multi_camera",
                calibrationId=calibration_id,
                usedCameraIds=[camera_id_a, camera_id_b],
                reprojectionErrorPx=round(reproj_error, 4),
                status=status,
                failureReason=failure_reason if status == "invalid" else None,
                qualityMetrics=quality_metrics,
            )
        )

    return result
