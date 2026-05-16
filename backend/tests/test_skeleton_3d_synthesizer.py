import json
from pathlib import Path

from schema.pose import (
    AlignedPoseChunkPair,
    PoseChunk,
    PoseChunkStreamItem,
    PoseFrameResult,
    PoseLandmarkPoint,
)
from schema.synthesis import SynthesisInput, SynthesisThresholds
from service.camera_calibration import CameraCalibrationService
from service.landmark_observation import POSE_LANDMARK_NAMES
from service.skeleton_3d_synthesizer import (
    Skeleton3DSynthesisError,
    Skeleton3DSynthesizer,
    SynthesisChunkResult,
)
from service.skeleton_artifact_repository import SkeletonArtifactRepository


def _write_calibration(path: Path) -> None:
    payload = {
        "cameras": [
            {
                "name": "A",
                "resolution": [640, 480],
                "K": [[1000.0, 0.0, 320.0], [0.0, 1000.0, 240.0], [0.0, 0.0, 1.0]],
                "distCoef": [0.0, 0.0, 0.0, 0.0, 0.0],
                "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "t": [[0.0], [0.0], [0.0]],
            },
            {
                "name": "B",
                "resolution": [640, 480],
                "K": [[1000.0, 0.0, 320.0], [0.0, 1000.0, 240.0], [0.0, 0.0, 1.0]],
                "distCoef": [0.0, 0.0, 0.0, 0.0, 0.0],
                "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "t": [[-1.0], [0.0], [0.0]],
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _skeleton(*, x: float, camera_id: str | None = None, calibration_ref: str | None = None) -> dict:
    landmarks = [
        {
            "name": name,
            "x": x,
            "y": 0.5,
            "z": 0.0,
            "visibility": 1.0,
            "presence": 1.0,
        }
        for name in POSE_LANDMARK_NAMES
    ]
    video_info = {
        "width": 640,
        "height": 480,
        "effectiveSamplingFps": 30.0,
    }
    payload = {
        "frames": [
            {
                "frameIndex": 0,
                "timestampMs": 0.0,
                "poseDetected": True,
                "landmarks": landmarks,
            }
        ],
        "videoInfo": video_info,
        "nextTimestampCursorMs": 1.0,
    }
    if camera_id is not None:
        camera_binding = {
            "sourceCameraId": camera_id,
            "calibrationCameraId": camera_id,
            "bindingSource": "test",
        }
        if calibration_ref is not None:
            camera_binding["calibrationRef"] = calibration_ref
        video_info["cameraId"] = camera_id
        video_info["cameraBinding"] = camera_binding
        payload["cameraBinding"] = camera_binding
    return payload


def test_synthesizer_writes_skeleton3d_shape_from_two_source_artifacts(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"
    _write_calibration(calibration_path)
    sources = {
        "job_a": _skeleton(x=0.5),
        "job_b": _skeleton(x=0.1875),
    }
    repository = SkeletonArtifactRepository(
        synthesis_dir=tmp_path / "synthesis",
        source_loader=lambda job_id: sources[job_id],
    )
    synthesizer = Skeleton3DSynthesizer(artifact_repository=repository)

    payload = synthesizer.synthesize(
        SynthesisInput(
            sourceJobIdA="job_a",
            sourceJobIdB="job_b",
            cameraIdA="A",
            cameraIdB="B",
            calibrationRef=str(calibration_path),
        )
    )

    assert payload["schemaVersion"] == "skeleton3d.v1"
    assert payload["qualitySummary"]["pairedFrameCount"] == 1
    assert payload["qualitySummary"]["usableJointRatio"] == 1.0
    first_joint = payload["frames"][0]["joints"][0]
    assert first_joint["success"] is True
    assert abs(first_joint["position"]["z"] - 5.0) < 1e-6
    assert payload["debugReport"]["schemaVersion"] == "synthesis_debug_report.v1"
    assert payload["debugReport"]["frameAlignmentDebug"]["samples"][0]["frameIndexDelta"] == 0

    view_hint = payload["synthesisInfo"]["viewHint"]
    assert view_hint["upAxis"] == "y"
    assert view_hint["upAxisDirection"] == "negative"
    assert view_hint["groundPlaneValue"] == 0.0
    front_view = view_hint["frontView"]
    assert "cameraMidpointXZ" in front_view
    # Camera A center: -R^T t = [0,0,0], Camera B center: [1,0,0]; midpoint XZ = [0.5, 0.0]
    assert front_view["cameraMidpointXZ"] == [0.5, 0.0]
    assert front_view["eyeHeightWorld"] == -150.0


def test_synthesizer_rejects_declared_camera_binding_mismatch(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"
    _write_calibration(calibration_path)
    sources = {
        "job_a": _skeleton(x=0.5, camera_id="A", calibration_ref=str(calibration_path)),
        "job_b": _skeleton(x=0.1875, camera_id="B", calibration_ref=str(calibration_path)),
    }
    repository = SkeletonArtifactRepository(
        synthesis_dir=tmp_path / "synthesis",
        source_loader=lambda job_id: sources[job_id],
    )
    synthesizer = Skeleton3DSynthesizer(artifact_repository=repository)

    try:
        synthesizer.synthesize(
            SynthesisInput(
                sourceJobIdA="job_a",
                sourceJobIdB="job_b",
                cameraIdA="B",
                cameraIdB="A",
                calibrationRef=str(calibration_path),
            )
        )
    except Skeleton3DSynthesisError as exc:
        assert "camera_binding_mismatch" in str(exc)
        assert "source A" in str(exc)
    else:
        raise AssertionError("Expected camera binding mismatch")


# --- synthesize_chunk tests ---


def _make_pose_chunk(
    chunk_index: int,
    *,
    x: float,
    frame_count: int = 1,
    start_timestamp_ms: float = 0.0,
    fps: float = 30.0,
) -> PoseChunk:
    frames = []
    for i in range(frame_count):
        landmarks = [
            PoseLandmarkPoint(name=name, x=x, y=0.5, z=0.0, visibility=1.0, presence=1.0)
            for name in POSE_LANDMARK_NAMES
        ]
        frames.append(
            PoseFrameResult(
                frame_index=chunk_index * frame_count + i,
                timestamp_ms=start_timestamp_ms + i * (1000.0 / fps),
                pose_detected=True,
                landmarks=landmarks,
            )
        )
    return PoseChunk(
        chunk_index=chunk_index,
        start_frame_index=chunk_index * frame_count,
        end_frame_index=chunk_index * frame_count + frame_count - 1,
        frames=frames,
    )


def _make_aligned_pair(chunk_index: int, *, x_a: float, x_b: float, frame_count: int = 1) -> AlignedPoseChunkPair:
    return AlignedPoseChunkPair(
        chunk_index=chunk_index,
        primary=PoseChunkStreamItem(stream_id="video_a", chunk=_make_pose_chunk(chunk_index, x=x_a, frame_count=frame_count)),
        secondary=PoseChunkStreamItem(stream_id="video_b", chunk=_make_pose_chunk(chunk_index, x=x_b, frame_count=frame_count)),
    )


def _make_synthesizer(tmp_path: Path) -> tuple[Skeleton3DSynthesizer, object, object]:
    calibration_path = tmp_path / "calibration.json"
    _write_calibration(calibration_path)
    repository = SkeletonArtifactRepository(
        synthesis_dir=tmp_path / "synthesis",
        source_loader=lambda _: {},
    )
    synthesizer = Skeleton3DSynthesizer(artifact_repository=repository)
    camera_a, camera_b = CameraCalibrationService().load_pair(str(calibration_path), "A", "B")
    return synthesizer, camera_a, camera_b


def test_synthesize_chunk_returns_synthesis_chunk_result(tmp_path: Path) -> None:
    synthesizer, camera_a, camera_b = _make_synthesizer(tmp_path)
    aligned_pair = _make_aligned_pair(0, x_a=0.5, x_b=0.1875)

    result = synthesizer.synthesize_chunk(
        aligned_pair,
        camera_a=camera_a,
        camera_b=camera_b,
        camera_id_a="A",
        camera_id_b="B",
        max_delta_ms=1000.0 / 30.0 / 2.0,
        thresholds=SynthesisThresholds(),
    )

    assert isinstance(result, SynthesisChunkResult)
    assert result.chunk_index == 0


def test_synthesize_chunk_produces_correct_3d_output(tmp_path: Path) -> None:
    synthesizer, camera_a, camera_b = _make_synthesizer(tmp_path)
    aligned_pair = _make_aligned_pair(0, x_a=0.5, x_b=0.1875)

    result = synthesizer.synthesize_chunk(
        aligned_pair,
        camera_a=camera_a,
        camera_b=camera_b,
        camera_id_a="A",
        camera_id_b="B",
        max_delta_ms=1000.0 / 30.0 / 2.0,
        thresholds=SynthesisThresholds(),
    )

    assert len(result.frames) == 1
    assert result.total_joint_count == len(POSE_LANDMARK_NAMES)
    assert result.success_joint_count == len(POSE_LANDMARK_NAMES)
    first_joint = result.frames[0]["joints"][0]
    assert first_joint["success"] is True
    assert abs(first_joint["position"]["z"] - 5.0) < 1e-6
    assert result.alignment_summary["pairedFrameCount"] == 1


def test_synthesize_chunk_preserves_chunk_index(tmp_path: Path) -> None:
    synthesizer, camera_a, camera_b = _make_synthesizer(tmp_path)
    aligned_pair = _make_aligned_pair(7, x_a=0.5, x_b=0.1875)

    result = synthesizer.synthesize_chunk(
        aligned_pair,
        camera_a=camera_a,
        camera_b=camera_b,
        camera_id_a="A",
        camera_id_b="B",
        max_delta_ms=1000.0 / 30.0 / 2.0,
        thresholds=SynthesisThresholds(),
    )

    assert result.chunk_index == 7


def test_synthesize_chunk_handles_multiple_frames(tmp_path: Path) -> None:
    synthesizer, camera_a, camera_b = _make_synthesizer(tmp_path)
    aligned_pair = _make_aligned_pair(0, x_a=0.5, x_b=0.1875, frame_count=4)

    result = synthesizer.synthesize_chunk(
        aligned_pair,
        camera_a=camera_a,
        camera_b=camera_b,
        camera_id_a="A",
        camera_id_b="B",
        max_delta_ms=1000.0 / 30.0 / 2.0,
        thresholds=SynthesisThresholds(),
    )

    assert len(result.frames) == 4
    assert result.total_joint_count == 4 * len(POSE_LANDMARK_NAMES)
    assert result.alignment_summary["pairedFrameCount"] == 4
