from pydantic import ValidationError

from schema.rack_motion import (
    BarbellEntity,
    ImageSize,
    Observation2D,
    QualityMetric,
    RackAnchor,
    RackMotionFrame,
    ReconstructionTarget3D,
    SupportZone,
)


def _rack_point(target_id: str, x: float, y: float, z: float) -> ReconstructionTarget3D:
    return ReconstructionTarget3D(
        frameIndex=12,
        targetId=target_id,
        spaceId="rack_world",
        unit="meter",
        x=x,
        y=y,
        z=z,
        quality=0.95,
        mode="multi_camera",
        calibrationId="calibration.synthetic",
        usedCameraIds=["cam.left", "cam.right"],
        reprojectionErrorPx=0.2,
        status="valid",
    )


def test_observation_requires_detected_pixel_coordinates() -> None:
    observation = Observation2D(
        sessionId="session.synthetic",
        cameraId="cam.left",
        frameIndex=3,
        targetId="bar_left_endpoint",
        imageSize=ImageSize(width=640, height=480),
        x=320.0,
        y=240.0,
        confidence=0.9,
        status="detected",
    )

    assert observation.spaceId == "source_image_pixels"
    assert observation.confidence == 0.9


def test_observation_rejects_out_of_bounds_detected_point() -> None:
    try:
        Observation2D(
            sessionId="session.synthetic",
            cameraId="cam.left",
            frameIndex=3,
            targetId="bar_left_endpoint",
            imageSize=ImageSize(width=640, height=480),
            x=640.0,
            y=240.0,
            confidence=0.9,
            status="detected",
        )
    except ValidationError as exc:
        assert "x must be within image bounds" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")


def test_multi_camera_reconstruction_requires_two_cameras_and_quality() -> None:
    target = ReconstructionTarget3D(
        frameIndex=4,
        targetId="bar_center",
        spaceId="capture_world",
        unit="meter",
        x=0.0,
        y=1.2,
        z=2.4,
        quality=0.88,
        mode="multi_camera",
        calibrationId="calibration.synthetic",
        usedCameraIds=["cam.left", "cam.right"],
        reprojectionErrorPx=0.4,
        status="valid",
    )

    assert target.status == "valid"
    assert target.reprojectionErrorPx == 0.4


def test_single_camera_estimate_cannot_be_marked_valid() -> None:
    try:
        ReconstructionTarget3D(
            frameIndex=4,
            targetId="bar_center",
            spaceId="rack_world",
            unit="meter",
            x=0.0,
            y=1.2,
            z=2.4,
            quality=0.4,
            mode="single_camera_estimate",
            usedCameraIds=["cam.left"],
            status="valid",
        )
    except ValidationError as exc:
        assert "single_camera_estimate must not be marked as valid" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")


def test_frame_rejects_support_zone_with_missing_anchor() -> None:
    try:
        RackMotionFrame(
            sessionId="session.synthetic",
            frameIndex=7,
            rackAnchors=[
                RackAnchor(
                    anchorId="left_jcup",
                    label="Left J-cup",
                    x=-0.6,
                    y=1.3,
                    z=0.0,
                    quality=1.0,
                    provenance="synthetic",
                )
            ],
            supportZones=[
                SupportZone(
                    zoneId="jcup_pair",
                    label="J-cup pair",
                    anchorIds=["left_jcup", "right_jcup"],
                    quality=1.0,
                )
            ],
        )
    except ValidationError as exc:
        assert "supportZones reference missing rack anchors" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")


def test_rack_motion_frame_accepts_barbell_endpoints_and_quality_metric() -> None:
    frame = RackMotionFrame(
        sessionId="session.synthetic",
        frameIndex=12,
        rackAnchors=[
            RackAnchor(
                anchorId="left_jcup",
                label="Left J-cup",
                x=-0.6,
                y=1.3,
                z=0.0,
                quality=1.0,
                provenance="synthetic",
            ),
            RackAnchor(
                anchorId="right_jcup",
                label="Right J-cup",
                x=0.6,
                y=1.3,
                z=0.0,
                quality=1.0,
                provenance="synthetic",
            ),
        ],
        supportZones=[
            SupportZone(
                zoneId="jcup_pair",
                label="J-cup pair",
                anchorIds=["left_jcup", "right_jcup"],
                quality=1.0,
            )
        ],
        barbell=BarbellEntity(
            entityId="barbell.primary",
            leftEndpoint=_rack_point("bar_left_endpoint", -0.55, 1.31, 0.08),
            rightEndpoint=_rack_point("bar_right_endpoint", 0.55, 1.30, 0.08),
            center=_rack_point("bar_center", 0.0, 1.305, 0.08),
            quality=0.94,
        ),
        qualityMetrics=[
            QualityMetric(
                metricName="rack_alignment_quality",
                value=0.98,
                status="ok",
                unit="ratio",
            )
        ],
    )

    assert frame.schemaVersion == "rack_motion.frame.v1"
    assert frame.barbell is not None
    assert frame.barbell.leftEndpoint.targetId == "bar_left_endpoint"


def test_rack_motion_frame_accepts_rack_world_person_keypoints() -> None:
    frame = RackMotionFrame(
        sessionId="session.synthetic",
        frameIndex=2,
        personKeypoints=[
            ReconstructionTarget3D(
                frameIndex=2,
                targetId="person.left_shoulder",
                spaceId="rack_world",
                unit="meter",
                x=-0.2,
                y=1.4,
                z=0.1,
                quality=0.9,
                mode="simulated",
                status="valid",
            )
        ],
    )

    assert frame.personKeypoints[0].targetId == "person.left_shoulder"


def test_rack_motion_frame_rejects_non_person_keypoint_namespace() -> None:
    try:
        RackMotionFrame(
            sessionId="session.synthetic",
            frameIndex=2,
            personKeypoints=[
                ReconstructionTarget3D(
                    frameIndex=2,
                    targetId="left_shoulder",
                    spaceId="rack_world",
                    unit="meter",
                    x=-0.2,
                    y=1.4,
                    z=0.1,
                    quality=0.9,
                    mode="simulated",
                    status="valid",
                )
            ],
        )
    except ValidationError as exc:
        assert "personKeypoints targetId must use the person. namespace" in str(exc)
    else:
        raise AssertionError("Expected ValidationError")
