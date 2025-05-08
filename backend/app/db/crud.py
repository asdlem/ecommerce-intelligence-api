"""数据库CRUD操作工具

包含基础的数据库增删改查操作函数，用于简化数据库操作。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import Base
from app.core.security import get_password_hash
from app.core.logging import get_logger

# 定义模型类型变量
ModelType = TypeVar("ModelType", bound=Base)
# 定义创建模型类型变量
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
# 定义更新模型类型变量
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """基础CRUD操作类"""

    def __init__(self, model: Type[ModelType]):
        """
        初始化CRUD对象
        
        Args:
            model: SQLAlchemy模型类
        """
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """
        通过ID获取记录
        
        Args:
            db: 数据库会话
            id: 记录ID
            
        Returns:
            查询到的记录或None
        """
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        获取多个记录
        
        Args:
            db: 数据库会话
            skip: 跳过记录的数量
            limit: 返回的记录数量
            
        Returns:
            查询到的记录列表
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        创建记录
        
        Args:
            db: 数据库会话
            obj_in: 要创建的记录数据，可以是Pydantic模型或字典
            
        Returns:
            创建后的记录
        """
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
            
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        更新记录
        
        Args:
            db: 数据库会话
            db_obj: 要更新的记录
            obj_in: 要更新的记录数据，可以是Pydantic模型或字典
            
        Returns:
            更新后的记录
        """
        obj_data = {c.name: getattr(db_obj, c.name) for c in db_obj.__table__.columns}
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        删除记录
        
        Args:
            db: 数据库会话
            id: 记录ID
            
        Returns:
            删除的记录或None
        """
        obj = await self.get(db=db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


# 用户CRUD操作
from app.db.models import User

class CRUDUser(CRUDBase[User, CreateSchemaType, UpdateSchemaType]):
    """用户CRUD操作类"""
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        通过邮箱获取用户
        
        Args:
            db: 数据库会话
            email: 用户邮箱
            
        Returns:
            用户记录或None
        """
        query = select(self.model).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            db: 数据库会话
            username: 用户名
            
        Returns:
            用户记录或None
        """
        query = select(self.model).where(self.model.username == username)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    # 添加获取用户的方法
    def get_by_username_sync(self, db: Session, *, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            db: 数据库会话
            username: 用户名
            
        Returns:
            用户记录或None
        """
        query = select(self.model).where(self.model.username == username)
        result = db.execute(query)
        return result.scalar_one_or_none()
    
    # 添加获取用户的方法
    def get_by_email_sync(self, db: Session, *, email: str) -> Optional[User]:
        """
        通过邮箱获取用户
        
        Args:
            db: 数据库会话
            email: 用户邮箱
            
        Returns:
            用户记录或None
        """
        query = select(self.model).where(self.model.email == email)
        result = db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_user(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> User:
        """
        创建用户
        
        Args:
            db: 数据库会话
            obj_in: 用户数据
            
        Returns:
            创建后的用户记录
        """
        import traceback
        try:
            hashed_pwd = get_password_hash(obj_in.get("password"))
            
            # 记录详细的输入参数
            logger = get_logger(__name__)
            logger.info(f"创建用户输入: {obj_in}")
            
            # 创建用户对象
            db_obj = User()
            
            # 逐个设置属性并记录
            try:
                db_obj.username = obj_in.get("username")
                logger.info("设置username成功")
            except Exception as e:
                logger.error(f"设置username失败: {str(e)}")
                
            try:
                db_obj.email = obj_in.get("email")
                logger.info("设置email成功")
            except Exception as e:
                logger.error(f"设置email失败: {str(e)}")
                
            try:
                db_obj.password = hashed_pwd
                logger.info("设置password成功")
            except Exception as e:
                logger.error(f"设置password失败: {str(e)}")
                
            try:
                # 设置为普通用户
                db_obj.status = "active"  # 设置状态而非is_active
                logger.info("设置status成功")
            except Exception as e:
                logger.error(f"设置status失败: {str(e)}")
                
            try:
                db_obj.is_admin = False   # 默认非管理员
                logger.info("设置is_admin成功")
            except Exception as e:
                logger.error(f"设置is_admin失败: {str(e)}")
            
            try:
                db.add(db_obj)
                logger.info("添加到会话成功")
            except Exception as e:
                logger.error(f"添加到会话失败: {str(e)}")
            
            try:
                await db.commit()
                logger.info("提交事务成功")
            except Exception as e:
                logger.error(f"提交事务失败: {str(e)}")
                await db.rollback()
                raise
            
            try:
                await db.refresh(db_obj)
                logger.info("刷新对象成功")
            except Exception as e:
                logger.error(f"刷新对象失败: {str(e)}")
                
            return db_obj
        except Exception as e:
            # 添加详细错误日志，包含堆栈跟踪
            logger.error(f"创建用户全局异常: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            raise
    
    # 添加创建用户的方法
    def create_user_sync(self, db: Session, *, obj_in: Dict[str, Any]) -> User:
        """
        创建用户
        
        Args:
            db: 数据库会话
            obj_in: 用户数据
            
        Returns:
            创建后的用户记录
        """
        try:
            hashed_pwd = get_password_hash(obj_in.get("password"))
            
            # 创建用户对象
            db_obj = User()
            db_obj.username = obj_in.get("username")
            db_obj.email = obj_in.get("email")
            db_obj.password = hashed_pwd
            # 设置为普通用户
            db_obj.status = "active"  # 设置状态而非is_active
            db_obj.is_admin = False   # 默认非管理员
            
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            # 添加详细错误日志
            logger = get_logger(__name__)
            logger.error(f"创建用户失败: {str(e)}", exc_info=True)
            raise
    
    async def is_active(self, user: User) -> bool:
        """
        检查用户是否活跃
        
        Args:
            user: 用户记录
            
        Returns:
            是否活跃
        """
        return user.is_active
    
    async def is_superuser(self, user: User) -> bool:
        """
        检查用户是否为超级用户
        
        Args:
            user: 用户记录
            
        Returns:
            是否为超级用户
        """
        return user.is_superuser

    async def authenticate(self, db: AsyncSession, *, username: str, password: str) -> Optional[User]:
        """
        验证用户名和密码
        
        Args:
            db: 数据库会话
            username: 用户名
            password: 密码
            
        Returns:
            验证成功的用户或None
        """
        from app.core.security import verify_password
        
        # 尝试通过用户名查找用户
        user = await self.get_by_username(db, username=username)
        if not user:
            # 尝试通过邮箱查找用户
            user = await self.get_by_email(db, email=username)
            if not user:
                return None
                
        # 验证密码
        if not verify_password(password, user.password):
            return None
            
        return user


# 其他CRUD操作
from app.db.models import (
    Role, SystemConfig, OperationLog, Product, Order, AIQueryLog
)

# 注意：CRUD实例创建移至文件末尾

# AI查询日志CRUD操作
logger = get_logger(__name__)

class CRUDAIQueryLog(CRUDBase[AIQueryLog, CreateSchemaType, UpdateSchemaType]):
    """AI查询日志CRUD操作类"""
    
    async def create_log(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[int],
        query_type: str,
        query_text: str,
        model_used: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        response_text: Optional[str] = None,
        status: str = "success",
        processing_time: Optional[float] = None,
        meta_info: Optional[Dict[str, Any]] = None
    ) -> AIQueryLog:
        """
        创建AI查询日志记录
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            query_type: 查询类型
            query_text: 查询文本
            model_used: 使用的模型
            prompt_tokens: 提示tokens
            completion_tokens: 完成tokens
            response_text: 响应文本
            status: 状态
            processing_time: 处理时间
            meta_info: 元数据
            
        Returns:
            创建的日志记录
        """
        logger.debug(f"创建AI查询日志: {query_type} - {query_text[:30]}...")
        
        try:
            obj_in_data = {
                "user_id": user_id,
                "query_type": query_type,
                "query_text": query_text,
                "model_used": model_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "response_text": response_text,
                "status": status,
                "processing_time": processing_time,
                "meta_info": meta_info or {}
            }
            
            db_obj = AIQueryLog(**obj_in_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"成功创建AI查询日志, ID: {db_obj.id}")
            return db_obj
        except Exception as e:
            logger.error(f"创建AI查询日志失败: {str(e)}")
            await db.rollback()
            raise
    
    async def get_user_query_history(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[int] = None,
        query_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[AIQueryLog]:
        """
        获取用户的查询历史
        
        Args:
            db: 数据库会话
            user_id: 用户ID (可选，如果不提供则获取所有用户的查询)
            query_type: 查询类型 (可选)
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            查询历史记录列表
        """
        logger.debug(f"获取用户查询历史: user_id={user_id}, type={query_type}, limit={limit}")
        
        # 构建查询条件
        query = select(AIQueryLog).order_by(AIQueryLog.created_at.desc())
        
        if user_id is not None:
            query = query.where(AIQueryLog.user_id == user_id)
            
        if query_type is not None:
            query = query.where(AIQueryLog.query_type == query_type)
            
        # 应用分页
        query = query.offset(offset).limit(limit)
        
        # 执行查询
        result = await db.execute(query)
        logs = result.scalars().all()
        
        logger.info(f"成功获取查询历史，返回 {len(logs)} 条记录")
        return logs


# 创建CRUD实例 - 统一在文件末尾创建所有实例
user = CRUDUser(User)
role = CRUDBase(Role)
system_config = CRUDBase(SystemConfig)
operation_log = CRUDBase(OperationLog)
product = CRUDBase(Product)
order = CRUDBase(Order)
ai_query_log = CRUDAIQueryLog(AIQueryLog) 
