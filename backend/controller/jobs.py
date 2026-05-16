from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

from config import (
    ALLOWED_VIDEO_EXTENSIONS,
    MOCK_VIDEO_BODYWEIGHT_KG,
    MOCK_VIDEO_EXERCISE_TYPE,
    MOCK_VIDEO_EXTERNAL_LOAD_KG,
    MOCK_VIDEO_PATH,
    PRESET_ESTIMATION_DIR,
    UPLOAD_DIR,
)
from schema.job import JobCreateResponse, JobStatusResponse
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])
EMPTY_FORM_SCHEMA = {"example": ""}


@router.post(
    "",
    response_model=JobCreateResponse,
    summary="Create Analysis Job",
    description=(
        "Queues a background job that runs frame extraction, pose inference, and the data-analysis "
        "pipeline. Poll `/jobs/{job_id}` for status and read `/jobs/{job_id}/result` for the final "
        "analysis payload."
    ),
)
async def create_job(
    response: Response,
    video: UploadFile | None = File(default=None),
    fps: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    samplingFps: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    exerciseType: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    bodyweightKg: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    externalLoadKg: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    barPlacementMode: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    modelAssetPath: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    modelVariant: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    delegate: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    presetEstimationId: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
) -> JobCreateResponse:
    response.headers["Deprecation"] = "true"
    response.headers["X-Deprecated-By"] = "/synthesis/jobs"
    resolved_preset_id = _resolve_optional_text(presetEstimationId)

    if resolved_preset_id is not None:
        preset_path = PRESET_ESTIMATION_DIR / f"{resolved_preset_id}.json"
        if not preset_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Preset estimation not found: {resolved_preset_id}",
            )
        return await job_manager.create_job(
            filename=resolved_preset_id,
            source_path=str(preset_path),
            requested_sampling_fps=None,
            exercise_type=exerciseType,
            bodyweight_kg=None,
            external_load_kg=None,
            bar_placement_mode=None,
            model_asset_path=None,
            model_variant=None,
            delegate=None,
            preset_estimation_id=resolved_preset_id,
        )

    source_path = str(MOCK_VIDEO_PATH)
    source_name = MOCK_VIDEO_PATH.name
    uses_mock_video = True

    if video is not None and video.filename:
        source_name = video.filename
        source_path = await _persist_upload(video)
        uses_mock_video = False

    if uses_mock_video:
        exerciseType = _resolve_optional_text(exerciseType) or MOCK_VIDEO_EXERCISE_TYPE
        bodyweightKg = bodyweightKg if bodyweightKg is not None else MOCK_VIDEO_BODYWEIGHT_KG
        externalLoadKg = (
            externalLoadKg if externalLoadKg is not None else MOCK_VIDEO_EXTERNAL_LOAD_KG
        )

    return await job_manager.create_job(
        filename=source_name,
        source_path=source_path,
        requested_sampling_fps=samplingFps if samplingFps is not None else fps,
        exercise_type=exerciseType,
        bodyweight_kg=bodyweightKg,
        external_load_kg=externalLoadKg,
        bar_placement_mode=barPlacementMode,
        model_asset_path=modelAssetPath,
        model_variant=modelVariant,
        delegate=delegate,
        preset_estimation_id=None,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    return job_manager.get_status(job_id)


@router.get("/{job_id}/stream")
async def stream_job_status(job_id: str) -> StreamingResponse:
    return StreamingResponse(
        job_manager.stream_status(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity",
        },
    )


async def _persist_upload(video: UploadFile) -> str:
    filename = Path(video.filename or "upload.mp4").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video file extension.")

    destination = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    content = await video.read()
    destination.write_bytes(content)
    return str(destination)


def _resolve_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
