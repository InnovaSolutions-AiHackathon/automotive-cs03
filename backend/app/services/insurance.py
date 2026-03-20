"""
Insurance Service — fetches vehicle insurance and available plans.
"""
from __future__ import annotations
import logging
from datetime import date
from typing import Any

from app.db.database import InsuranceSession
from app.db.schemas.insurance import InsurancePlan, VehicleInsurance

logger = logging.getLogger(__name__)


async def get_vehicle_insurance(vehicle_code: str) -> dict[str, Any]:
    db = InsuranceSession()
    try:
        policy = (
            db.query(VehicleInsurance)
            .filter_by(vehicle_code=vehicle_code, status="active")
            .first()
        )
        if not policy:
            return {"found": False, "message": "No active insurance found for this vehicle"}

        days_left = (policy.expires_on - date.today()).days
        return {
            "found": True,
            "vehicle_code": vehicle_code,
            "provider":   policy.provider,
            "policy_no":  policy.policy_no,
            "plan_name":  policy.plan_name,
            "expires_on": str(policy.expires_on),
            "premium":    float(policy.premium) if policy.premium else None,
            "status":     policy.status,
            "days_left":  days_left,
        }
    except Exception as exc:
        logger.error(f"Insurance fetch error for {vehicle_code}: {exc}")
        return {"found": False, "message": "Error fetching insurance"}
    finally:
        db.close()


async def get_plans() -> dict[str, Any]:
    db = InsuranceSession()
    try:
        plans = db.query(InsurancePlan).filter_by(is_active=True).all()
        return {
            "plans": [
                {
                    "id":       p.id,
                    "name":     p.name,
                    "price":    float(p.price),
                    "duration": p.duration,
                    "features": p.features or [],
                }
                for p in plans
            ]
        }
    except Exception as exc:
        logger.error(f"Plans fetch error: {exc}")
        return {"plans": []}
    finally:
        db.close()
