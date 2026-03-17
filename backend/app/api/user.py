from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from pydantic import BaseModel
from jose import jwt
from passlib.hash import bcrypt

SECRET = "SUPERSECRET123"
ALGO = "HS256"

router = APIRouter()

# -------------------------
# Request Schemas
# -------------------------
class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    mobile: str

class LoginRequest(BaseModel):
    email: str
    password: str


# -------------------------
# Signup
# -------------------------
@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        raise HTTPException(400, "Email already registered")

    # Need to implement hasing    
    # hashed_pw = bcrypt.hash(req.password)

    new_user = User(
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        password=req.password,
        mobile=req.mobile
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created"}


# -------------------------
# Login
# -------------------------
@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()

    if not user:
        raise HTTPException(401, "Invalid email or password")

    if not (req.password == user.password):
        raise HTTPException(401, "Invalid email or password")

    token = jwt.encode({"email": user.email, "id": user.id}, SECRET, algorithm=ALGO)

    return {"access_token": token}