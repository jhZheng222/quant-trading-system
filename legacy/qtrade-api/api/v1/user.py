from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from models.user import User
from typing import Union
from schemas.user import UserCreate, UserLogin, UserResponse, Token, UserUpdate, TradingPairUpdate
from schemas.response import SuccessResponse, ErrorResponse
from utils.auth import get_password_hash, verify_password, create_access_token, get_current_active_user
from datetime import timedelta, datetime
from core.config import settings

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# 用户注册
@router.post("/register", response_model=SuccessResponse[UserResponse])
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        return ErrorResponse(
            code=status.HTTP_400_BAD_REQUEST,
            message="用户名已存在"
        )

    # 检查邮箱是否已存在
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        return ErrorResponse(
            code=status.HTTP_400_BAD_REQUEST,
            message="邮箱已存在"
        )

    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        trading_pairs=user.trading_pairs,
        created_at=datetime.now()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return SuccessResponse(
        data=UserResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            last_login_at=db_user.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if db_user.last_login_at else None,
            trading_pairs=db_user.trading_pairs
        ),
        message="注册成功"
    )

# 用户登录
@router.post("/login", response_model=SuccessResponse[Token])
def login(user: UserLogin, db: Session = Depends(get_db)):
    # 检查用户是否存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        return ErrorResponse(
            code=status.HTTP_401_UNAUTHORIZED,
            message="用户名或密码错误"
        )

    # 更新最后登录时间
    db_user.last_login_at = datetime.now()
    db.commit()
    db.refresh(db_user)

    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )

    return SuccessResponse(
        data=Token(access_token=access_token, token_type="bearer"),
        message="登录成功"
    )

# 获取当前用户信息
@router.get("/me", response_model=SuccessResponse[UserResponse])
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return SuccessResponse(
        data=UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if current_user.created_at else None,
            last_login_at=current_user.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if current_user.last_login_at else None,
            trading_pairs=current_user.trading_pairs
        ),
        message="获取用户信息成功"
    )

# 更新用户交易对
@router.patch("/me/trading-pairs", response_model=Union[SuccessResponse[UserResponse], ErrorResponse])
def update_user_trading_pairs(
    trading_pair_update: TradingPairUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 初始化trading_pairs列表（如果为空）
    if current_user.trading_pairs is None:
        current_user.trading_pairs = []
    else:
        # 确保trading_pairs是列表类型
        current_user.trading_pairs = list(current_user.trading_pairs)

    # 执行添加或删除操作
    if trading_pair_update.action == "add":
        if trading_pair_update.trading_pair not in current_user.trading_pairs:
            current_user.trading_pairs.append(trading_pair_update.trading_pair)
            message = f"成功添加交易对: {trading_pair_update.trading_pair}"
        else:
            message = f"交易对 {trading_pair_update.trading_pair} 已存在"
    elif trading_pair_update.action == "remove":
        if trading_pair_update.trading_pair in current_user.trading_pairs:
            current_user.trading_pairs.remove(trading_pair_update.trading_pair)
            message = f"成功删除交易对: {trading_pair_update.trading_pair}"
        else:
            message = f"交易对 {trading_pair_update.trading_pair} 不存在"
    else:
        return ErrorResponse(
            code=status.HTTP_400_BAD_REQUEST,
            message="无效的操作类型，只支持 'add' 或 'remove'"
        )

    db.commit()
    # 重新查询用户以确保获取最新数据
    updated_user = db.query(User).filter(User.id == current_user.id).first()

    return SuccessResponse(
        data=UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            role=updated_user.role,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if updated_user.created_at else None,
            last_login_at=updated_user.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if updated_user.last_login_at else None,
            trading_pairs=updated_user.trading_pairs
        ),
        message=message
    )

# 更新用户信息
@router.put("/me", response_model=SuccessResponse[UserResponse])
def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 更新用户信息
    if user_update.email:
        current_user.email = user_update.email
    if user_update.password:
        current_user.password_hash = get_password_hash(user_update.password)
    if user_update.role:
        current_user.role = user_update.role
    if user_update.is_active is not None:
        current_user.is_active = user_update.is_active
    if user_update.trading_pairs is not None:
        current_user.trading_pairs = user_update.trading_pairs

    db.commit()
    db.refresh(current_user)

    return SuccessResponse(
        data=UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if current_user.created_at else None,
            last_login_at=current_user.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if current_user.last_login_at else None,
            trading_pairs=current_user.trading_pairs
        ),
        message="更新用户信息成功"
    )