from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db import get_db
from app.models import Session as UserSession
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="האימייל כבר רשום במערכת")

    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_token(str(user.id), 30, "access")
    refresh_token = create_token(str(user.id), 60 * 24 * 7, "refresh")
    db.add(UserSession(user_id=user.id, refresh_token=refresh_token, is_active=True))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="פרטי ההתחברות שגויים")
    access_token = create_token(str(user.id), 30, "access")
    refresh_token = create_token(str(user.id), 60 * 24 * 7, "refresh")
    db.add(UserSession(user_id=user.id, refresh_token=refresh_token, is_active=True))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="טוקן רענון לא תקין")
    existing = (
        db.query(UserSession)
        .filter(UserSession.refresh_token == payload.refresh_token, UserSession.is_active.is_(True))
        .first()
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="טוקן הרענון בוטל")
    access_token = create_token(claims["sub"], 30, "access")
    refresh_token = create_token(claims["sub"], 60 * 24 * 7, "refresh")
    existing.is_active = False
    db.add(UserSession(user_id=int(claims["sub"]), refresh_token=refresh_token, is_active=True))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
