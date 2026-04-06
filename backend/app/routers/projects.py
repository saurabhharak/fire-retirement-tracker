"""Projects API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import ProjectCreate, ProjectUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import projects_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["projects"])


@router.get("/projects")
@limiter.limit("60/minute")
async def list_projects(
    request: Request,
    status: str = Query(None),
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = projects_svc.load_projects(
        user.id, user.access_token, status=status, active_only=active,
    )
    return {"data": entries}


@router.post("/projects")
@limiter.limit("30/minute")
async def create_project(
    request: Request,
    data: ProjectCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = projects_svc.save_project(user.id, data.model_dump(), user.access_token)
    log_audit(user.id, "create_project", {"name": data.name}, user.access_token)
    return {"data": result, "message": "Project created"}


@router.patch("/projects/{project_id}")
@limiter.limit("30/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    data: ProjectUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = projects_svc.update_project(
        str(project_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_project", {"project_id": str(project_id)}, user.access_token)
    return {"data": result, "message": "Project updated"}


@router.delete("/projects/{project_id}")
@limiter.limit("10/minute")
async def deactivate_project(
    request: Request,
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    projects_svc.deactivate_project(str(project_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_project", {"project_id": str(project_id)}, user.access_token)
    return {"message": "Project deactivated"}
