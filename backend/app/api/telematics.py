from fastapi import APIRouter
from app.services.telematics import get_vehicle_data, decode_dtc

router = APIRouter()

@router.get("/{vehicle_id}")
async def vehicle_telematics(vehicle_id: str):
    return await get_vehicle_data(vehicle_id)

@router.post("/decode")
async def decode_codes(body: dict):
    return await decode_dtc(body.get("codes", []))