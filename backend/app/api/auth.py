from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RefreshToken, User
from ..schemas import AuthCredentials, RefreshRequest, RegisterRequest, TokenPair, UserOut
from ..security import decode_token, issue_access_token, issue_refresh_token, verify_password, hash_password
from .deps import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(db: Session, user: User) -> TokenPair:
    access = issue_access_token(user.id, user.role)
    refresh, jti, expires = issue_refresh_token(user.id)
    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=expires))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    duplicate = db.scalar(select(User).where((User.username == payload.username) | (User.email == payload.email)))
    if duplicate:
        raise HTTPException(status_code=409, detail="Username or email is already registered")
    allowed_roles = {"Emergency Dispatcher", "Field Operator", "Hospital Operator"}
    role = payload.role
    if role not in allowed_roles:
        raise HTTPException(status_code=422, detail=f"Unsupported role '{role}'. Allowed roles: {sorted(allowed_roles)}")
    user = User(username=payload.username, email=payload.email, password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.flush()
    return _token_pair(db, user)


@router.post("/login", response_model=TokenPair)
def login(payload: AuthCredentials, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return _token_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    record = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims.get("jti")).with_for_update())
    expires_at = record.expires_at if record is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if record is None or record.revoked_at is not None or expires_at is None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token has expired or was already used")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    record.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return _token_pair(db, user)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict[str, bool]:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError:
        return {"ok": False}
    record = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims.get("jti")))
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, UserOut]:
    return {"user": UserOut.model_validate(user)}


@router.get("/users", response_model=list[UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_roles("Administrator"))) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.patch("/users/{user_id}/active", response_model=UserOut, tags=["users"])
def set_user_active(user_id: str, is_active: bool, db: Session = Depends(get_db), _admin: User = Depends(require_roles("Administrator"))) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
