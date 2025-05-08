"""数据库模型定义

使用SQLAlchemy ORM定义的数据库模型，包括用户、商品、订单、类别等核心表结构。
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, JSON, Float, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.db.session import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="邮箱")
    password = Column(String(100), nullable=False, comment="哈希密码")
    phone = Column(String(20), nullable=True, comment="手机号")
    registration_date = Column(DateTime, default=datetime.utcnow, comment="注册日期")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    status = Column(String(20), default="active", comment="账户状态")
    is_admin = Column(Boolean, default=False, comment="是否为管理员")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    ai_query_logs = relationship("AIQueryLog", back_populates="user")
    
    # 兼容性属性
    @property
    def is_active(self) -> bool:
        """兼容性属性，根据status判断用户是否活跃"""
        return self.status == "active"

    @property
    def is_superuser(self) -> bool:
        """兼容性属性，管理员即为超级用户"""
        return self.is_admin


class Category(Base):
    """产品类别表"""
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="类别名称")
    parent_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True, comment="父类别ID")
    description = Column(Text, nullable=True, comment="类别描述")
    
    # 关系
    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[category_id], backref="subcategories")


class Product(Base):
    """产品表"""
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="产品名称")
    description = Column(Text, nullable=True, comment="产品描述")
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True, comment="类别ID")
    price = Column(Numeric(10, 2), nullable=False, comment="价格")
    cost = Column(Numeric(10, 2), nullable=True, comment="成本")
    inventory = Column(Integer, default=0, comment="库存数量")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    status = Column(String(20), default="active", comment="状态")
    
    # 关系
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    inventory_history = relationship("InventoryHistory", back_populates="product")
    returns = relationship("Return", back_populates="product")


class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    order_date = Column(DateTime, default=datetime.utcnow, comment="订单日期")
    total_amount = Column(Numeric(12, 2), nullable=False, comment="订单总金额")
    status = Column(String(20), default="pending", comment="订单状态")
    shipping_address = Column(Text, nullable=True, comment="配送地址")
    payment_method = Column(String(50), nullable=True, comment="支付方式")
    
    # 关系
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    returns = relationship("Return", back_populates="order")


class OrderItem(Base):
    """订单项表"""
    __tablename__ = "order_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, comment="订单ID")
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, comment="产品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(10, 2), nullable=False, comment="单价")
    discount = Column(Numeric(10, 2), default=0, comment="折扣")
    subtotal = Column(Numeric(10, 2), nullable=False, comment="小计")
    
    # 关系
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Review(Base):
    """评价表"""
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=True, comment="产品ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    rating = Column(Integer, nullable=True, comment="评分")
    comment = Column(Text, nullable=True, comment="评论内容")
    review_date = Column(DateTime, default=datetime.utcnow, comment="评价日期")
    helpful_votes = Column(Integer, default=0, comment="有用票数")
    
    # 关系
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class InventoryHistory(Base):
    """库存历史表"""
    __tablename__ = "inventory_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, comment="产品ID")
    change_amount = Column(Integer, nullable=False, comment="变动数量")
    change_date = Column(DateTime, default=datetime.utcnow, comment="变动日期")
    reason = Column(String(100), nullable=True, comment="变动原因")
    operator = Column(String(50), nullable=True, comment="操作员")
    
    # 关系
    product = relationship("Product", back_populates="inventory_history")


class Promotion(Base):
    """促销活动表"""
    __tablename__ = "promotions"

    promotion_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="活动名称")
    description = Column(Text, nullable=True, comment="活动描述")
    discount_type = Column(String(20), nullable=False, comment="折扣类型")
    discount_value = Column(Numeric(10, 2), nullable=False, comment="折扣值")
    start_date = Column(DateTime, nullable=False, comment="开始日期")
    end_date = Column(DateTime, nullable=True, comment="结束日期")
    active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class Return(Base):
    """退货表"""
    __tablename__ = "returns"

    return_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, comment="订单ID")
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, comment="产品ID")
    return_date = Column(DateTime, default=datetime.utcnow, comment="退货日期")
    quantity = Column(Integer, nullable=False, comment="数量")
    reason = Column(Text, nullable=True, comment="退货原因")
    status = Column(String(20), default="pending", comment="状态")
    refund_amount = Column(Numeric(10, 2), nullable=True, comment="退款金额")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    order = relationship("Order", back_populates="returns")
    product = relationship("Product", back_populates="returns")


class Supplier(Base):
    """供应商表"""
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="供应商名称")
    contact_person = Column(String(50), nullable=True, comment="联系人")
    email = Column(String(100), nullable=True, comment="电子邮件")
    phone = Column(String(20), nullable=True, comment="电话")
    address = Column(Text, nullable=True, comment="地址")
    status = Column(String(20), default="active", comment="状态")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


# 以下是系统功能相关表，保留用于系统运行

class Role(Base):
    """角色模型"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色名称")
    description = Column(String(200), nullable=True, comment="角色描述")
    permissions = Column(JSON, nullable=True, comment="权限JSON")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class UserRole(Base):
    """用户角色关系表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID")
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), comment="角色ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(Text, nullable=True, comment="配置值")
    description = Column(String(200), nullable=True, comment="配置描述")
    is_encrypted = Column(Boolean, default=False, comment="是否加密")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    operation_type = Column(String(50), nullable=False, comment="操作类型")
    resource_type = Column(String(50), nullable=True, comment="资源类型")
    resource_id = Column(String(50), nullable=True, comment="资源ID")
    details = Column(JSON, nullable=True, comment="操作详情")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    status = Column(String(20), nullable=False, default="success", comment="操作状态")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class AIQueryLog(Base):
    """AI查询日志表"""
    __tablename__ = "ai_query_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    query_type = Column(String(50), nullable=False, comment="查询类型")
    query_text = Column(Text, nullable=False, comment="查询文本")
    model_used = Column(String(100), nullable=True, comment="使用的模型")
    prompt_tokens = Column(Integer, nullable=True, comment="提示token数量")
    completion_tokens = Column(Integer, nullable=True, comment="完成token数量")
    response_text = Column(Text, nullable=True, comment="响应文本")
    status = Column(String(20), nullable=False, default="success", comment="查询状态")
    processing_time = Column(Float, nullable=True, comment="处理时间")
    meta_info = Column(JSON, nullable=True, comment="元信息")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关联关系
    user = relationship("User", back_populates="ai_query_logs") 