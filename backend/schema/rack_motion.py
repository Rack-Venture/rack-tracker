from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CoordinateSpaceId = Literal[
    "source_image_pixels",
    "detector_input_pixels",
    "camera_space",
    "capture_world",
    "rack_world",
]
ObservationStatus = Literal["detected", "missing", "outside_roi", "rejected_by_policy"]
ReconstructionMode = Literal["multi_camera", "single_camera_estimate", "simulated"]
ReconstructionStatus = Literal["valid", "invalid", "degraded", "interpolated"]
QualityStatus = Literal["ok", "warning", "failed", "not_applicable", "not_computed"]
RackAlignmentStatus = Literal["calibrated", "dev_assumption", "not_computed"]
CaptureToRackStatus = Literal["calibrated", "identity_assumed", "not_computed"]
SyncQualityStatus = Literal["ok", "partial", "warn"]


class _TextModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip_text_values(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ImageSize(_TextModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class CoordinateSpace(_TextModel):
    spaceId: CoordinateSpaceId
    unit: str = Field(min_length=1)
    axes: tuple[str, ...] = Field(min_length=2)
    provenance: str = Field(min_length=1)

    @field_validator("axes")
    @classmethod
    def _validate_axes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("axes must be unique")
        if any(not axis for axis in value):
            raise ValueError("axes must not contain empty values")
        return value


class QualityMetric(_TextModel):
    metricName: str = Field(min_length=1)
    value: float | int | bool | str | None = None
    status: QualityStatus = "not_computed"
    unit: str | None = None
    policyId: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_policy_for_thresholded_status(self) -> "QualityMetric":
        if self.status in {"warning", "failed"} and not self.policyId:
            raise ValueError("policyId is required for warning or failed quality metrics")
        return self


class RackMotionSourceRefs(_TextModel):
    skeletonJobIds: list[str] = Field(default_factory=list)
    calibrationId: str = Field(min_length=1)
    rackAlignmentId: str | None = None

    @field_validator("skeletonJobIds")
    @classmethod
    def _validate_skeleton_job_ids(cls, value: list[str]) -> list[str]:
        stripped = [job_id.strip() for job_id in value]
        if any(not job_id for job_id in stripped):
            raise ValueError("skeletonJobIds must not contain empty values")
        if len(set(stripped)) != len(stripped):
            raise ValueError("skeletonJobIds must be unique")
        return stripped


class RackMotionSpaceSummary(_TextModel):
    spaceId: Literal["capture_world", "rack_world"]
    unit: str = Field(min_length=1)
    axisUp: str = Field(min_length=1)
    status: RackAlignmentStatus | None = None

    @model_validator(mode="after")
    def _validate_rack_world_status(self) -> "RackMotionSpaceSummary":
        if self.spaceId == "rack_world" and self.status is None:
            raise ValueError("rack_world space summaries require status")
        return self


class RackMotionCoordinateSpaces(BaseModel):
    captureWorld: RackMotionSpaceSummary
    rackWorld: RackMotionSpaceSummary

    @model_validator(mode="after")
    def _validate_space_ids(self) -> "RackMotionCoordinateSpaces":
        if self.captureWorld.spaceId != "capture_world":
            raise ValueError("captureWorld must describe capture_world")
        if self.rackWorld.spaceId != "rack_world":
            raise ValueError("rackWorld must describe rack_world")
        return self


class RackMotionSyncQuality(_TextModel):
    status: SyncQualityStatus = "ok"
    policyId: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_sync_policy(self) -> "RackMotionSyncQuality":
        if self.status in {"partial", "warn"} and not self.policyId:
            raise ValueError("policyId is required for partial or warn sync quality")
        return self


class RackMotionSessionManifest(_TextModel):
    schemaVersion: Literal["rack_motion.session.v1"] = "rack_motion.session.v1"
    sessionId: str = Field(min_length=1)
    sourceRefs: RackMotionSourceRefs
    coordinateSpaces: RackMotionCoordinateSpaces
    syncQuality: RackMotionSyncQuality = Field(default_factory=RackMotionSyncQuality)
    producer: dict[str, Any] = Field(default_factory=dict)


class RackDimensions(_TextModel):
    width: float = Field(gt=0.0)
    depth: float = Field(gt=0.0)
    height: float = Field(gt=0.0)


class RackAlignmentSummary(_TextModel):
    schemaVersion: Literal["rack_motion.rack_alignment_summary.v1"] = (
        "rack_motion.rack_alignment_summary.v1"
    )
    rackAlignmentId: str | None = None
    status: RackAlignmentStatus
    rackDimensionsM: RackDimensions
    jcupHeightsM: list[float] = Field(default_factory=list)
    safetyPinHeightsM: list[float] = Field(default_factory=list)
    displayUnit: Literal["cm", "m"] = "cm"
    captureToRackStatus: CaptureToRackStatus
    qualityMetrics: list[QualityMetric] = Field(default_factory=list)

    @field_validator("jcupHeightsM", "safetyPinHeightsM")
    @classmethod
    def _validate_heights(cls, value: list[float]) -> list[float]:
        if any(height < 0 for height in value):
            raise ValueError("rack heights must be non-negative")
        return value

    @model_validator(mode="after")
    def _validate_alignment_state(self) -> "RackAlignmentSummary":
        if self.status != "not_computed" and not self.rackAlignmentId:
            raise ValueError("rackAlignmentId is required when rack alignment is available")
        if self.status == "not_computed" and self.captureToRackStatus != "not_computed":
            raise ValueError("not_computed rack alignment requires not_computed captureToRackStatus")
        all_heights = [*self.jcupHeightsM, *self.safetyPinHeightsM]
        if any(height > self.rackDimensionsM.height for height in all_heights):
            raise ValueError("rack heights must fit within rackDimensionsM.height")
        return self


class Observation2D(_TextModel):
    schemaVersion: Literal["rack_motion.observation2d.v1"] = "rack_motion.observation2d.v1"
    sessionId: str = Field(min_length=1)
    cameraId: str = Field(min_length=1)
    frameIndex: int = Field(ge=0)
    targetId: str = Field(min_length=1)
    spaceId: Literal["source_image_pixels"] = "source_image_pixels"
    imageSize: ImageSize
    x: float | None = None
    y: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    status: ObservationStatus
    statusReason: str | None = None
    timestampMs: float | None = None
    preprocessingTransformId: str | None = None

    @model_validator(mode="after")
    def _validate_coordinates_match_status(self) -> "Observation2D":
        has_point = self.x is not None and self.y is not None
        if self.status == "detected" and not has_point:
            raise ValueError("detected observations require x and y")
        if self.status != "detected" and has_point:
            raise ValueError("non-detected observations must not include x and y")
        if has_point:
            if self.x < 0 or self.x >= self.imageSize.width:
                raise ValueError("x must be within image bounds")
            if self.y < 0 or self.y >= self.imageSize.height:
                raise ValueError("y must be within image bounds")
        if self.status != "detected" and not self.statusReason:
            raise ValueError("statusReason is required for non-detected observations")
        return self


class ReconstructionTarget3D(_TextModel):
    schemaVersion: Literal["rack_motion.reconstruction_target3d.v1"] = (
        "rack_motion.reconstruction_target3d.v1"
    )
    frameIndex: int = Field(ge=0)
    targetId: str = Field(min_length=1)
    spaceId: Literal["capture_world", "rack_world"]
    unit: str = Field(min_length=1)
    x: float | None = None
    y: float | None = None
    z: float | None = None
    quality: float = Field(ge=0.0, le=1.0)
    mode: ReconstructionMode
    calibrationId: str | None = None
    usedCameraIds: list[str] = Field(default_factory=list)
    reprojectionErrorPx: float | None = Field(default=None, ge=0.0)
    status: ReconstructionStatus
    failureReason: str | None = None
    qualityMetrics: list[QualityMetric] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_reconstruction_state(self) -> "ReconstructionTarget3D":
        has_point = self.x is not None and self.y is not None and self.z is not None
        if self.status == "valid" and not has_point:
            raise ValueError("valid reconstruction targets require x, y, and z")
        if self.status == "invalid" and not self.failureReason:
            raise ValueError("invalid reconstruction targets require failureReason")
        if self.mode == "multi_camera":
            if len(set(self.usedCameraIds)) < 2:
                raise ValueError("multi_camera reconstruction requires at least two cameras")
            if not self.calibrationId:
                raise ValueError("multi_camera reconstruction requires calibrationId")
            if self.reprojectionErrorPx is None:
                raise ValueError("multi_camera reconstruction requires reprojectionErrorPx")
        if self.mode == "single_camera_estimate" and self.status == "valid":
            raise ValueError("single_camera_estimate must not be marked as valid")
        return self


class RackAnchor(_TextModel):
    anchorId: str = Field(min_length=1)
    label: str = Field(min_length=1)
    spaceId: Literal["rack_world"] = "rack_world"
    x: float
    y: float
    z: float
    quality: float = Field(ge=0.0, le=1.0)
    provenance: str = Field(min_length=1)


class SupportZone(_TextModel):
    zoneId: str = Field(min_length=1)
    label: str = Field(min_length=1)
    anchorIds: list[str] = Field(min_length=1)
    quality: float = Field(ge=0.0, le=1.0)


class BarbellEntity(_TextModel):
    entityId: str = Field(min_length=1)
    spaceId: Literal["rack_world"] = "rack_world"
    leftEndpoint: ReconstructionTarget3D
    rightEndpoint: ReconstructionTarget3D
    center: ReconstructionTarget3D | None = None
    quality: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_barbell_points(self) -> "BarbellEntity":
        for endpoint in (self.leftEndpoint, self.rightEndpoint):
            if endpoint.spaceId != "rack_world":
                raise ValueError("barbell endpoints must be in rack_world")
            if endpoint.status == "invalid":
                raise ValueError("barbell endpoints must not be invalid")
        if self.center is not None and self.center.spaceId != "rack_world":
            raise ValueError("barbell center must be in rack_world")
        return self


class RackMotionFrame(_TextModel):
    schemaVersion: Literal["rack_motion.frame.v1"] = "rack_motion.frame.v1"
    sessionId: str = Field(min_length=1)
    frameIndex: int = Field(ge=0)
    timestampMs: float | None = None
    rackAnchors: list[RackAnchor] = Field(default_factory=list)
    supportZones: list[SupportZone] = Field(default_factory=list)
    barbell: BarbellEntity | None = None
    personKeypoints: list[ReconstructionTarget3D] = Field(default_factory=list)
    qualityMetrics: list[QualityMetric] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_support_zone_anchors(self) -> "RackMotionFrame":
        anchor_ids = {anchor.anchorId for anchor in self.rackAnchors}
        for zone in self.supportZones:
            missing = [anchor_id for anchor_id in zone.anchorIds if anchor_id not in anchor_ids]
            if missing:
                raise ValueError("supportZones reference missing rack anchors")
        for target in self.personKeypoints:
            if target.spaceId != "rack_world":
                raise ValueError("personKeypoints must be in rack_world")
            if not target.targetId.startswith("person."):
                raise ValueError("personKeypoints targetId must use the person. namespace")
        return self


class RackMotionFramePage(_TextModel):
    schemaVersion: Literal["rack_motion.frame_page.v1"] = "rack_motion.frame_page.v1"
    page: dict[str, Any] = Field(default_factory=dict)
    frames: list[RackMotionFrame] = Field(default_factory=list)


class RackMotionViewerFixture(_TextModel):
    schemaVersion: Literal["rack_motion.viewer_fixture.v1"] = "rack_motion.viewer_fixture.v1"
    session: RackMotionSessionManifest
    rackAlignment: RackAlignmentSummary
    framePage: RackMotionFramePage
