from datetime import datetime, timedelta
import random

TECHNICIANS = {
    "T01_Kumar":  ["engine","transmission","drivetrain"],
    "T02_Patel":  ["electrical","diagnostics"],
    "T03_Ahmed":  ["brakes","suspension"],
    "T04_Ramos":  ["ac","interior","general"],
}

async def get_slots(service_type: str, urgency: str = "normal") -> dict:
    offset = {"critical": 1, "high": 2, "normal": 3}.get(urgency, 3)
    qualified = [t for t,s in TECHNICIANS.items()
                 if service_type in s or "general" in s]
    slots, today = [], datetime.now()
    for d in range(offset, offset+7):
        day = today + timedelta(days=d)
        if day.weekday() < 5:
            for hr in [8,10,13,15]:
                slots.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "time": f"{hr:02d}:00",
                    "technician": random.choice(qualified) if qualified else "TBA",
                    "duration_hours": 2,
                    "bay": random.randint(1,4)
                })
    return {"slots": slots[:4], "urgency": urgency, "service_type": service_type}