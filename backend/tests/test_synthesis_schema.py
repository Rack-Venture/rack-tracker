from pydantic import ValidationError

from schema.synthesis import SynthesisInput, SynthesisJobCreateRequest, StreamingPairManifest


def _request_payload() -> dict:
    return {
        "pairManifest": {
            "sources": {
                "A": {"sourceJobId": "job_a", "cameraId": "00_00"},
                "B": {"sourceJobId": "job_b", "cameraId": "00_01"},
            },
            "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
            "sync": {
                "mode": "timestamp",
                "timestampDomain": "media_time_ms",
                "maxDeltaMs": 16.7,
            },
            "landmarkSet": "mediapipe_pose_33",
            "outputCoordinateSystem": "panoptic_world_cm",
        },
        "options": {"runEvaluation": True},
    }


def test_pair_manifest_normalizes_to_synthesis_input() -> None:
    request = SynthesisJobCreateRequest.model_validate(_request_payload())
    synthesis_input = SynthesisInput.from_manifest(request.pairManifest)

    assert synthesis_input.sourceJobIdA == "job_a"
    assert synthesis_input.sourceJobIdB == "job_b"
    assert synthesis_input.cameraIdA == "00_00"
    assert synthesis_input.cameraIdB == "00_01"
    assert synthesis_input.sync.maxDeltaMs == 16.7


def test_pair_manifest_rejects_same_source_job() -> None:
    payload = _request_payload()
    payload["pairManifest"]["sources"]["B"]["sourceJobId"] = "job_a"

    try:
        SynthesisJobCreateRequest.model_validate(payload)
    except ValidationError as exc:
        assert "sourceJobId" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")


def _streaming_payload() -> dict:
    return {
        "streamingManifest": {
            "sources": {
                "A": {"videoPath": "/data/videos/cam_a.mp4", "cameraId": "cam_00"},
                "B": {"videoPath": "/data/videos/cam_b.mp4", "cameraId": "cam_01"},
            },
            "calibrationRef": "calibration.json",
            "sync": {"mode": "timestamp", "maxDeltaMs": 16.7},
        }
    }


def test_streaming_manifest_parses_correctly() -> None:
    request = SynthesisJobCreateRequest.model_validate(_streaming_payload())
    assert request.pairManifest is None
    assert request.streamingManifest is not None
    m = request.streamingManifest
    assert m.sources.A.videoPath == "/data/videos/cam_a.mp4"
    assert m.sources.A.cameraId == "cam_00"
    assert m.sources.B.cameraId == "cam_01"
    assert m.sync.maxDeltaMs == 16.7


def test_streaming_manifest_rejects_same_camera_id() -> None:
    payload = _streaming_payload()
    payload["streamingManifest"]["sources"]["B"]["cameraId"] = "cam_00"
    try:
        SynthesisJobCreateRequest.model_validate(payload)
    except ValidationError as exc:
        assert "cameraId" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")


def test_request_rejects_no_manifest() -> None:
    try:
        SynthesisJobCreateRequest.model_validate({"options": {}})
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError")


def test_request_rejects_both_manifests() -> None:
    payload = {**_request_payload(), **_streaming_payload()}
    try:
        SynthesisJobCreateRequest.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError")
