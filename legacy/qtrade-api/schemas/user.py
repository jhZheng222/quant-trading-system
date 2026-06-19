from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    NORMAL = "NORMAL"
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    password: str = Field(..., min_length=6, description="密码")
    role: Optional[UserRole] = Field(UserRole.NORMAL, description="用户角色")
    trading_pairs: Optional[List[str]] = Field([], description="交易对")

class UserLogin(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: Optional[str]
    last_login_at: Optional[str]
    trading_pairs: Optional[List[str]]

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="电子邮箱")
    password: Optional[str] = Field(None, min_length=6, description="密码")
    role: Optional[UserRole] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    trading_pairs: Optional[List[str]] = Field(None, description="交易对")

class Token(BaseModel):
    access_token: str
    token_type: str

class TradingPairUpdate(BaseModel):
    action: str = Field(..., description="操作类型: add 或 remove")
    trading_pair: str = Field(..., description="交易对名称")

class TokenData(BaseModel):
    username: Optional[str] = None