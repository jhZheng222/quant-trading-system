from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.user import router as user_router
from core.config import settings
from database.database import Base, enigne

# 创建数据库表
Base.metadata.create_all(bind=enigne)

# 初始化FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user_router, prefix=settings.API_V1_STR)

# 根路径
@app.get("/")
def root():
    return {"message": "QTrade API is running."}