from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SynthesisSyncMode = Literal["timestamp"]
SynthesisLandmarkSet = Literal["mediapipe_pose_33"]
SynthesisCoordinateSystem = Literal["panoptic_world_cm"]


class SynthesisSourceBinding(BaseModel):
    sourceJobId: str = Field(min_length=1)
    cameraId: str = Field(min_length=1)

    @field_validator("sourceJobId", "cameraId")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class SynthesisPairSources(BaseModel):
    A: SynthesisSourceBinding
    B: SynthesisSourceBinding

    @model_validator(mode="after")
    def _validate_distinct_sources(self) -> "SynthesisPairSources":
        if self.A.sourceJobId == self.B.sourceJobId:
            raise ValueError("sources.A.sourceJobId and sources.B.sourceJobId must differ")
        if self.A.cameraId == self.B.cameraId:
            raise ValueError("sources.A.cameraId and sources.B.cameraId must differ")
        return self


class SynthesisSyncConfig(BaseModel):
    mode: SynthesisSyncMode = "timestamp"
    timestampDomain: str = "media_time_ms"
    maxDeltaMs: float | None = None
    fallback: str | None = "frameIndex_for_gt_aligned_dataset_only"

    @field_validator("timestampDomain", "fallback")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("maxDeltaMs")
    @classmethod
    def _validate_max_delta(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("maxDeltaMs must be > 0")
        return value


class SynthesisThresholds(BaseModel):
    minVisibility: float = 0.5
    minPresence: float = 0.5
    maxReprojectionErrorPx: float = 8.0

    @field_validator("minVisibility", "minPresence")
    @classmethod
    def _validate_probability(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("threshold must be between 0 and 1")
        return value

    @field_validator("maxReprojectionErrorPx")
    @classmethod
    def _validate_reprojection_error(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("maxReprojectionErrorPx must be > 0")
        return value


class SynthesisPairManifest(BaseModel):
    schemaVersion: Literal["synthesis_pair_manifest.v1"] = "synthesis_pair_manifest.v1"
    sources: SynthesisPairSources
    calibrationRef: str = Field(min_length=1)
    sync: SynthesisSyncConfig = Field(default_factory=SynthesisSyncConfig)
    landmarkSet: SynthesisLandmarkSet = "mediapipe_pose_33"
    outputCoordinateSystem: SynthesisCoordinateSystem = "panoptic_world_cm"

    @field_validator("calibrationRef")
    @classmethod
    def _strip_calibration_ref(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("calibrationRef must not be empty")
        return stripped


class StreamingVideoSource(BaseModel):
    videoPath: str = Field(min_length=1)
    cameraId: str = Field(min_length=1)

    @field_validator("videoPath", "cameraId")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class StreamingSource(BaseModel):
    """Video source or preset estimation source for streaming synthesis."""
    videoPath: str | None = None
    presetEstimationId: str | None = None
    cameraId: str = Field(min_length=1)

    @field_validator("videoPath", "presetEstimationId")
    @classmethod
    def _strip_optional_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("cameraId")
    @classmethod
    def _strip_camera_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("cameraId must not be empty")
        return stripped

    @model_validator(mode="after")
    def _validate_exactly_one_source(self) -> "StreamingSource":
        has_video = self.videoPath is not None
        has_preset = self.presetEstimationId is not None
        if not (has_video ^ has_preset):
            raise ValueError("Exactly one of videoPath or presetEstimationId must be provided")
        return self


class StreamingPairSources(BaseModel):
    A: StreamingSource
    B: StreamingSource

    @model_validator(mode="after")
    def _validate_distinct_cameras(self) -> "StreamingPairSources":
        if self.A.cameraId == self.B.cameraId:
            raise ValueError("sources.A.cameraId and sources.B.cameraId must differ")
        return self


class StreamingPairManifest(BaseModel):
    schemaVersion: Literal["streaming_pair_manifest.v1"] = "streaming_pair_manifest.v1"
    sources: StreamingPairSources
    calibrationRef: str = Field(min_length=1)
    sync: SynthesisSyncConfig = Field(default_factory=SynthesisSyncConfig)
    landmarkSet: SynthesisLandmarkSet = "mediapipe_pose_33"
    outputCoordinateSystem: SynthesisCoordinateSystem = "panoptic_world_cm"
    thresholds: SynthesisThresholds = Field(default_factory=SynthesisThresholds)

    @field_validator("calibrationRef")
    @classmethod
    def _strip_calibration_ref(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("calibrationRef must not be empty")
        return stripped


class SynthesisJobOptions(BaseModel):
    runEvaluation: bool = False
    gtRef: str | None = None

    @field_validator("gtRef")
    @classmethod
    def _strip_gt_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SynthesisJobCreateRequest(BaseModel):
    pairManifest: SynthesisPairManifest | None = None
    streamingManifest: StreamingPairManifest | None = None
    options: SynthesisJobOptions = Field(default_factory=SynthesisJobOptions)

    @model_validator(mode="after")
    def _validate_exactly_one_manifest(self) -> "SynthesisJobCreateRequest":
        has_artifact = self.pairManifest is not None
        has_streaming = self.streamingManifest is not None
        if not has_artifact and not has_streaming:
            raise ValueError("Exactly one of pairManifest or streamingManifest must be provided")
        if has_artifact and has_streaming:
            raise ValueError("Exactly one of pairManifest or streamingManifest must be provided")
        return self


class SynthesisInput(BaseModel):
    sourceJobIdA: str
    sourceJobIdB: str
    cameraIdA: str
    cameraIdB: str
    calibrationRef: str
    sync: SynthesisSyncConfig = Field(default_factory=SynthesisSyncConfig)
    landmarkSet: SynthesisLandmarkSet = "mediapipe_pose_33"
    outputCoordinateSystem: SynthesisCoordinateSystem = "panoptic_world_cm"
    thresholds: SynthesisThresholds = Field(default_factory=SynthesisThresholds)

    @classmethod
    def from_manifest(
        cls,
        manifest: SynthesisPairManifest,
        *,
        thresholds: SynthesisThresholds | None = None,
    ) -> "SynthesisInput":
        return cls(
            sourceJobIdA=manifest.sources.A.sourceJobId,
            sourceJobIdB=manifest.sources.B.sourceJobId,
            cameraIdA=manifest.sources.A.cameraId,
            cameraIdB=manifest.sources.B.cameraId,
            calibrationRef=manifest.calibrationRef,
            sync=manifest.sync,
            landmarkSet=manifest.landmarkSet,
            outputCoordinateSystem=manifest.outputCoordinateSystem,
            thresholds=thresholds or SynthesisThresholds(),
        )


class SynthesisArtifactRef(BaseModel):
    path: str
    schemaVersion: str
    summary: dict[str, Any] = Field(default_factory=dict)


class SynthesisPageResponse(BaseModel):
    schemaVersion: Literal["skeleton3d.v1"] = "skeleton3d.v1"
    page: dict[str, Any] = Field(default_factory=dict)
    timeline: dict[str, Any] = Field(default_factory=dict)
    synthesisInfo: dict[str, Any] = Field(default_factory=dict)
    qualitySummary: dict[str, Any] = Field(default_factory=dict)
    frames: list[dict[str, Any]] = Field(default_factory=list)
