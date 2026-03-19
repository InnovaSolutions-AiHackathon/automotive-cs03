from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.scheduler_models import Customer, Vehicle
from loguru import logger


# ======================== CUSTOMER CRUD OPERATIONS ========================

def create_customer(db: Session, name: str, email: str, phone: Optional[str] = None) -> Customer:
    """Create a new customer."""
    try:
        customer = Customer(name=name, email=email, phone=phone)
        db.add(customer)
        db.commit()
        db.refresh(customer)
        logger.info(f"Customer created: {customer.id} - {email}")
        return customer
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating customer: {e}")
        raise


def get_customer(db: Session, customer_id: int) -> Optional[Customer]:
    """Get customer by ID."""
    try:
        return db.query(Customer).filter(Customer.id == customer_id).first()
    except Exception as e:
        logger.error(f"Error fetching customer: {e}")
        return None


def get_customer_by_email(db: Session, email: str) -> Optional[Customer]:
    """Get customer by email."""
    try:
        return db.query(Customer).filter(Customer.email == email).first()
    except Exception as e:
        logger.error(f"Error fetching customer by email: {e}")
        return None


def get_all_customers(db: Session) -> List[Customer]:
    """Get all customers."""
    try:
        return db.query(Customer).all()
    except Exception as e:
        logger.error(f"Error fetching all customers: {e}")
        return []


def update_customer(db: Session, customer_id: int, **kwargs) -> Optional[Customer]:
    """Update customer."""
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None
        
        for key, value in kwargs.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)
        
        db.commit()
        db.refresh(customer)
        logger.info(f"Customer {customer_id} updated")
        return customer
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating customer: {e}")
        raise


def delete_customer(db: Session, customer_id: int) -> bool:
    """Delete a customer."""
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return False
        db.delete(customer)
        db.commit()
        logger.info(f"Customer {customer_id} deleted")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting customer: {e}")
        return False


# ======================== VEHICLE CRUD OPERATIONS ========================

def create_vehicle(
    db: Session,
    vehicle_code: str,
    vin: str,
    make: str,
    model: str,
    year: int,
    purchase_date,
    customer_id: int,
    odometer: int = 0,
    fuel_level: int = 100,
    battery_voltage: float = 12.6,
    engine_temp: int = 90,
    oil_life: int = 100
) -> Vehicle:
    """Create a new vehicle."""
    try:
        vehicle = Vehicle(
            vehicle_code=vehicle_code,
            vin=vin,
            make=make,
            model=model,
            year=year,
            purchase_date=purchase_date,
            customer_id=customer_id,
            odometer=odometer,
            fuel_level=fuel_level,
            battery_voltage=battery_voltage,
            engine_temp=engine_temp,
            oil_life=oil_life
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        logger.info(f"Vehicle created: {vehicle.id} - {vin}")
        return vehicle
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating vehicle: {e}")
        raise


def get_vehicle(db: Session, vehicle_id: int) -> Optional[Vehicle]:
    """Get vehicle by ID."""
    try:
        return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    except Exception as e:
        logger.error(f"Error fetching vehicle: {e}")
        return None


def get_vehicle_by_vin(db: Session, vin: str) -> Optional[Vehicle]:
    """Get vehicle by VIN."""
    try:
        return db.query(Vehicle).filter(Vehicle.vin == vin).first()
    except Exception as e:
        logger.error(f"Error fetching vehicle by VIN: {e}")
        return None


def get_vehicle_by_code(db: Session, vehicle_code: str) -> Optional[Vehicle]:
    """Get vehicle by vehicle code."""
    try:
        return db.query(Vehicle).filter(Vehicle.vehicle_code == vehicle_code).first()
    except Exception as e:
        logger.error(f"Error fetching vehicle by code: {e}")
        return None


def get_vehicles_by_customer(db: Session, customer_id: int) -> List[Vehicle]:
    """Get all vehicles for a customer."""
    try:
        return db.query(Vehicle).filter(Vehicle.customer_id == customer_id).all()
    except Exception as e:
        logger.error(f"Error fetching vehicles by customer: {e}")
        return []


def get_all_vehicles(db: Session) -> List[Vehicle]:
    """Get all vehicles."""
    try:
        return db.query(Vehicle).all()
    except Exception as e:
        logger.error(f"Error fetching all vehicles: {e}")
        return []


def update_vehicle(db: Session, vehicle_id: int, **kwargs) -> Optional[Vehicle]:
    """Update vehicle."""
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None
        
        for key, value in kwargs.items():
            if hasattr(vehicle, key) and value is not None:
                setattr(vehicle, key, value)
        
        db.commit()
        db.refresh(vehicle)
        logger.info(f"Vehicle {vehicle_id} updated")
        return vehicle
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating vehicle: {e}")
        raise


def delete_vehicle(db: Session, vehicle_id: int) -> bool:
    """Delete a vehicle."""
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return False
        db.delete(vehicle)
        db.commit()
        logger.info(f"Vehicle {vehicle_id} deleted")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting vehicle: {e}")
        return False
