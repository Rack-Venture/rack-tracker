from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from schema.rack_motion import (
    QualityMetric,
    RackAlignmentSummary,
    RackAnchor,
    RackMotionCoordinateSpaces,
    RackMotionFrame,
    RackMotionFramePage,
    RackMotionSessionManifest,
    RackMotionSourceRefs,
    RackMotionSpaceSummary,
    RackMotionSyncQuality,
    RackMotionViewerFixture,
    ReconstructionTarget3D,
    SupportZone,
)
from service.skeleton3d_to_rack_mapper import map_skeleton3d_frame


DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "rack_motion"
STAGE1_ALIGNMENT_FILE = "virtual_power_rack_dev_alignment.json"
STAGE1_FRAME_COUNT = 90


class RackMotionArtifactRepository:
    def __init__(self, *, fixture_dir: Path = DEFAULT_FIXTURE_DIR) -> None:
        self._fixture_dir = fixture_dir

    def get_stage1_fixture_from_skeleton3d(
        self,
        skeleton3d_payload: dict[str, Any],
        *,
        offset: int = 0,
        limit: int = 120,
    ) -> dict[str, Any]:
        """Build a Stage 1 viewer fixture using real skeleton3d.v1 data.

        Person keypoints are imported from skeleton3d.v1 via the curated
        person.* target set.  Rack geometry comes from the synthetic dev
        alignment fixture.  capture_to_rack is identity_assumed.
        """
        rack_alignment = self._read_rack_alignment(STAGE1_ALIGNMENT_FILE)
        synthesis_info = skeleton3d_payload.get("synthesisInfo", {})
        source_job_ids: list[str] = synthesis_info.get("sourceJobIds", [])
        camera_pair: list[str] = synthesis_info.get("cameraPair", [])
        calibration_ref: str = synthesis_info.get("calibrationRef", "synthetic.stage1.dev")

        camera_id_a = camera_pair[0] if len(camera_pair) > 0 else "unknown_cam_a"
        camera_id_b = camera_pair[1] if len(camera_pair) > 1 else "unknown_cam_b"
        calibration_id = calibration_ref.replace("\\", "/").split("/")[-1]

        session_id = "rack_motion_stage1_" + ("_".join(source_job_ids) if source_job_ids else "skeleton3d")

        quality_summary = skeleton3d_payload.get("qualitySummary", {})
        paired_count = quality_summary.get("pairedFrameCount", 0)
        unmatched = quality_summary.get("unmatchedPrimaryCount", 0) + quality_summary.get("unmatchedSecondaryCount", 0)
        sync_status: str = "ok" if unmatched == 0 else "partial"
        sync_policy_id = "rack_motion.stage1.partial_sync" if sync_status == "partial" else None

        session = RackMotionSessionManifest(
            sessionId=session_id,
            sourceRefs=RackMotionSourceRefs(
                skeletonJobIds=source_job_ids if source_job_ids else ["unknown.skeleton3d"],
                calibrationId=calibration_id or "synthetic.stage1.dev",
                rackAlignmentId=rack_alignment.rackAlignmentId,
            ),
            coordinateSpaces=RackMotionCoordinateSpaces(
                captureWorld=RackMotionSpaceSummary(
                    spaceId="capture_world",
                    unit="meter",
                    axisUp="+y",
                    status=None,
                ),
                rackWorld=RackMotionSpaceSummary(
                    spaceId="rack_world",
                    unit="meter",
                    axisUp="+y",
                    status=rack_alignment.status,
                ),
            ),
            syncQuality=RackMotionSyncQuality(
                status=sync_status,
                policyId=sync_policy_id,
                detail={
                    "pairedFrameCount": paired_count,
                    "unmatchedCount": unmatched,
                    "source": "skeleton3d.v1",
                },
            ),
            producer={
                "name": "rack-tracker-stage1-from-skeleton3d",
                "sourceJobIds": source_job_ids,
                "calibrationRef": calibration_ref,
            },
        )

        all_skeleton_frames: list[dict[str, Any]] = skeleton3d_payload.get("frames", [])
        total_frames = len(all_skeleton_frames)
        bounded_offset = min(max(offset, 0), total_frames)
        bounded_limit = min(max(limit, 1), max(total_frames - bounded_offset, 0))
        page_skeleton_frames = all_skeleton_frames[bounded_offset : bounded_offset + bounded_limit]

        rack_frames: list[RackMotionFrame] = []
        for skel_frame in page_skeleton_frames:
            frame_index = int(skel_frame.get("frameIndex", 0))
            timestamp_ms = skel_frame.get("timestampMs")
            person_keypoints = map_skeleton3d_frame(
                skel_frame,
                calibration_id=calibration_id or "synthetic.stage1.dev",
                camera_id_a=camera_id_a,
                camera_id_b=camera_id_b,
            )
            rack_frames.append(
                RackMotionFrame(
                    sessionId=session_id,
                    frameIndex=frame_index,
                    timestampMs=float(timestamp_ms) if timestamp_ms is not None else None,
                    rackAnchors=self._build_rack_anchors(rack_alignment),
                    supportZones=self._build_support_zones(),
                    personKeypoints=person_keypoints,
                    qualityMetrics=[
                        QualityMetric(
                            metricName="sync_delta_ms",
                            value=round(float(skel_frame.get("timestampDeltaMs", 0.0)), 4),
                            status="ok",
                            unit="ms",
                            detail={"source": "skeleton3d.v1"},
                        )
                    ],
                )
            )

        next_start_frame = (
            bounded_offset + len(rack_frames)
            if bounded_offset + len(rack_frames) < total_frames
            else None
        )
        frame_page = RackMotionFramePage(
            page={
                "startFrame": bounded_offset,
                "limit": bounded_limit,
                "totalFrames": total_frames,
                "nextStartFrame": next_start_frame,
            },
            frames=rack_frames,
        )
        return RackMotionViewerFixture(
            session=session,
            rackAlignment=rack_alignment,
            framePage=frame_page,
        ).model_dump(mode="json")

    def get_stage1_fixture(self, *, offset: int = 0, limit: int = 120) -> dict[str, Any]:
        rack_alignment = self._read_rack_alignment(STAGE1_ALIGNMENT_FILE)
        session = self._build_stage1_session(rack_alignment)
        frames = self._build_stage1_frames(
            session_id=session.sessionId,
            rack_alignment=rack_alignment,
        )
        bounded_offset = min(max(offset, 0), len(frames))
        bounded_limit = min(max(limit, 1), max(len(frames) - bounded_offset, 0))
        page_frames = frames[bounded_offset : bounded_offset + bounded_limit]
        next_start_frame = (
            bounded_offset + len(page_frames)
            if bounded_offset + len(page_frames) < len(frames)
            else None
        )
        frame_page = RackMotionFramePage(
            page={
                "startFrame": bounded_offset,
                "limit": bounded_limit,
                "totalFrames": len(frames),
                "nextStartFrame": next_start_frame,
            },
            frames=page_frames,
        )
        return RackMotionViewerFixture(
            session=session,
            rackAlignment=rack_alignment,
            framePage=frame_page,
        ).model_dump(mode="json")

    def _read_rack_alignment(self, filename: str) -> RackAlignmentSummary:
        path = self._fixture_dir / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RackAlignmentSummary.model_validate(payload)

    def _build_stage1_session(
        self,
        rack_alignment: RackAlignmentSummary,
    ) -> RackMotionSessionManifest:
        return RackMotionSessionManifest(
            sessionId="rack_motion_stage1_fixture",
            sourceRefs=RackMotionSourceRefs(
                skeletonJobIds=["synthetic.person_keypoint.stage1"],
                calibrationId="synthetic.capture_world.stage1",
                rackAlignmentId=rack_alignment.rackAlignmentId,
            ),
            coordinateSpaces=RackMotionCoordinateSpaces(
                captureWorld=RackMotionSpaceSummary(
                    spaceId="capture_world",
                    unit="meter",
                    axisUp="+y",
                    status=None,
                ),
                rackWorld=RackMotionSpaceSummary(
                    spaceId="rack_world",
                    unit="meter",
                    axisUp="+y",
                    status=rack_alignment.status,
                ),
            ),
            syncQuality=RackMotionSyncQuality(
                status="ok",
                detail={
                    "frameSource": "synthetic_fixture",
                    "droppedFrameCount": 0,
                },
            ),
            producer={
                "name": "rack-tracker-stage1-fixture",
                "source": "backend/fixtures/rack_motion/virtual_power_rack_dev_alignment.json",
            },
        )

    def _build_stage1_frames(
        self,
        *,
        session_id: str,
        rack_alignment: RackAlignmentSummary,
    ) -> list[RackMotionFrame]:
        frames: list[RackMotionFrame] = []
        for frame_index in range(STAGE1_FRAME_COUNT):
            phase = (frame_index / max(STAGE1_FRAME_COUNT - 1, 1)) * math.tau
            frames.append(
                RackMotionFrame(
                    sessionId=session_id,
                    frameIndex=frame_index,
                    timestampMs=frame_index * (1000 / 30),
                    rackAnchors=self._build_rack_anchors(rack_alignment),
                    supportZones=self._build_support_zones(),
                    personKeypoints=self._build_person_keypoints(
                        frame_index=frame_index,
                        phase=phase,
                    ),
                    qualityMetrics=[
                        QualityMetric(
                            metricName="sync_delta_ms",
                            value=0.0,
                            status="ok",
                            unit="ms",
                            detail={"source": "synthetic_fixture"},
                        )
                    ],
                )
            )
        return frames

    def _build_rack_anchors(self, rack_alignment: RackAlignmentSummary) -> list[RackAnchor]:
        dimensions = rack_alignment.rackDimensionsM
        jcup_height = rack_alignment.jcupHeightsM[0] if rack_alignment.jcupHeightsM else 0.0
        safety_height = (
            rack_alignment.safetyPinHeightsM[0] if rack_alignment.safetyPinHeightsM else 0.0
        )
        half_width = dimensions.width / 2
        half_depth = dimensions.depth / 2
        return [
            RackAnchor(
                anchorId="rack.left_jcup",
                label="Left J-cup",
                x=-half_width,
                y=jcup_height,
                z=-half_depth,
                quality=1.0,
                provenance=rack_alignment.rackAlignmentId or "synthetic_fixture",
            ),
            RackAnchor(
                anchorId="rack.right_jcup",
                label="Right J-cup",
                x=half_width,
                y=jcup_height,
                z=-half_depth,
                quality=1.0,
                provenance=rack_alignment.rackAlignmentId or "synthetic_fixture",
            ),
            RackAnchor(
                anchorId="rack.left_safety_pin",
                label="Left safety pin",
                x=-half_width,
                y=safety_height,
                z=half_depth,
                quality=1.0,
                provenance=rack_alignment.rackAlignmentId or "synthetic_fixture",
            ),
            RackAnchor(
                anchorId="rack.right_safety_pin",
                label="Right safety pin",
                x=half_width,
                y=safety_height,
                z=half_depth,
                quality=1.0,
                provenance=rack_alignment.rackAlignmentId or "synthetic_fixture",
            ),
        ]

    def _build_support_zones(self) -> list[SupportZone]:
        return [
            SupportZone(
                zoneId="rack.jcup_pair",
                label="J-cup pair",
                anchorIds=["rack.left_jcup", "rack.right_jcup"],
                quality=1.0,
            ),
            SupportZone(
                zoneId="rack.safety_pin_pair",
                label="Safety pin pair",
                anchorIds=["rack.left_safety_pin", "rack.right_safety_pin"],
                quality=1.0,
            ),
        ]

    def _build_person_keypoints(
        self,
        *,
        frame_index: int,
        phase: float,
    ) -> list[ReconstructionTarget3D]:
        hip_y = 0.93 + 0.1 * math.sin(phase)
        shoulder_y = hip_y + 0.48
        knee_y = max(0.42, hip_y - 0.42)
        ankle_y = 0.08
        sway_x = 0.03 * math.sin(phase * 0.5)
        torso_z = -0.06 + 0.03 * math.cos(phase)
        points = {
            "person.left_shoulder": (-0.18 + sway_x, shoulder_y, torso_z),
            "person.right_shoulder": (0.18 + sway_x, shoulder_y, torso_z),
            "person.left_hip": (-0.14 + sway_x, hip_y, 0.0),
            "person.right_hip": (0.14 + sway_x, hip_y, 0.0),
            "person.left_knee": (-0.16 + sway_x, knee_y, 0.07),
            "person.right_knee": (0.16 + sway_x, knee_y, 0.07),
            "person.left_ankle": (-0.18 + sway_x, ankle_y, 0.09),
            "person.right_ankle": (0.18 + sway_x, ankle_y, 0.09),
        }
        return [
            ReconstructionTarget3D(
                frameIndex=frame_index,
                targetId=target_id,
                spaceId="rack_world",
                unit="meter",
                x=x,
                y=y,
                z=z,
                quality=0.9,
                mode="simulated",
                status="valid",
                qualityMetrics=[
                    QualityMetric(
                        metricName="target_fixture_quality",
                        value=0.9,
                        status="ok",
                        unit="ratio",
                        detail={"source": "synthetic_fixture"},
                    )
                ],
            )
            for target_id, (x, y, z) in points.items()
        ]
