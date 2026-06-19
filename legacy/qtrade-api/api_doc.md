# API 接口文档

## 用户相关接口

### 1. 用户注册
- **URL**: `/users/register`
- **方法**: `POST`
- **描述**: 注册新用户
- **请求体**: `UserCreate`
- **请求样例**: 
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpassword123",
  "role": "NORMAL",
  "trading_pairs": ["BTCUSDT", "ETHUSDT"]
}
```
- **成功响应样例**: 
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "testuser",
    "email": "test@example.com",
    "role": "NORMAL",
    "is_active": true,
    "created_at": "2023-11-22T12:34:56Z",
    "last_login_at": null,
    "trading_pairs": ["BTCUSDT", "ETHUSDT"]
  }
}
```
- **错误响应样例**: 
```json
{
  "code": 400,
  "message": "用户名已存在",
  "data": null
}
```
- **响应**: `SuccessResponse[UserResponse]`

### 2. 用户登录
- **URL**: `/users/login`
- **方法**: `POST`
- **描述**: 用户登录获取访问令牌
- **请求体**: `UserLogin`
- **请求样例**: 
```json
{
  "username": "testuser",
  "password": "testpassword123"
}
```
- **成功响应样例**: 
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```
- **错误响应样例**: 
```json
{
  "code": 401,
  "message": "无效的凭据",
  "data": null
}
```
- **响应**: `SuccessResponse[Token]`

### 3. 获取当前用户信息
- **URL**: `/users/me`
- **方法**: `GET`
- **描述**: 获取当前登录用户的信息
- **请求头**: 需包含 `Authorization: Bearer {token}`
- **成功响应样例**: 
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "testuser",
    "email": "test@example.com",
    "role": "NORMAL",
    "is_active": true,
    "created_at": "2023-11-22T12:34:56Z",
    "last_login_at": "2023-11-22T13:45:67Z",
    "trading_pairs": ["BTCUSDT", "ETHUSDT"]
  }
}
```
- **错误响应样例**: 
```json
{
  "code": 401,
  "message": "无法验证凭据",
  "data": null
}
```
- **响应**: `SuccessResponse[UserResponse]`

### 4. 更新用户交易对
- **URL**: `/users/me/trading-pairs`
- **方法**: `PATCH`
- **描述**: 添加或删除用户的交易对
- **请求头**: 需包含 `Authorization: Bearer {token}`
- **请求体**: `TradingPairUpdate`
- **添加交易对请求样例**: 
```json
{
  "action": "add",
  "trading_pair": "SOLUSDT"
}
```
- **删除交易对请求样例**: 
```json
{
  "action": "remove",
  "trading_pair": "BTCUSDT"
}
```
- **无效操作请求样例**: 
```json
{
  "action": "invalid",
  "trading_pair": "BTCUSDT"
}
```
- **成功响应样例**: 
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "testuser",
    "email": "test@example.com",
    "role": "NORMAL",
    "is_active": true,
    "created_at": "2023-11-22T12:34:56Z",
    "last_login_at": "2023-11-22T13:45:67Z",
    "trading_pairs": ["ETHUSDT", "SOLUSDT"]
  }
}
```
- **错误响应样例**: 
```json
{
  "code": 400,
  "message": "无效的操作类型。必须是 'add' 或 'remove'。",
  "data": null
}
```
- **响应**: `Union[SuccessResponse[UserResponse], ErrorResponse]`

### 5. 更新用户信息
- **URL**: `/users/me`
- **方法**: `PUT`
- **描述**: 更新当前登录用户的信息
- **请求头**: 需包含 `Authorization: Bearer {token}`
- **请求体**: `UserUpdate`
- **请求样例**: 
```json
{
  "email": "updated@example.com",
  "password": "newpassword123",
  "is_active": true
}
```
- **成功响应样例**: 
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "testuser",
    "email": "updated@example.com",
    "role": "NORMAL",
    "is_active": true,
    "created_at": "2023-11-22T12:34:56Z",
    "last_login_at": "2023-11-22T13:45:67Z",
    "trading_pairs": ["ETHUSDT", "SOLUSDT"]
  }
}
```
- **错误响应样例**: 
```json
{
  "code": 400,
  "message": "邮箱已被注册",
  "data": null
}
```
- **响应**: `SuccessResponse[UserResponse]`

## 数据模型

### 1. 枚举类型

#### UserRole
```python
class UserRole(str, Enum):
    NORMAL = "NORMAL"
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"
```

### 2. 请求模型

#### UserCreate
```python
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    password: str = Field(..., min_length=6, description="密码")
    role: Optional[UserRole] = Field(UserRole.NORMAL, description="用户角色")
    trading_pairs: Optional[List[str]] = Field([], description="交易对")
```

#### UserLogin
```python
class UserLogin(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
```

#### TradingPairUpdate
```python
class TradingPairUpdate(BaseModel):
    action: str = Field(..., description="操作类型: add 或 remove")
    trading_pair: str = Field(..., description="交易对名称")
```

#### UserUpdate
```python
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="电子邮箱")
    password: Optional[str] = Field(None, min_length=6, description="密码")
    role: Optional[UserRole] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    trading_pairs: Optional[List[str]] = Field(None, description="交易对")
```

### 3. 响应模型

#### UserResponse
```python
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: Optional[str]
    last_login_at: Optional[str]
    trading_pairs: Optional[List[str]]
```

#### Token
```python
class Token(BaseModel):
    access_token: str
    token_type: str
```

#### ResponseModel
```python
class ResponseModel(BaseModel, Generic[DataT]):
    code: int = Field(..., description="响应状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[DataT] = Field(None, description="响应数据")
```

#### SuccessResponse
```python
class SuccessResponse(ResponseModel[DataT]):
    def __init__(self, data: Optional[DataT] = None, message: str = "请求成功", code: int = 200):
        super().__init__(code=code, message=message, data=data)
```

#### ErrorResponse
```python
class ErrorResponse(ResponseModel[Any]):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(code=code, message=message, data=data)
```