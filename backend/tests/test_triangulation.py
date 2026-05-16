import numpy as np

from schema.synthesis import SynthesisThresholds
from service.camera_calibration import CameraModel
from service.landmark_observation import LandmarkObservation
from service.triangulation import TriangulationService


def _camera(camera_id: str, camera_center_x: float) -> CameraModel:
    k = np.asarray(
        [
            [1000.0, 0.0, 320.0],
            [0.0, 1000.0, 240.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    r = np.eye(3, dtype=np.float64)
    t = np.asarray([[-camera_center_x], [0.0], [0.0]], dtype=np.float64)
    return CameraModel(
        camera_id=camera_id,
        image_width=640,
        image_height=480,
        K=k,
        dist_coeffs=np.zeros((5, 1), dtype=np.float64),
        R=r,
        t=t,
        projection_matrix=k @ np.hstack([r, t]),
    )


def test_triangulates_synthetic_joint_and_scores_reprojection() -> None:
    camera_a = _camera("A", 0.0)
    camera_b = _camera("B", 1.0)
    observation_a = LandmarkObservation(
        name="nose",
        landmark_index=0,
        normalized=(0.5, 0.5),
        pixel=(320.0, 240.0),
        visibility=1.0,
        presence=1.0,
    )
    observation_b = LandmarkObservation(
        name="nose",
        landmark_index=0,
        normalized=(0.1875, 0.5),
        pixel=(120.0, 240.0),
        visibility=1.0,
        presence=1.0,
    )

    joint = TriangulationService().triangulate_joint(
        observation_a=observation_a,
        observation_b=observation_b,
        camera_a=camera_a,
        camera_b=camera_b,
        thresholds=SynthesisThresholds(maxReprojectionErrorPx=0.01),
    )

    assert joint.success is True
    assert joint.position is not None
    assert abs(joint.position[0]) < 1e-6
    assert abs(joint.position[1]) < 1e-6
    assert abs(joint.position[2] - 5.0) < 1e-6
    assert joint.mean_reprojection_error_px is not None
    assert joint.mean_reprojection_error_px < 1e-6


class _FixedReprojectionScorer:
    def __init__(self, value: float) -> None:
        self.value = value

    def score(self, **_kwargs) -> float:
        return self.value


def test_high_reprojection_error_keeps_diagnostic_position_non_renderable() -> None:
    camera_a = _camera("A", 0.0)
    camera_b = _camera("B", 1.0)
    observation_a = LandmarkObservation(
        name="nose",
        landmark_index=0,
        normalized=(0.5, 0.5),
        pixel=(320.0, 240.0),
        visibility=1.0,
        presence=1.0,
    )
    observation_b = LandmarkObservation(
        name="nose",
        landmark_index=0,
        normalized=(0.1875, 0.5),
        pixel=(120.0, 240.0),
        visibility=1.0,
        presence=1.0,
    )

    service = TriangulationService(
        reprojection_scorer=_FixedReprojectionScorer(value=20.0)
    )
    joint = service.triangulate_joint(
        observation_a=observation_a,
        observation_b=observation_b,
        camera_a=camera_a,
        camera_b=camera_b,
        thresholds=SynthesisThresholds(maxReprojectionErrorPx=8.0),
    )
    payload = service.joint_to_payload(
        joint=joint,
        observation_a=observation_a,
        observation_b=observation_b,
        camera_id_a="A",
        camera_id_b="B",
    )

    assert joint.success is False
    assert joint.failure_reason == "high_reprojection_error"
    assert joint.position is None
    assert joint.diagnostic_position is not None
    assert payload["position"] is None
    assert payload["diagnosticPosition"] is not None
    assert payload["epipolarSampsonErrorPx"] is not None
