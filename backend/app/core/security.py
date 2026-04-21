from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录令牌")

    user = db.query(User).filter(User.username == subject).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号已停用")
    return user


def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def user_has_permission(user: User, permission: str) -> bool:
    if user.is_superuser:
        return True
    permissions = set(user.permissions or [])
    return permission in permissions


def user_has_any_permission(user: User, permissions: Iterable[str]) -> bool:
    if user.is_superuser:
        return True
    user_permissions = set(user.permissions or [])
    return any(permission in user_permissions for permission in permissions)


def require_permission(permission: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(current_user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号没有此功能权限")
        return current_user

    return dependency


def require_any_permission(*permissions: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_any_permission(current_user, permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号没有此功能权限")
        return current_user

    return dependency
