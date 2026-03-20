"""
Insurance API — /api/insurance
"""
from fastapi import APIRouter
from app.services.insurance import get_vehicle_insurance, get_plans

router = APIRouter()


@router.get("/plans")
async def insurance_plans():
    return await get_plans()


@router.get("/{vehicle_code}")
async def vehicle_insurance(vehicle_code: str):
    return await get_vehicle_insurance(vehicle_code)
