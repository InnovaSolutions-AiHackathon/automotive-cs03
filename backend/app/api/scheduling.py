from fastapi import APIRouter
from pydantic import BaseModel
from app.services.scheduler import get_slots

router = APIRouter()

class SlotsRequest(BaseModel):
    service_type: str
    urgency: str = "normal"

@router.post("/slots")
async def available_slots(req: SlotsRequest):
    return await get_slots(req.service_type, req.urgency)