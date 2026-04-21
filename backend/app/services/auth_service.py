from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import ALL_PERMISSIONS
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_permissions(permissions: Optional[List[str]]) -> List[str]:
        normalized = []
        seen = set()
        for permission in permissions or []:
            code = str(permission or "").strip()
            if not code or code in seen or code not in ALL_PERMISSIONS:
                continue
            seen.add(code)
            normalized.append(code)
        return normalized

    def list_users(self) -> List[User]:
        return self.db.query(User).order_by(User.id.asc()).all()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username.strip()).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def authenticate(self, username: str, password: str) -> User:
        user = self.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号已停用")
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_user(self, payload: UserCreate) -> User:
        username = payload.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="用户名不能为空")
        if self.get_by_username(username):
            raise HTTPException(status_code=400, detail="用户名已存在")
        if len(payload.password.strip()) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于 6 位")

        user = User(
            username=username,
            display_name=(payload.display_name or "").strip() or None,
            role_name=(payload.role_name or "").strip() or None,
            password_hash=get_password_hash(payload.password),
            permissions=self._normalize_permissions(payload.permissions),
            is_active=payload.is_active,
            is_superuser=payload.is_superuser,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, payload: UserUpdate, current_user_id: Optional[int] = None) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if payload.is_superuser is False and current_user_id == user.id:
            raise HTTPException(status_code=400, detail="不能取消当前登录管理员的超级管理员身份")
        if payload.is_active is False and current_user_id == user.id:
            raise HTTPException(status_code=400, detail="不能停用当前登录账号")

        if payload.display_name is not None:
            user.display_name = payload.display_name.strip() or None
        if payload.role_name is not None:
            user.role_name = payload.role_name.strip() or None
        if payload.permissions is not None:
            user.permissions = self._normalize_permissions(payload.permissions)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.is_superuser is not None:
            user.is_superuser = payload.is_superuser

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user_id: int, password: str) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if len(password.strip()) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于 6 位")

        user.password_hash = get_password_hash(password)
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        user = self.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="原密码不正确")
        if len(new_password.strip()) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于 6 位")

        user.password_hash = get_password_hash(new_password)
        self.db.commit()

    def delete_user(self, user_id: int, current_user_id: Optional[int] = None) -> None:
        user = self.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if current_user_id == user.id:
            raise HTTPException(status_code=400, detail="不能删除当前登录账号")

        self.db.delete(user)
        self.db.commit()


def ensure_default_admin(db: Session, username: str, password: str, display_name: Optional[str] = None) -> None:
    exists = db.query(User.id).first()
    if exists:
        return

    user = User(
        username=username.strip(),
        display_name=(display_name or "").strip() or "系统管理员",
        role_name="管理员",
        password_hash=get_password_hash(password),
        permissions=list(ALL_PERMISSIONS),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
