from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, MessageResponse, TokenResponse, UserProfile
from app.services.auth_service import AuthService


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.username, payload.password)
    token = create_access_token(user.username)
    return TokenResponse(
        access_token=token,
        user=UserProfile.model_validate(user),
    )


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    return UserProfile.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(db)
    service.change_password(current_user.id, payload.old_password, payload.new_password)
    return MessageResponse(message="密码已修改")
