#!/usr/bin/env python
"""
API测试脚本

用于测试电商智能API接口，包括完整用户流程：注册、登录、数据查询等功能。
自动测试所有API端点并生成测试报告。

用法:
    python test_api_simple.py [--base-url URL]

参数:
    --base-url: API基础URL，默认为http://localhost:8000/api/v1
"""

import sys
import requests
import json
import random
import argparse
from typing import Dict, Any, Optional, Tuple
import time

# 默认API基础URL
DEFAULT_BASE_URL = "http://localhost:8000/api/v1"

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="电商智能API测试脚本")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                      help=f"API基础URL (默认: {DEFAULT_BASE_URL})")
    args = parser.parse_args()
    
    # 验证URL格式
    if not args.base_url.startswith("http"):
        print(f"警告: URL '{args.base_url}' 不包含协议，可能不正确")
    
    return args

# 全局变量
args = parse_args()
BASE_URL = args.base_url

def login(username: str, password: str) -> Optional[str]:
    """登录并获取令牌
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        令牌字符串，登录失败则返回None
    """
    print(f"正在登录用户: {username}...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login", 
            data={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"登录成功: {token[:15]}...{token[-5:] if len(token) > 20 else ''}")
            return token
        else:
            print(f"登录失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    except Exception as e:
        print(f"登录出错: {e}")
        return None

def test_register() -> Optional[Tuple[str, str]]:
    """测试用户注册接口
    
    Returns:
        成功时返回(用户名, 密码)元组，失败则返回None
    """
    print("\n=== 测试用户注册 ===")
    
    # 生成随机用户名和邮箱以避免冲突
    random_suffix = f"{random.randint(1000, 9999)}"
    username = f"testuser{random_suffix}"
    email = f"test{random_suffix}@example.com"
    password = "Password123!"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        
        if response.status_code == 200:
            print(f"用户注册成功: {username}")
            return (username, password)
        else:
            print(f"用户注册失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    except Exception as e:
        print(f"注册测试出错: {e}")
        return None

def test_get_user_info(token: str) -> bool:
    """测试获取当前用户信息
    
    Args:
        token: 用户认证令牌
        
    Returns:
        测试是否成功
    """
    print("\n=== 测试获取用户信息 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=headers
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"获取用户信息成功: {user_info.get('username')}")
            if "username" in user_info and "email" in user_info:
                print(f"用户名: {user_info['username']}, 邮箱: {user_info['email']}")
                return True
            else:
                print("响应格式异常，缺少用户信息")
                return False
        else:
            print(f"获取用户信息失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"获取用户信息出错: {e}")
        return False

def test_nl2sql(token: str) -> bool:
    """测试自然语言转SQL接口
    
    将自然语言查询转换为SQL语句并获取查询建议
    
    Args:
        token: 用户认证令牌
        
    Returns:
        测试是否成功
    """
    print("\n=== 测试自然语言转SQL ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    query = "销量最高的3个产品是什么？"
    
    try:
        response = requests.post(
            f"{BASE_URL}/data/nl2sql",
            headers=headers,
            json={"query": query}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and "sql" in result:
                print(f"生成SQL成功: {result['sql'][:100]}...")
                
                # 检查是否返回了建议
                if "suggestions" in result and isinstance(result["suggestions"], list):
                    suggestion_count = len(result["suggestions"])
                    print(f"获取 {suggestion_count} 条查询建议")
                    if suggestion_count > 0:
                        print(f"建议示例: {result['suggestions'][0][:50]}...")
                    return True
                else:
                    print("未返回查询建议")
                    return False
            else:
                print(f"生成SQL失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"NL2SQL测试出错: {e}")
        return False

def test_nl2sql_query(token: str) -> bool:
    """测试自然语言查询执行接口
    
    将自然语言查询转换为SQL并执行，获取结果、建议和可视化配置
    
    Args:
        token: 用户认证令牌
        
    Returns:
        测试是否成功
    """
    print("\n=== 测试自然语言查询执行 ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    query = "销量最高的3个产品是什么？"
    
    try:
        response = requests.post(
            f"{BASE_URL}/data/nl2sql-query",
            headers=headers,
            json={
                "query": query,
                "need_visualization": True,
                "include_suggestions": True
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"查询执行成功: {query}")
            if "data" in result:
                data = result["data"]
                
                # 检查SQL生成
                if "sql" in data:
                    print(f"生成的SQL: {data['sql'][:100]}...")
                
                # 检查查询结果
                if "results" in data and data["results"]:
                    print(f"结果数量: {len(data['results'])}")
                    print(f"结果示例: {data['results'][0] if data['results'] else '无结果'}")
                else:
                    print("查询无结果或结果字段缺失")
                
                # 检查解释
                if "explanation" in data and data["explanation"]:
                    print(f"结果解释: {data['explanation'][:100]}...")
                
                # 检查建议
                if "suggestions" in data and isinstance(data["suggestions"], list):
                    print(f"建议数量: {len(data['suggestions'])}")
                    for i, suggestion in enumerate(data["suggestions"][:2], 1):
                        print(f"  建议{i}: {suggestion[:50]}...")
                
                # 检查可视化配置
                if "visualization" in data and data["visualization"]:
                    print("包含可视化配置")
                
                return True
            else:
                print("响应中缺少数据字段")
                return False
        else:
            print(f"查询执行失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"查询执行出错: {e}")
        return False

def test_get_tables(token: str) -> bool:
    """测试获取数据库表列表
    
    Args:
        token: 用户认证令牌
        
    Returns:
        测试是否成功
    """
    print("\n=== 测试获取数据库表 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/data/tables",
            headers=headers
        )
        
        print(f"表接口响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"接口响应: {result}")
            
            # 检查响应结构 - 支持两种可能的格式
            tables = []
            if "tables" in result:
                # 使用旧的格式
                tables = result.get("tables", [])
            elif "data" in result and isinstance(result["data"], list):
                # 使用新的格式 - 'data' 字段包含表名
                tables = result["data"]
            else:
                print("错误: 响应中既没有 'tables' 也没有 'data' 字段")
                return False
                
            print(f"获取到 {len(tables)} 个数据库表")
            
            if tables:
                # 显示前5个表
                for i, table in enumerate(tables[:5], 1):
                    print(f"  表{i}: {table}")
                if len(tables) > 5:
                    print(f"  ... 以及 {len(tables) - 5} 个其他表")
                return True
            else:
                print("未获取到任何表信息，请检查:")
                print("  1. 数据库中是否有表")
                print("  2. 用户是否有访问数据库表的权限")
                print("  3. API实现是否正确返回表信息")
                return False
        else:
            print(f"获取表失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"获取表出错: {e}")
        print(f"异常类型: {type(e).__name__}")
        if hasattr(e, "__traceback__"):
            import traceback
            print(f"堆栈跟踪: {traceback.format_exc()}")
        return False

def test_query_history(token: str) -> bool:
    """测试获取查询历史
    
    获取用户历史查询记录
    
    Args:
        token: 用户认证令牌
        
    Returns:
        测试是否成功
    """
    print("\n=== 测试获取查询历史 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/data/history",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            history = result.get("history", [])
            print(f"获取到 {len(history)} 条历史查询记录")
            
            if history:
                # 显示前3条历史记录
                for i, record in enumerate(history[:3], 1):
                    query = record.get("query", "未知查询")
                    timestamp = record.get("timestamp", "未知时间")
                    print(f"  记录{i}: {query[:30]}... ({timestamp})")
                if len(history) > 3:
                    print(f"  ... 以及 {len(history) - 3} 条其他记录")
                return True
            else:
                print("没有历史查询记录")
                # 这不应该被视为测试失败，因为新用户可能没有历史记录
                return True
        else:
            print(f"获取历史记录失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"获取历史记录出错: {e}")
        return False

def main():
    """
    主测试流程
    
    按顺序执行所有测试步骤，并统计测试结果
    """
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"\n=== 开始API测试 (时间: {now}) ===")
    print(f"API基础URL: {BASE_URL}")
    start_time = time.time()
    
    # 测试结果跟踪
    results = {}
    
    try:
        # 步骤1: 注册新用户
        print("\n步骤1: 注册新用户")
        user_credentials = test_register()
        results["register"] = user_credentials is not None
        
        if not user_credentials:
            print("注册失败，测试中断")
            return summarize_results(results, start_time)
        
        username, password = user_credentials
        
        # 步骤2: 使用新用户登录
        print("\n步骤2: 新用户登录")
        token = login(username=username, password=password)
        results["login"] = token is not None
        
        if not token:
            print("登录失败，测试中断")
            return summarize_results(results, start_time)
        
        # 步骤3: 测试获取用户信息
        results["get_user_info"] = test_get_user_info(token)
        
        # 步骤4: 测试数据库表列表
        results["get_tables"] = test_get_tables(token)
        
        # 步骤5: 测试自然语言转SQL及建议
        results["nl2sql_with_suggestions"] = test_nl2sql(token)
        
        # 步骤6: 测试执行自然语言查询
        results["nl2sql_query"] = test_nl2sql_query(token)
        
        # 步骤7: 测试查询历史
        results["query_history"] = test_query_history(token)
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生未预期的错误: {e}")
    
    # 总结测试结果
    return summarize_results(results, start_time)

def summarize_results(results, start_time):
    """
    总结测试结果
    
    Args:
        results: 测试结果字典，键为测试名称，值为测试是否通过
        start_time: 测试开始时间戳
        
    Returns:
        整体测试是否成功
    """
    end_time = time.time()
    elapsed = end_time - start_time
    end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
    success_count = sum(1 for result in results.values() if result)
    total_tests = len(results)
    
    print("\n" + "="*60)
    print(" 测试结果摘要 ".center(58, "="))
    print("="*60)
    
    # 测试名称映射，使输出更友好
    test_name_map = {
        "register": "用户注册",
        "login": "用户登录",
        "get_user_info": "获取用户信息",
        "get_tables": "获取数据库表",
        "nl2sql_with_suggestions": "自然语言转SQL及建议",
        "nl2sql_query": "自然语言查询执行",
        "query_history": "查询历史获取"
    }
    
    # 按测试流程顺序输出结果
    for test_key, passed in results.items():
        test_name = test_name_map.get(test_key, test_key.replace('_', ' ').title())
        status = "✓ 通过" if passed else "✗ 失败"
        status_color = "\033[92m" if passed else "\033[91m"  # 绿色或红色
        print(f"  {test_name.ljust(25)} | {status_color}{status}\033[0m")
    
    # 计算和显示成功率
    success_rate = success_count / total_tests * 100 if total_tests > 0 else 0
    print("\n" + "-"*60)
    
    # 根据成功率确定颜色：绿色(>=90%)，黄色(>=70%)，红色(<70%)
    rate_color = "\033[92m" if success_rate >= 90 else "\033[93m" if success_rate >= 70 else "\033[91m"
    
    print(f"  总测试数: {total_tests}")
    print(f"  通过测试: {success_count}")
    print(f"  失败测试: {total_tests - success_count}")
    print(f"  测试成功率: {rate_color}{success_rate:.1f}%\033[0m")
    print(f"  测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    print(f"  测试结束时间: {end_time_str}")
    print(f"  测试用时: {elapsed:.2f} 秒")
    print("-"*60)
    
    if success_rate == 100:
        print("\n\033[92m所有测试通过！API功能正常。\033[0m")
    elif success_rate >= 80:
        print("\n\033[93m大部分测试通过，但有一些问题需要解决。\033[0m")
    else:
        print("\n\033[91m测试失败率较高，API可能存在严重问题。\033[0m")
    
    return success_rate == 100

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 