from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt as pyjwt
from jwt.exceptions import PyJWTError

from config.settings import get_settings

settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return pyjwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
    except PyJWTError:
        return None


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
