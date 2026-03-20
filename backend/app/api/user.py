"""
Auth API Router — app/api/user.py

Handles user registration, login, and authenticated profile retrieval.

Endpoints:
    POST /api/user/signup — register a new user account
    POST /api/user/login  — authenticate and receive a JWT
    GET  /api/user/me     — return the authenticated user's profile

Security:
    Passwords are hashed with bcrypt (never stored in plaintext).
    Authentication tokens are signed JWTs; the secret and algorithm come
    from ``app.config.settings``.

DB schema used:
    cs03_auth — ``users`` table via ``app.db.schemas.auth.User``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_auth_db
from app.db.schemas.auth import User

logger = logging.getLogger(__name__)

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def _decode_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    """Decode and validate a Bearer JWT from the Authorization header.

    Args:
        credentials: The HTTP Bearer credentials extracted by FastAPI's
            ``HTTPBearer`` security scheme.  May be ``None`` if the header
            was absent.

    Returns:
        dict: The decoded JWT payload (includes ``sub``, ``email``, ``role``,
            ``first_name``, ``last_name``, ``exp``).

    Raises:
        HTTPException: 401 if ``credentials`` is ``None`` or the token is
            invalid/expired.
    """
    if not credentials:
        logger.warning("_decode_token: no credentials provided")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        logger.debug("_decode_token: decoding JWT token")
        payload = jwt.decode(
            credentials.credentials, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        logger.debug(f"_decode_token: token valid sub={payload.get('sub')!r}")
        return payload
    except JWTError as exc:
        logger.warning(f"_decode_token: invalid or expired token error={exc}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    """Request body for the ``/signup`` endpoint.

    Attributes:
        first_name: User's given name.
        last_name: User's family name.
        email: Unique email address (validated as RFC-compliant email).
        password: Plaintext password; hashed with bcrypt before storage.
        mobile: Optional mobile phone number string.
    """

    first_name: str
    last_name: str
    email: EmailStr
    password: str
    mobile: str = ""


class LoginRequest(BaseModel):
    """Request body for the ``/login`` endpoint.

    Attributes:
        email: Registered email address.
        password: Plaintext password to verify against the stored bcrypt hash.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body returned from the ``/login`` endpoint.

    Attributes:
        access_token: Signed JWT string.
        token_type: Always ``'bearer'``.
        expires_in: Token lifetime in seconds.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_token(user: User) -> str:
    """Generate a signed JWT for the given user.

    The token payload includes the user's ID (``sub``), email, role, and
    display name fields.  Expiry is set to
    ``settings.ACCESS_TOKEN_EXPIRE_MINUTES`` from now (UTC).

    Args:
        user: The authenticated ``User`` ORM instance.

    Returns:
        str: A signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub":        str(user.id),
        "email":      user.email,
        "role":       user.role,
        "first_name": user.first_name,
        "last_name":  user.last_name,
        "exp":        expire,
    }
    logger.debug(
        f"_create_token: creating JWT for user_id={user.id} "
        f"email={user.email!r} role={user.role!r} expires={expire.isoformat()}"
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    req: SignupRequest,
    db: Session = Depends(get_auth_db),
) -> dict:
    """Register a new user account.

    Checks for duplicate email, bcrypt-hashes the password, and persists the
    new ``User`` row to ``cs03_auth``.

    Args:
        req: The parsed ``SignupRequest`` with user profile fields.
        db: Injected SQLAlchemy session for ``cs03_auth``.

    Returns:
        dict: ``{"message": "User created", "id": <new_user_id>}``

    Raises:
        HTTPException: 400 if the email address is already registered.
    """
    logger.info(f"POST /api/user/signup email={req.email!r} name={req.first_name!r} {req.last_name!r}")

    logger.debug(f"signup: checking for duplicate email={req.email!r}")
    if db.query(User).filter(User.email == req.email).first():
        logger.warning(f"signup: duplicate email rejected email={req.email!r}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    logger.debug(f"signup: hashing password for email={req.email!r}")
    hashed_pw = _bcrypt.hashpw(req.password.encode(), _bcrypt.gensalt()).decode()

    user = User(
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        password=hashed_pw,
        mobile=req.mobile,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"signup: user created user_id={user.id} email={req.email!r}")
    return {"message": "User created", "id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest,
    db: Session = Depends(get_auth_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Looks up the user by email, verifies the bcrypt password hash, checks that
    the account is active, and generates a signed JWT.

    Args:
        req: The parsed ``LoginRequest`` with ``email`` and ``password``.
        db: Injected SQLAlchemy session for ``cs03_auth``.

    Returns:
        TokenResponse: Contains ``access_token``, ``token_type``, and
            ``expires_in`` (seconds).

    Raises:
        HTTPException: 401 if email/password is wrong.
        HTTPException: 403 if the account is disabled.
    """
    logger.info(f"POST /api/user/login email={req.email!r}")

    logger.debug(f"login: querying user email={req.email!r}")
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not _bcrypt.checkpw(req.password.encode(), user.password.encode()):
        logger.warning(f"login: invalid credentials email={req.email!r}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        logger.warning(f"login: account disabled user_id={user.id} email={req.email!r}")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = _create_token(user)
    logger.info(
        f"login: successful user_id={user.id} email={req.email!r} role={user.role!r}"
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_auth_db),
    ) -> dict:
    """Return the authenticated user's profile.

    Decodes the Bearer token, extracts the user ID from ``sub``, and fetches
    the full user record from ``cs03_auth``.

    Args:
        credentials: Bearer token from the ``Authorization`` header.
        db: Injected SQLAlchemy session for ``cs03_auth``.

    Returns:
        dict: User profile containing ``id``, ``first_name``, ``last_name``,
            ``email``, and ``role``.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
        HTTPException: 404 if the user record no longer exists in the DB.
    """
    logger.info("GET /api/user/me")

    logger.debug("get_current_user: decoding token")
    payload = _decode_token(credentials)

    user_id = int(payload.get("sub", 0))
    logger.debug(f"get_current_user: querying user_id={user_id}")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.warning(f"get_current_user: user not found user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(
        f"get_current_user: returning profile user_id={user.id} "
        f"email={user.email!r} role={user.role!r}"
    )
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
    }
