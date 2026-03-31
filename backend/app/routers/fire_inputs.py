"""FIRE inputs API routes."""
from fastapi import APIRouter, Depends
from app.core.models import FireInputs
from app.dependencies import CurrentUser, get_current_user
from app.services import fire_inputs_svc

router = APIRouter(tags=["fire-inputs"])

@router.get("/fire-inputs")
async def get_fire_inputs(user: CurrentUser = Depends(get_current_user)) -> dict:
    result = fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if result is None:
        return {"data": None, "message": "No FIRE settings configured yet"}
    return {"data": result}

@router.put("/fire-inputs")
async def update_fire_inputs(data: FireInputs, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = fire_inputs_svc.save_fire_inputs(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "FIRE settings saved"}
