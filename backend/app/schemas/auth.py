from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    role_name: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    is_active: bool
    is_superuser: bool
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    display_name: Optional[str] = None
    role_name: Optional[str] = None
    password: str
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserListResponse(BaseModel):
    items: List[UserProfile]


TokenResponse.model_rebuild()
