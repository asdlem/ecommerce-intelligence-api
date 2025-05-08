#!/usr/bin/env python
"""
后端服务器启动脚本

提供后端API服务器的启动功能，支持开发和生产环境配置。
"""

import os
import sys
import argparse
import platform
import subprocess
import dotenv
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.absolute()

def load_env_file(env_file=None):
    """加载环境变量文件
    
    Args:
        env_file: 环境变量文件路径，如果为None则自动查找.env文件
    """
    if env_file is None:
        env_file = os.path.join(get_project_root(), ".env")
    
    # 如果文件存在则加载环境变量
    if os.path.exists(env_file):
        print(f"正在加载环境变量文件: {env_file}")
        dotenv.load_dotenv(env_file)
        return True
    else:
        print(f"警告: 环境变量文件 {env_file} 不存在")
        return False

def run_server(host="0.0.0.0", port=8000, reload=True, workers=1, log_level="info", env_file=None):
    """启动后端服务器
    
    Args:
        host: 服务器主机
        port: 服务器端口
        reload: 是否自动重载代码
        workers: 工作进程数
        log_level: 日志级别
        env_file: 环境变量文件路径
    """
    # 加载环境变量
    load_env_file(env_file)
    
    # 切换到backend目录
    backend_dir = os.path.join(get_project_root(), "backend")
    os.chdir(backend_dir)
    print(f"当前工作目录: {os.getcwd()}")
    
    # 构建Uvicorn命令
    cmd = [
        "uvicorn", 
        "app.main:app", 
        "--host", host, 
        "--port", str(port), 
        "--log-level", log_level
    ]
    
    if reload:
        cmd.append("--reload")
    
    if workers > 1 and not reload:  # reload模式不支持多workers
        cmd.extend(["--workers", str(workers)])
    
    print(f"启动命令: {' '.join(cmd)}")
    
    try:
        # 执行命令
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"启动服务器出错: {e}")
        return e.returncode
    except KeyboardInterrupt:
        print("服务器已停止")
        return 0
    except Exception as e:
        print(f"发生意外错误: {e}")
        return 1

if __name__ == "__main__":
    print("=== API服务器启动工具 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="启动后端API服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="禁用代码自动重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    parser.add_argument("--log-level", default="info", 
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="日志级别 (默认: info)")
    parser.add_argument("--production", action="store_true", 
                       help="生产模式 (禁用重载, 启用多工作进程)")
    parser.add_argument("--env-file", help="指定环境变量文件路径")
    
    args = parser.parse_args()
    
    # 处理生产模式
    if args.production:
        args.no_reload = True
        if args.workers == 1:
            args.workers = min(os.cpu_count() or 1, 4)  # 默认使用CPU核心数或最大4个
    
    # 运行服务器
    sys.exit(run_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        workers=args.workers,
        log_level=args.log_level,
        env_file=args.env_file
    )) 