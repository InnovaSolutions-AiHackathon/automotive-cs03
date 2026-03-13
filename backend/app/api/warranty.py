from fastapi import APIRouter
from pydantic import BaseModel
from app.services.warranty_engine import check_warranty

router = APIRouter()

class WarrantyRequest(BaseModel):
    vehicle_id: str
    repair_type: str

@router.post("/check")
async def warranty_check(req: WarrantyRequest):
    return await check_warranty(req.vehicle_id, req.repair_type)