from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from schema.rack_motion import RackMotionViewerFixture
from service.rack_motion_repository import RackMotionArtifactRepository
from service.skeleton_artifact_repository import (
    SkeletonArtifactNotFoundError,
    SkeletonArtifactNotReadyError,
    SkeletonArtifactRepository,
)


rack_motion_repository = RackMotionArtifactRepository()
skeleton_artifact_repository = SkeletonArtifactRepository()

router = APIRouter(prefix="/rack-motion", tags=["rack-motion"])


@router.get("/fixtures/stage1", response_model=RackMotionViewerFixture)
def get_stage1_rack_motion_fixture(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=600),
) -> RackMotionViewerFixture:
    return RackMotionViewerFixture.model_validate(
        rack_motion_repository.get_stage1_fixture(offset=offset, limit=limit)
    )


@router.get("/from-synthesis/{synthesis_job_id}/stage1", response_model=RackMotionViewerFixture)
def get_stage1_fixture_from_synthesis(
    synthesis_job_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=600),
) -> RackMotionViewerFixture:
    try:
        skeleton3d_payload = skeleton_artifact_repository.read_skeleton3d(synthesis_job_id)
    except SkeletonArtifactNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"skeleton3d artifact not found for synthesis job {synthesis_job_id}",
        )
    except SkeletonArtifactNotReadyError:
        raise HTTPException(
            status_code=409,
            detail=f"skeleton3d artifact not ready for synthesis job {synthesis_job_id}",
        )
    return RackMotionViewerFixture.model_validate(
        rack_motion_repository.get_stage1_fixture_from_skeleton3d(
            skeleton3d_payload,
            offset=offset,
            limit=limit,
        )
    )
