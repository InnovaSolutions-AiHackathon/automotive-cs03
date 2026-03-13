from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.agent.claude_agent import run_agent

router = APIRouter()

class AskRequest(BaseModel):
    session_id: str
    message: str
    vehicle_id: Optional[str] = None
    image_base64: Optional[str] = None

@router.post("/ask")
async def ask_agent(req: AskRequest):
    return await run_agent(
        session_id=req.session_id, user_message=req.message,
        vehicle_id=req.vehicle_id, image_base64=req.image_base64
    )