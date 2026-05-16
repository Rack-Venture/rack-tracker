from typing import Any

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    stage: str
    currentStep: int
    totalSteps: int
    ratio: float
    stageDurationsMs: dict[str, float] = Field(default_factory=dict)
    stageDetails: dict[str, Any] = Field(default_factory=dict)
    processedFrames: int | None = None
    totalFrames: int | None = None


class JobError(BaseModel):
    code: str
    message: str


class JobCreateResponse(BaseModel):
    jobId: str
    status: str
    videoPath: str | None = None


class JobStatusResponse(BaseModel):
    jobId: str
    status: str
    progress: JobProgress | None = None
    error: JobError | None = None
