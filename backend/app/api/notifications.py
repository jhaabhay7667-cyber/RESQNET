from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.deps import get_current_user
from ..database import get_db
from ..models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    records = db.scalars(select(Notification).where((Notification.user_id.is_(None)) | (Notification.user_id == user.id)).order_by(Notification.created_at.desc()).limit(50)).all()
    return [{"id": item.id, "title": item.title, "message": item.message, "is_read": item.is_read, "created_at": item.created_at.isoformat()} for item in records]


@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, bool]:
    item = db.get(Notification, notification_id)
    if item is None or item.user_id not in {None, user.id}:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    db.commit()
    return {"ok": True}
