"""
Seed script — populates all agent schemas with realistic dummy data.
Run: python -m scripts.seed_data  (from /backend directory)
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import bcrypt
from sqlalchemy.orm import Session

from app.db.database import (
    AuthSession, VehicleSession, WarrantySession,
    SchedulerSession, TelematicsSession, InsuranceSession,
    create_all_schemas,
)
from app.db.schemas.auth      import User
from app.db.schemas.vehicle   import Customer, Vehicle, FaultCode
from app.db.schemas.warranty  import WarrantyRecord, WarrantyRule
from app.db.schemas.scheduler import Technician, ServiceAppointment
from app.db.schemas.telematics import DTCCode, TelematicsSnapshot
from app.db.schemas.insurance  import InsurancePlan, VehicleInsurance


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _clear(db: Session, *models) -> None:
    """Delete in the order given (caller must pass child tables first)."""
    for m in models:
        db.query(m).delete()
    db.commit()


# ===========================================================================
# AUTH — cs03_auth
# ===========================================================================
def seed_auth() -> None:
    db = AuthSession()
    try:
        _clear(db, User)
        users = [
            User(first_name="Amresh",  last_name="Kumar",   email="amresh@cs03.com",  password=_hash("Admin@123"),  role="admin",      mobile="9800000001"),
            User(first_name="Priya",   last_name="Sharma",  email="priya@cs03.com",   password=_hash("Agent@123"),  role="agent",      mobile="9800000002"),
            User(first_name="Rahul",   last_name="Mehta",   email="rahul@cs03.com",   password=_hash("Agent@123"),  role="agent",      mobile="9800000003"),
            User(first_name="Sonia",   last_name="Verma",   email="sonia@cs03.com",   password=_hash("Super@123"),  role="supervisor", mobile="9800000004"),
        ]
        db.add_all(users)
        db.commit()
        print(f"[auth] {len(users)} users seeded")
    finally:
        db.close()


# ===========================================================================
# VEHICLE — cs03_vehicle
# ===========================================================================
def seed_vehicles() -> None:
    db = VehicleSession()
    try:
        _clear(db, FaultCode, Vehicle, Customer)

        customers = [
            Customer(name="Amresh Kumar",    email="amresh.kumar@gmail.com",  phone="9811111111"),
            Customer(name="Priya Singh",     email="priya.singh@gmail.com",   phone="9822222222"),
            Customer(name="Rahul Verma",     email="rahul.verma@gmail.com",   phone="9833333333"),
            Customer(name="Sonia Mehta",     email="sonia.mehta@gmail.com",   phone="9844444444"),
            Customer(name="Vikram Joshi",    email="vikram.joshi@gmail.com",  phone="9855555555"),
        ]
        db.add_all(customers)
        db.flush()  # assign IDs

        c = {cust.name.split()[0]: cust for cust in customers}

        vehicles = [
            # VH001 — normal, healthy vehicle
            Vehicle(
                vehicle_code="VH001", vin="1HGBH41JXMN109186",
                make="Honda", model="Accord", year=2022,
                odometer=28_500, purchase_date=date(2022, 3, 15),
                customer_id=c["Amresh"].id,
                fuel_level=65, battery_voltage=12.4,
                engine_temp=92, oil_life=45,
            ),
            # VH002 — overheating Royal Enfield (engine_temp=108 is high for a bike)
            Vehicle(
                vehicle_code="VH002", vin="1HGBH41JXMN109301",
                make="Royal Enfield", model="Meteor 650", year=2022,
                odometer=15_200, purchase_date=date(2022, 7, 20),
                customer_id=c["Amresh"].id,
                fuel_level=30, battery_voltage=11.8,
                engine_temp=108, oil_life=12,
            ),
            # VH003 — low fuel + battery warning
            Vehicle(
                vehicle_code="VH003", vin="2T1BURHE0JC041234",
                make="Toyota", model="Corolla", year=2021,
                odometer=52_000, purchase_date=date(2021, 5, 10),
                customer_id=c["Priya"].id,
                fuel_level=8, battery_voltage=11.2,
                engine_temp=88, oil_life=72,
            ),
            # VH004 — high mileage, nearly due for service
            Vehicle(
                vehicle_code="VH004", vin="WVWZZZ1KZAW045678",
                make="Volkswagen", model="Polo", year=2020,
                odometer=88_400, purchase_date=date(2020, 1, 25),
                customer_id=c["Rahul"].id,
                fuel_level=55, battery_voltage=12.6,
                engine_temp=95, oil_life=5,
            ),
            # VH005 — multiple active fault codes
            Vehicle(
                vehicle_code="VH005", vin="5YJ3E1EA4KF345678",
                make="Tesla", model="Model 3", year=2023,
                odometer=12_000, purchase_date=date(2023, 6, 1),
                customer_id=c["Sonia"].id,
                fuel_level=78, battery_voltage=12.9,
                engine_temp=85, oil_life=90,
            ),
            # VH006 — brand new, pristine
            Vehicle(
                vehicle_code="VH006", vin="MB1GG25E48E067890",
                make="Mercedes-Benz", model="C-Class", year=2024,
                odometer=3_200, purchase_date=date(2024, 1, 10),
                customer_id=c["Sonia"].id,
                fuel_level=92, battery_voltage=12.8,
                engine_temp=89, oil_life=95,
            ),
            # VH007 — old diesel, critical condition
            Vehicle(
                vehicle_code="VH007", vin="SAJAC2240KCP56789",
                make="Jaguar", model="XE", year=2019,
                odometer=120_000, purchase_date=date(2019, 11, 5),
                customer_id=c["Vikram"].id,
                fuel_level=22, battery_voltage=11.5,
                engine_temp=102, oil_life=3,
            ),
            # VH008 — SUV, in for scheduled service next week
            Vehicle(
                vehicle_code="VH008", vin="KL8CD6SA7AC789012",
                make="Mahindra", model="XUV700", year=2023,
                odometer=34_700, purchase_date=date(2023, 2, 28),
                customer_id=c["Vikram"].id,
                fuel_level=48, battery_voltage=12.5,
                engine_temp=91, oil_life=35,
            ),
        ]
        db.add_all(vehicles)
        db.flush()

        vmap = {v.vehicle_code: v for v in vehicles}

        # Active fault codes
        faults = [
            # VH002 — Royal Enfield overheating + lean mixture
            FaultCode(vehicle_id=vmap["VH002"].id, dtc_code="P0217", resolved=False),  # engine overtemp
            FaultCode(vehicle_id=vmap["VH002"].id, dtc_code="P0171", resolved=False),  # lean bank 1
            # VH003 — Toyota low battery
            FaultCode(vehicle_id=vmap["VH003"].id, dtc_code="P0562", resolved=False),  # low voltage
            # VH004 — VW oil life critical
            FaultCode(vehicle_id=vmap["VH004"].id, dtc_code="P0520", resolved=False),  # oil pressure sensor
            # VH005 — Tesla multiple codes
            FaultCode(vehicle_id=vmap["VH005"].id, dtc_code="P0300", resolved=False),  # misfire
            FaultCode(vehicle_id=vmap["VH005"].id, dtc_code="C0035", resolved=False),  # wheel speed
            FaultCode(vehicle_id=vmap["VH005"].id, dtc_code="B0001", resolved=False),  # airbag circuit
            # VH007 — Jaguar critical
            FaultCode(vehicle_id=vmap["VH007"].id, dtc_code="P0420", resolved=False),  # catalyst
            FaultCode(vehicle_id=vmap["VH007"].id, dtc_code="P0217", resolved=False),  # overtemp
        ]
        db.add_all(faults)
        db.commit()
        print(f"[vehicle] {len(vehicles)} vehicles, {len(faults)} fault codes seeded")
    finally:
        db.close()


# ===========================================================================
# WARRANTY — cs03_warranty
# ===========================================================================
def seed_warranty() -> None:
    db = WarrantySession()
    try:
        _clear(db, WarrantyRecord, WarrantyRule)

        rules = [
            WarrantyRule(
                coverage_type="Bumper to Bumper",
                covered_types=["engine", "transmission", "electrical", "suspension", "brakes", "ac"],
                exclusions=["tires", "wipers", "consumables"],
                notes="Full vehicle coverage for 3 years / 100,000 km"
            ),
            WarrantyRule(
                coverage_type="Powertrain",
                covered_types=["engine", "transmission", "drivetrain"],
                exclusions=["electrical", "body", "interior"],
                notes="Powertrain only — 5 years / 150,000 km"
            ),
            WarrantyRule(
                coverage_type="Extended",
                covered_types=["engine", "transmission", "electrical", "suspension", "brakes", "ac", "infotainment"],
                exclusions=["tires", "glass"],
                notes="Comprehensive extended warranty"
            ),
            WarrantyRule(
                coverage_type="Basic",
                covered_types=["engine", "transmission"],
                exclusions=["electrical", "body", "suspension", "brakes"],
                notes="Basic manufacturer warranty"
            ),
        ]
        db.add_all(rules)

        today = date.today()
        records = [
            WarrantyRecord(vehicle_code="VH001", coverage_type="Bumper to Bumper", start_date=date(2022, 3, 15), end_date=today + timedelta(days=365), mileage_limit=100_000, is_extended=False),
            WarrantyRecord(vehicle_code="VH001", coverage_type="Powertrain",       start_date=date(2022, 3, 15), end_date=today + timedelta(days=730), mileage_limit=150_000, is_extended=False),
            WarrantyRecord(vehicle_code="VH002", coverage_type="Basic",            start_date=date(2022, 7, 20), end_date=today + timedelta(days=180), mileage_limit=50_000, is_extended=False),
            WarrantyRecord(vehicle_code="VH003", coverage_type="Powertrain",       start_date=date(2021, 5, 10), end_date=today - timedelta(days=30),  mileage_limit=100_000, is_extended=False),  # EXPIRED
            WarrantyRecord(vehicle_code="VH004", coverage_type="Basic",            start_date=date(2020, 1, 25), end_date=today - timedelta(days=180), mileage_limit=80_000,  is_extended=False),  # EXPIRED
            WarrantyRecord(vehicle_code="VH005", coverage_type="Bumper to Bumper", start_date=date(2023, 6, 1),  end_date=today + timedelta(days=500), mileage_limit=100_000, is_extended=False),
            WarrantyRecord(vehicle_code="VH005", coverage_type="Extended",         start_date=date(2023, 6, 1),  end_date=today + timedelta(days=900), mileage_limit=200_000, is_extended=True),
            WarrantyRecord(vehicle_code="VH006", coverage_type="Bumper to Bumper", start_date=date(2024, 1, 10), end_date=today + timedelta(days=700), mileage_limit=100_000, is_extended=False),
            WarrantyRecord(vehicle_code="VH007", coverage_type="Basic",            start_date=date(2019, 11, 5), end_date=today - timedelta(days=365), mileage_limit=80_000,  is_extended=False),  # EXPIRED
            WarrantyRecord(vehicle_code="VH008", coverage_type="Bumper to Bumper", start_date=date(2023, 2, 28), end_date=today + timedelta(days=400), mileage_limit=100_000, is_extended=False),
        ]
        db.add_all(records)
        db.commit()
        print(f"[warranty] {len(rules)} rules, {len(records)} records seeded")
    finally:
        db.close()


# ===========================================================================
# SCHEDULER — cs03_scheduler
# ===========================================================================
def seed_scheduler() -> None:
    db = SchedulerSession()
    try:
        _clear(db, ServiceAppointment, Technician)

        techs = [
            Technician(tech_code="TECH01", name="Arjun Nair",    specialties=["engine", "transmission", "diagnostics"], is_active=True),
            Technician(tech_code="TECH02", name="Deepak Rao",    specialties=["electrical", "brakes", "suspension"],    is_active=True),
            Technician(tech_code="TECH03", name="Sunita Bose",   specialties=["engine", "oil", "general"],              is_active=True),
            Technician(tech_code="TECH04", name="Manish Gupta",  specialties=["body", "paint", "ac"],                   is_active=True),
            Technician(tech_code="TECH05", name="Kavya Pillai",  specialties=["ev", "battery", "electrical"],           is_active=True),
        ]
        db.add_all(techs)

        today = date.today()
        appts = [
            # Past completed
            ServiceAppointment(vehicle_code="VH001", service_type="Oil Change",             scheduled_date=today - timedelta(days=90),  scheduled_time="10:00", technician_code="TECH03", bay=1, duration_hours=1, status="completed",    urgency="normal",   warranty_covered=True),
            ServiceAppointment(vehicle_code="VH001", service_type="Brake Inspection",       scheduled_date=today - timedelta(days=45),  scheduled_time="14:00", technician_code="TECH02", bay=2, duration_hours=2, status="completed",    urgency="normal",   warranty_covered=True),
            ServiceAppointment(vehicle_code="VH002", service_type="Engine Overheating Fix", scheduled_date=today - timedelta(days=10),  scheduled_time="09:00", technician_code="TECH01", bay=1, duration_hours=3, status="completed",    urgency="high",     warranty_covered=False),
            ServiceAppointment(vehicle_code="VH003", service_type="Battery Replacement",    scheduled_date=today - timedelta(days=5),   scheduled_time="11:00", technician_code="TECH02", bay=3, duration_hours=2, status="completed",    urgency="high",     warranty_covered=False),
            # Upcoming confirmed
            ServiceAppointment(vehicle_code="VH002", service_type="Cooling System Flush",   scheduled_date=today + timedelta(days=3),   scheduled_time="09:30", technician_code="TECH01", bay=1, duration_hours=2, status="confirmed",    urgency="critical", warranty_covered=False, notes="Engine temp spiking to 108°C, suspected thermostat failure"),
            ServiceAppointment(vehicle_code="VH004", service_type="Full Service + Oil",     scheduled_date=today + timedelta(days=5),   scheduled_time="08:00", technician_code="TECH03", bay=2, duration_hours=3, status="confirmed",    urgency="high",     warranty_covered=False, notes="Oil life critically low at 5%"),
            ServiceAppointment(vehicle_code="VH007", service_type="Engine Diagnostics",     scheduled_date=today + timedelta(days=2),   scheduled_time="10:00", technician_code="TECH01", bay=1, duration_hours=4, status="confirmed",    urgency="critical", warranty_covered=False, notes="Multiple DTC codes, overheating"),
            ServiceAppointment(vehicle_code="VH008", service_type="Scheduled Maintenance",  scheduled_date=today + timedelta(days=7),   scheduled_time="09:00", technician_code="TECH03", bay=3, duration_hours=2, status="pending",      urgency="normal",   warranty_covered=True),
            # Tesla — EV specialist
            ServiceAppointment(vehicle_code="VH005", service_type="Software Update + Diag", scheduled_date=today + timedelta(days=1),   scheduled_time="13:00", technician_code="TECH05", bay=4, duration_hours=2, status="confirmed",    urgency="high",     warranty_covered=True,  notes="3 active DTCs including airbag circuit open"),
            ServiceAppointment(vehicle_code="VH006", service_type="First Service Check",    scheduled_date=today + timedelta(days=14),  scheduled_time="10:00", technician_code="TECH03", bay=2, duration_hours=1, status="pending",      urgency="normal",   warranty_covered=True),
        ]
        db.add_all(appts)
        db.commit()
        print(f"[scheduler] {len(techs)} technicians, {len(appts)} appointments seeded")
    finally:
        db.close()


# ===========================================================================
# TELEMATICS — cs03_telematics
# ===========================================================================
def seed_telematics() -> None:
    db = TelematicsSession()
    try:
        _clear(db, TelematicsSnapshot, DTCCode)

        dtc_codes = [
            DTCCode(code="P0300", desc="Random/Multiple Cylinder Misfire Detected",      severity="high",     system="engine",    notes="Check ignition system, injectors"),
            DTCCode(code="P0171", desc="System Too Lean (Bank 1)",                       severity="medium",   system="engine",    notes="Check MAF sensor, vacuum leaks, O2 sensor"),
            DTCCode(code="P0217", desc="Engine Coolant Over Temperature Condition",      severity="critical", system="cooling",   notes="Stop vehicle immediately. Check coolant level, thermostat, water pump"),
            DTCCode(code="P0420", desc="Catalyst System Efficiency Below Threshold",     severity="medium",   system="emission",  notes="Inspect catalytic converter and O2 sensors"),
            DTCCode(code="C0035", desc="Left Front Wheel Speed Sensor Circuit Fault",    severity="high",     system="brakes",    notes="Inspect ABS sensor and wiring"),
            DTCCode(code="B0001", desc="Driver Frontal Stage 1 Airbag Deployment Loop",  severity="critical", system="airbag",    notes="Do not drive until resolved. Visit dealer immediately"),
            DTCCode(code="P0562", desc="System Voltage Low",                             severity="medium",   system="electrical",notes="Check battery, alternator, charging system"),
            DTCCode(code="P0520", desc="Engine Oil Pressure Sensor/Switch Circuit",      severity="high",     system="lubrication",notes="Check oil level and pressure sensor immediately"),
            DTCCode(code="P0128", desc="Coolant Temperature Below Thermostat Reg Temp",  severity="low",      system="cooling",   notes="Thermostat may be stuck open"),
            DTCCode(code="P0401", desc="Exhaust Gas Recirculation Insufficient Flow",    severity="low",      system="emission",  notes="Clean or replace EGR valve"),
            DTCCode(code="U0100", desc="Lost Communication With ECM/PCM",               severity="critical", system="network",   notes="CAN bus fault — check wiring harness"),
        ]
        db.add_all(dtc_codes)

        today = date.today()
        snapshots = [
            TelematicsSnapshot(vehicle_code="VH001", fuel_level=65, battery_voltage=12.4, engine_temp=92,  oil_life=45, active_dtcs=[]),
            TelematicsSnapshot(vehicle_code="VH002", fuel_level=30, battery_voltage=11.8, engine_temp=108, oil_life=12, active_dtcs=["P0217", "P0171"]),
            TelematicsSnapshot(vehicle_code="VH003", fuel_level=8,  battery_voltage=11.2, engine_temp=88,  oil_life=72, active_dtcs=["P0562"]),
            TelematicsSnapshot(vehicle_code="VH004", fuel_level=55, battery_voltage=12.6, engine_temp=95,  oil_life=5,  active_dtcs=["P0520"]),
            TelematicsSnapshot(vehicle_code="VH005", fuel_level=78, battery_voltage=12.9, engine_temp=85,  oil_life=90, active_dtcs=["P0300", "C0035", "B0001"]),
            TelematicsSnapshot(vehicle_code="VH006", fuel_level=92, battery_voltage=12.8, engine_temp=89,  oil_life=95, active_dtcs=[]),
            TelematicsSnapshot(vehicle_code="VH007", fuel_level=22, battery_voltage=11.5, engine_temp=102, oil_life=3,  active_dtcs=["P0420", "P0217"]),
            TelematicsSnapshot(vehicle_code="VH008", fuel_level=48, battery_voltage=12.5, engine_temp=91,  oil_life=35, active_dtcs=[]),
        ]
        db.add_all(snapshots)
        db.commit()
        print(f"[telematics] {len(dtc_codes)} DTC codes, {len(snapshots)} snapshots seeded")
    finally:
        db.close()


# ===========================================================================
# INSURANCE — cs03_insurance
# ===========================================================================
def seed_insurance() -> None:
    db = InsuranceSession()
    try:
        _clear(db, VehicleInsurance, InsurancePlan)

        plans = [
            InsurancePlan(name="Third Party",    price=4_999.00,  duration="1 Year",  features=["Third party liability", "Personal accident cover"], is_active=True),
            InsurancePlan(name="Comprehensive",  price=12_999.00, duration="1 Year",  features=["Own damage", "Third party", "Theft", "Natural calamity", "Zero depreciation"], is_active=True),
            InsurancePlan(name="Premium Shield", price=21_499.00, duration="2 Years", features=["Comprehensive + Engine protect", "24x7 roadside assist", "NCB protect", "Key replacement"], is_active=True),
            InsurancePlan(name="Fleet Basic",    price=8_499.00,  duration="1 Year",  features=["Multi-vehicle discount", "Third party", "Own damage"], is_active=True),
        ]
        db.add_all(plans)

        today = date.today()
        policies = [
            VehicleInsurance(vehicle_code="VH001", provider="HDFC Ergo",     policy_no="POL-2022-VH001", plan_name="Comprehensive",  start_date=date(2022, 3, 15), expires_on=today + timedelta(days=30),  premium=12_999, status="active"),
            VehicleInsurance(vehicle_code="VH002", provider="Bajaj Allianz", policy_no="POL-2022-VH002", plan_name="Comprehensive",  start_date=date(2022, 7, 20), expires_on=today + timedelta(days=120), premium=9_500,  status="active"),
            VehicleInsurance(vehicle_code="VH003", provider="ICICI Lombard", policy_no="POL-2021-VH003", plan_name="Third Party",    start_date=date(2021, 5, 10), expires_on=today - timedelta(days=15),  premium=4_999,  status="expired"),
            VehicleInsurance(vehicle_code="VH004", provider="New India",     policy_no="POL-2020-VH004", plan_name="Comprehensive",  start_date=date(2020, 1, 25), expires_on=today + timedelta(days=60),  premium=11_200, status="active"),
            VehicleInsurance(vehicle_code="VH005", provider="Tata AIG",      policy_no="POL-2023-VH005", plan_name="Premium Shield", start_date=date(2023, 6, 1),  expires_on=today + timedelta(days=450), premium=21_499, status="active"),
            VehicleInsurance(vehicle_code="VH006", provider="HDFC Ergo",     policy_no="POL-2024-VH006", plan_name="Premium Shield", start_date=date(2024, 1, 10), expires_on=today + timedelta(days=660), premium=25_000, status="active"),
            VehicleInsurance(vehicle_code="VH007", provider="Oriental",      policy_no="POL-2019-VH007", plan_name="Third Party",    start_date=date(2019, 11, 5), expires_on=today - timedelta(days=90),  premium=4_999,  status="expired"),
            VehicleInsurance(vehicle_code="VH008", provider="Reliance",      policy_no="POL-2023-VH008", plan_name="Comprehensive",  start_date=date(2023, 2, 28), expires_on=today + timedelta(days=340), premium=13_500, status="active"),
        ]
        db.add_all(policies)
        db.commit()
        print(f"[insurance] {len(plans)} plans, {len(policies)} policies seeded")
    finally:
        db.close()


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == "__main__":
    print("Creating tables in all schemas...")
    create_all_schemas()

    print("\nSeeding data...")
    seed_auth()
    seed_vehicles()
    seed_warranty()
    seed_scheduler()
    seed_telematics()
    seed_insurance()

    print("\nDone. Summary of test accounts:")
    print("  admin@login : amresh@cs03.com  / Admin@123")
    print("  agent@login : priya@cs03.com   / Agent@123")
    print("  agent@login : rahul@cs03.com   / Agent@123")
    print("  supervisor  : sonia@cs03.com   / Super@123")
    print("\nVehicles seeded: VH001-VH008")
    print("  VH001 Honda Accord     — healthy, warranty active")
    print("  VH002 Royal Enfield    — OVERHEATING (P0217), lean (P0171), oil low")
    print("  VH003 Toyota Corolla   — low fuel 8%, low battery (P0562)")
    print("  VH004 VW Polo          — high mileage, oil life CRITICAL 5%")
    print("  VH005 Tesla Model 3    — 3 active DTCs incl. airbag + wheel speed")
    print("  VH006 Mercedes C-Class — new vehicle, all healthy")
    print("  VH007 Jaguar XE        — critical condition, 2 DTCs, warranty expired")
    print("  VH008 Mahindra XUV700  — scheduled service next week")
