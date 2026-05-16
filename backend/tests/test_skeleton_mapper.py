from pathlib import Path

from schema.frame import FrameExtractionResult
from schema.pose import PoseInferenceResult
from service.skeleton_mapper import SkeletonMapperService


def test_skeleton_mapper_adds_camera_binding_and_coordinate_space(tmp_path: Path) -> None:
    extraction = FrameExtractionResult(
        source_path=Path("171204_pose1/171204_pose1/hdVideos_2min/hd_00_21_2min.mp4"),
        backend="opencv",
        source_fps=29.97,
        frame_count=100,
        width=1920,
        height=1080,
        extracted_count=0,
        frames=[],
    )
    inference = PoseInferenceResult(
        source_path=str(extraction.source_path),
        running_mode="VIDEO",
        model_name="pose_landmarker_full",
        inference_backend="python",
        frame_count=0,
        detected_frame_count=0,
        requested_delegate="CPU",
        actual_delegate="CPU",
        delegate_fallback_applied=False,
        delegate_errors={},
        frames=[],
    )

    skeleton = SkeletonMapperService(repo_root=tmp_path).map_landmarks(
        extraction,
        inference,
        display_name="hd_00_21_2min.mp4",
    )

    assert skeleton["cameraBinding"]["sourceCameraId"] == "00_21"
    assert skeleton["cameraBinding"]["calibrationCameraId"] == "00_21"
    assert skeleton["cameraBinding"]["calibrationRef"] == (
        "171204_pose1/171204_pose1/calibration_171204_pose1.json"
    )
    assert skeleton["videoInfo"]["cameraId"] == "00_21"
    assert skeleton["videoInfo"]["cameraBinding"]["sourceCameraId"] == "00_21"
    assert skeleton["imageCoordinateSpace"]["landmarkSpace"] == "mediapipe_normalized_image"
    assert skeleton["imageCoordinateSpace"]["pixelBasis"] == {
        "width": 1920,
        "height": 1080,
    }
