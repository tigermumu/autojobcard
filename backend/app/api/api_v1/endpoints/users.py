from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionCodes
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.schemas.auth import (
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserProfile,
    UserUpdate,
)
from app.services.auth_service import AuthService


router = APIRouter(dependencies=[Depends(require_permission(PermissionCodes.ADMIN_USER_MANAGEMENT))])


@router.get("", response_model=UserListResponse)
def list_users(db: Session = Depends(get_db)):
    service = AuthService(db)
    users = [UserProfile.model_validate(item) for item in service.list_users()]
    return UserListResponse(items=users)


@router.post("", response_model=UserProfile)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return UserProfile.model_validate(service.create_user(payload))


@router.put("/{user_id}", response_model=UserProfile)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(db)
    return UserProfile.model_validate(
        service.update_user(user_id, payload, current_user_id=current_user.id)
    )


@router.put("/{user_id}/password", response_model=UserProfile)
def update_user_password(
    user_id: int,
    payload: UserPasswordUpdate,
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return UserProfile.model_validate(service.update_password(user_id, payload.password))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(db)
    service.delete_user(user_id, current_user_id=current_user.id)
    return {"message": "用户已删除"}
