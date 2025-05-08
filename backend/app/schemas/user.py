"""用户相关模式

包含用户相关的Pydantic模型。
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


# 基础用户模型
class UserBase(BaseModel):
    """用户基础模型"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    
    # 添加验证器将is_active映射到status
    @validator("is_active", pre=True)
    def validate_is_active(cls, v, values):
        if isinstance(v, str):
            return v == "active"
        return v
    
    # 添加验证器将is_superuser映射到is_admin
    @validator("is_superuser", pre=True)
    def validate_is_superuser(cls, v, values):
        if hasattr(v, "is_admin"):
            return v.is_admin
        return v


class UserCreate(UserBase):
    """用户创建模型"""
    username: str
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    """用户更新模型"""
    password: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None


class UserInDBBase(UserBase):
    """数据库中的用户基础模型"""
    id: Optional[int] = None
    phone: Optional[str] = None
    registration_date: Optional[datetime] = None
    last_login: Optional[datetime] = None
    status: Optional[str] = "active"
    is_admin: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
    
    # 确保从ORM模型映射时属性一致
    @validator("is_active", pre=True)
    def map_status_to_is_active(cls, v, values):
        # 如果有status字段，则根据status确定is_active
        if "status" in values:
            return values["status"] == "active"
        return v
    
    @validator("is_superuser", pre=True)
    def map_is_admin_to_is_superuser(cls, v, values):
        # 如果有is_admin字段，映射到is_superuser
        if "is_admin" in values:
            return values["is_admin"]
        return v


class User(UserInDBBase):
    """返回给API的用户模型"""
    pass


class UserInDB(UserInDBBase):
    """数据库中的用户模型"""
    password: str


# 用户角色模型
class RoleBase(BaseModel):
    """角色基础模型"""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """角色创建模型"""
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(RoleBase):
    """角色更新模型"""
    name: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleInDBBase(RoleBase):
    """数据库中的角色基础模型"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class Role(RoleInDBBase):
    """返回给API的角色模型"""
    permissions: List[str] = Field(default_factory=list)


class RoleInDB(RoleInDBBase):
    """数据库中的角色模型"""
    permissions: dict 
