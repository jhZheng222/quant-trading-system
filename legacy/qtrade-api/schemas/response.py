from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel, Field

DataT = TypeVar('DataT')

class ResponseModel(BaseModel, Generic[DataT]):
    code: int = Field(..., description="响应状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[DataT] = Field(None, description="响应数据")

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "message": "请求成功",
                "data": {}
            }
        }

class SuccessResponse(ResponseModel[DataT]):
    def __init__(self, data: Optional[DataT] = None, message: str = "请求成功", code: int = 200):
        super().__init__(code=code, message=message, data=data)

class ErrorResponse(ResponseModel[Any]):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(code=code, message=message, data=data)