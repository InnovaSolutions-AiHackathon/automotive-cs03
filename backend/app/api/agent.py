from app.orch.orchestrator import run_orchestrator
from app.api.vehicles import list_vehicles
from app.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.agent.askAI import run_agent

router = APIRouter()

class AskRequest(BaseModel):
    session_id: str
    message: str
    vehicle_id: Optional[str] = None
    image_base64: Optional[str] = None
    user_id: Optional[str] = None

# @router.post("/ask")
# async def ask_agent(req: AskRequest):
#     return await run_agent(
#         session_id=req.session_id, user_message=req.message,
#         vehicle_id=req.vehicle_id, image_base64=req.image_base64
#     )


@router.post("/ask")
async def query_handler(payload: AskRequest, db: Session = Depends(get_db)):
    user_message = payload.message

    if not user_message:
        return {"error": "Message cannot be empty."}
    
    context = {
        "session_id": payload.session_id,
        "vehicle_id": payload.vehicle_id,
        "image_base64": payload.image_base64,
        "user_id": payload.user_id
    }
    result = await run_orchestrator(user_message, context)
    print(f"Orchestrator result: {result}")
    return result
