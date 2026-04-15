from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: str, expires_minutes: int, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_token(token: str, token_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
