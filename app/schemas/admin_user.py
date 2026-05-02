from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    role_id: str


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserResponse(BaseModel):
    user_id: str
    email: str
    role_id: str
    role_name: str
    is_active: bool
    must_change_password: bool


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[AdminUserResponse]