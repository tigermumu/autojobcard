from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    role_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
