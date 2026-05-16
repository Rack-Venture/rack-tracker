from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from config import ALLOWED_VIDEO_EXTENSIONS, UPLOAD_DIR
from schema.job import JobCreateResponse, JobStatusResponse
from schema.synthesis import SynthesisJobCreateRequest, SynthesisPageResponse
from service.job_manager import job_manager
from service.skeleton_artifact_repository import SkeletonArtifactRepository
from service.synthesis_job_manager import SynthesisJobManager


artifact_repository = SkeletonArtifactRepository(
    source_loader=job_manager.load_skeleton_artifact,
)
synthesis_job_manager = SynthesisJobManager(
    artifact_repository=artifact_repository,
)

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


@router.post("/upload")
async def upload_synthesis_video(video: UploadFile = File(...)) -> dict:
    """Upload a video file and return its server-side path for use in streaming synthesis jobs."""
    filename = Path(video.filename or "upload.mp4").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video file extension.")
    destination = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    content = await video.read()
    destination.write_bytes(content)
    return {"videoPath": str(destination)}


@router.post("/jobs", response_model=JobCreateResponse)
async def create_synthesis_job(request: SynthesisJobCreateRequest) -> JobCreateResponse:
    return await synthesis_job_manager.create_job(request)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_synthesis_job_status(job_id: str) -> JobStatusResponse:
    return synthesis_job_manager.get_status(job_id)


@router.get("/jobs/{job_id}/result")
def get_synthesis_job_result(job_id: str) -> dict:
    return synthesis_job_manager.get_result(job_id)


@router.get("/jobs/{job_id}/skeleton3d/all", response_model=SynthesisPageResponse)
def get_synthesis_skeleton3d_all(job_id: str) -> SynthesisPageResponse:
    return SynthesisPageResponse.model_validate(
        synthesis_job_manager.get_skeleton3d_all(job_id)
    )


@router.get("/jobs/{job_id}/skeleton3d", response_model=SynthesisPageResponse)
def get_synthesis_skeleton3d_page(
    job_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=600),
) -> SynthesisPageResponse:
    return SynthesisPageResponse.model_validate(
        synthesis_job_manager.get_skeleton3d_page(job_id, offset=offset, limit=limit)
    )


@router.get("/jobs/{job_id}/skeleton_a")
def get_synthesis_skeleton_a_page(
    job_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=300, ge=1, le=600),
) -> dict:
    return synthesis_job_manager.get_skeleton_a_page(job_id, offset=offset, limit=limit)


@router.get("/jobs/{job_id}/skeleton_b")
def get_synthesis_skeleton_b_page(
    job_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=300, ge=1, le=600),
) -> dict:
    return synthesis_job_manager.get_skeleton_b_page(job_id, offset=offset, limit=limit)


@router.get("/jobs/{job_id}/evaluation")
def get_synthesis_evaluation(job_id: str) -> dict:
    return synthesis_job_manager.get_evaluation(job_id)


@router.get("/jobs/{job_id}/debug")
def get_synthesis_debug_report(job_id: str) -> dict:
    return synthesis_job_manager.get_debug_report(job_id)
