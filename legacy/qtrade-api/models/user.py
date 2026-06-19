from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from database.database import Base
import uuid
from enum import Enum as PyEnum

class UserRole(PyEnum):
    NORMAL = "NORMAL"
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('NORMAL', 'MEMBER', 'ADMIN', name='user_role'), default='NORMAL')
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    trading_pairs = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())