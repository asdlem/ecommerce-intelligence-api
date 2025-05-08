from fastapi import APIRouter

# 创建API路由器
api_router = APIRouter()

# 导入并注册路由
from app.api.v1 import auth

# 尝试导入data_query，如果存在缩进错误或其他问题，将抛出明确的错误
try:
    from app.api.v1 import data_query
    api_router.include_router(data_query.router, prefix="/data", tags=["数据查询"])
    print("成功加载data_query模块")
except Exception as e:
    import traceback
    error_trace = traceback.format_exc()
    print(f"错误: 无法加载data_query模块: {str(e)}")
    print(f"错误详情:\n{error_trace}")
    
    # 尝试导入tables模块作为备用
    try:
        from app.api.v1 import tables
        api_router.include_router(tables.router, prefix="/data", tags=["数据查询(备用)"])
        print("成功加载tables备用模块 - 警告: 这不是完整实现")
    except Exception as e:
        print(f"严重错误: 无法加载tables备用模块: {str(e)}")
        # 不再静默失败，在这里抛出异常以明确问题
        raise Exception(f"数据查询模块加载失败: {str(e)}") from e

# 避免导入不存在的模块
try:
    from app.api.v1 import users
    api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
except ImportError as e:
    print(f"未找到users模块: {str(e)}")
except Exception as e:
    print(f"加载users模块时出错: {str(e)}")

try:
    from app.api.v1 import admin
    api_router.include_router(admin.router, prefix="/admin", tags=["管理员工具"])
except ImportError as e:
    print(f"未找到admin模块: {str(e)}")
except Exception as e:
    print(f"加载admin模块时出错: {str(e)}")

# 注册确定存在的路由
api_router.include_router(auth.router, prefix="/auth", tags=["身份认证"])

# 后续扩展:
# api_router.include_router(search.router, prefix="/search", tags=["智能搜索"])
# api_router.include_router(operations.router, prefix="/operations", tags=["快捷操作"])
# api_router.include_router(assistant.router, prefix="/assistant", tags=["智能助手"]) 