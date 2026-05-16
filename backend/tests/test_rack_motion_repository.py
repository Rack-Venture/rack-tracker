import json

from service.rack_motion_repository import RackMotionArtifactRepository


def _make_skeleton3d_joint(name: str, *, success: bool = True, reproj_error: float = 2.5):
    position = {"x": -14.3, "y": -145.0, "z": 5.0} if success else None
    return {
        "name": name,
        "landmarkIndex": 0,
        "position": position,
        "diagnosticPosition": {"x": -14.3, "y": -145.0, "z": 5.0},
        "success": success,
        "failureReason": None if success else "high_reprojection_error",
        "reprojectionErrorPx": reproj_error,
        "cameraDepths": {"00_11": 2.1, "00_21": 2.0},
        "observations": {},
    }


def _make_skeleton3d_frame(frame_index: int = 0) -> dict:
    return {
        "frameIndex": frame_index,
        "timestampMs": frame_index * 33.33,
        "timestampDeltaMs": 1.2,
        "joints": [
            _make_skeleton3d_joint("left_shoulder"),
            _make_skeleton3d_joint("right_shoulder"),
            _make_skeleton3d_joint("left_hip"),
            _make_skeleton3d_joint("right_hip"),
            _make_skeleton3d_joint("left_knee", success=False, reproj_error=12.0),
            _make_skeleton3d_joint("nose", success=True, reproj_error=1.5),
            _make_skeleton3d_joint("left_eye"),
        ],
    }


def _make_skeleton3d_payload(num_frames: int = 3) -> dict:
    return {
        "schemaVersion": "skeleton3d.v1",
        "synthesisInfo": {
            "sourceJobIds": ["job_a_test", "job_b_test"],
            "cameraPair": ["00_11", "00_21"],
            "calibrationRef": "calibration_171204_pose1.json",
        },
        "qualitySummary": {
            "pairedFrameCount": num_frames,
            "unmatchedPrimaryCount": 0,
            "unmatchedSecondaryCount": 0,
        },
        "frames": [_make_skeleton3d_frame(i) for i in range(num_frames)],
    }


def _write_alignment(path, *, width=1.5, depth=1.4, height=2.4):
    path.write_text(
        json.dumps(
            {
                "schemaVersion": "rack_motion.rack_alignment_summary.v1",
                "rackAlignmentId": "test_stage1_alignment",
                "status": "dev_assumption",
                "rackDimensionsM": {
                    "width": width,
                    "depth": depth,
                    "height": height,
                },
                "jcupHeightsM": [1.1],
                "safetyPinHeightsM": [0.66],
                "displayUnit": "cm",
                "captureToRackStatus": "identity_assumed",
                "qualityMetrics": [
                    {
                        "metricName": "rack_alignment_status",
                        "value": "dev_assumption",
                        "status": "warning",
                        "policyId": "rack_motion.test.dev_alignment",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_stage1_fixture_uses_alignment_file_dimensions(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json", width=1.5)
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)

    fixture = repository.get_stage1_fixture(offset=1, limit=2)

    assert fixture["schemaVersion"] == "rack_motion.viewer_fixture.v1"
    assert fixture["rackAlignment"]["rackDimensionsM"]["width"] == 1.5
    assert fixture["rackAlignment"]["status"] == "dev_assumption"
    assert fixture["session"]["coordinateSpaces"]["rackWorld"]["status"] == "dev_assumption"
    assert fixture["framePage"]["page"]["startFrame"] == 1
    assert len(fixture["framePage"]["frames"]) == 2


def test_stage1_fixture_person_keypoints_are_rack_world_records(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json")
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)

    fixture = repository.get_stage1_fixture(offset=0, limit=1)
    frame = fixture["framePage"]["frames"][0]

    assert frame["schemaVersion"] == "rack_motion.frame.v1"
    assert frame["rackAnchors"][0]["spaceId"] == "rack_world"
    assert frame["personKeypoints"]
    assert all(point["spaceId"] == "rack_world" for point in frame["personKeypoints"])
    assert all(point["targetId"].startswith("person.") for point in frame["personKeypoints"])


def test_from_skeleton3d_produces_rack_world_keypoints(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json")
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)
    payload = _make_skeleton3d_payload(num_frames=3)

    fixture = repository.get_stage1_fixture_from_skeleton3d(payload, offset=0, limit=3)

    assert fixture["schemaVersion"] == "rack_motion.viewer_fixture.v1"
    assert "job_a_test" in fixture["session"]["sessionId"]
    assert fixture["session"]["sourceRefs"]["skeletonJobIds"] == ["job_a_test", "job_b_test"]

    frame = fixture["framePage"]["frames"][0]
    assert frame["schemaVersion"] == "rack_motion.frame.v1"
    keypoints = frame["personKeypoints"]
    assert keypoints
    assert all(p["spaceId"] == "rack_world" for p in keypoints)
    assert all(p["targetId"].startswith("person.") for p in keypoints)
    # left_eye is now part of the full 33-landmark set
    assert any(p["targetId"] == "person.left_eye" for p in keypoints)


def test_from_skeleton3d_converts_cm_to_meters(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json")
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)
    payload = _make_skeleton3d_payload(num_frames=1)

    fixture = repository.get_stage1_fixture_from_skeleton3d(payload, offset=0, limit=1)
    frame = fixture["framePage"]["frames"][0]
    shoulder = next(p for p in frame["personKeypoints"] if p["targetId"] == "person.left_shoulder")

    # panoptic (x=-14.3, y=-145.0, z=5.0 cm) → rack_world:
    #   rack_x = -panoptic_z * CM_TO_M = -0.05
    #   rack_y = -panoptic_y * CM_TO_M = +1.45
    #   rack_z = -panoptic_x * CM_TO_M = +0.143
    assert abs(shoulder["x"] - (-0.05)) < 1e-4
    assert abs(shoulder["y"] - 1.45) < 1e-4
    assert abs(shoulder["z"] - 0.143) < 1e-4
    assert shoulder["unit"] == "meter"


def test_from_skeleton3d_invalid_joint_included_with_reproj_error(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json")
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)
    payload = _make_skeleton3d_payload(num_frames=1)

    fixture = repository.get_stage1_fixture_from_skeleton3d(payload, offset=0, limit=1)
    frame = fixture["framePage"]["frames"][0]
    # left_knee was created with success=False, reproj_error=12.0
    knee = next((p for p in frame["personKeypoints"] if p["targetId"] == "person.left_knee"), None)
    assert knee is not None
    assert knee["status"] == "invalid"
    assert knee["failureReason"] is not None


def test_from_skeleton3d_pagination(tmp_path) -> None:
    _write_alignment(tmp_path / "virtual_power_rack_dev_alignment.json")
    repository = RackMotionArtifactRepository(fixture_dir=tmp_path)
    payload = _make_skeleton3d_payload(num_frames=5)

    fixture = repository.get_stage1_fixture_from_skeleton3d(payload, offset=2, limit=2)

    assert fixture["framePage"]["page"]["startFrame"] == 2
    assert len(fixture["framePage"]["frames"]) == 2
    assert fixture["framePage"]["page"]["totalFrames"] == 5
