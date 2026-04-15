from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db import get_db
from app.models import Session as UserSession
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.jwt_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_token_expire_minutes * 60,
        httponly=True,
        secure=settings.jwt_refresh_cookie_secure,
        samesite=settings.jwt_refresh_cookie_samesite,
        path="/auth",
    )


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="האימייל כבר רשום במערכת")

    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_token(str(user.id), settings.jwt_access_token_expire_minutes, "access")
    refresh_token = create_token(str(user.id), settings.jwt_refresh_token_expire_minutes, "refresh")
    db.add(UserSession(user_id=user.id, refresh_token=refresh_token, is_active=True))
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="פרטי ההתחברות שגויים")
    access_token = create_token(str(user.id), settings.jwt_access_token_expire_minutes, "access")
    refresh_token = create_token(str(user.id), settings.jwt_refresh_token_expire_minutes, "refresh")
    db.add(UserSession(user_id=user.id, refresh_token=refresh_token, is_active=True))
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    refresh_token = payload.refresh_token if payload else None
    if not refresh_token:
        refresh_token = request.cookies.get(settings.jwt_refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="חסר טוקן רענון")
    try:
        claims = decode_token(refresh_token, "refresh")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="טוקן רענון לא תקין")
    existing = (
        db.query(UserSession)
        .filter(UserSession.refresh_token == refresh_token, UserSession.is_active.is_(True))
        .first()
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="טוקן הרענון בוטל")
    access_token = create_token(claims["sub"], settings.jwt_access_token_expire_minutes, "access")
    refresh_token = create_token(claims["sub"], settings.jwt_refresh_token_expire_minutes, "refresh")
    existing.is_active = False
    db.add(UserSession(user_id=int(claims["sub"]), refresh_token=refresh_token, is_active=True))
    db.commit()
    if response:
        _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)
