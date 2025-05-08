# 电商智能API

基于FastAPI的电商数据智能查询API，提供自然语言到SQL的转换、数据查询、结果解释和可视化建议。

## 功能特性

- **自然语言转SQL**：将用户自然语言问题转换为SQL查询语句
- **智能查询建议**：自动生成相关后续查询建议
- **数据库查询**：执行SQL查询并返回格式化结果
- **用户认证管理**：完整的用户注册、登录和权限控制
- **查询历史**：记录和获取历史查询

## 环境要求

- Python 3.8+
- MySQL 8.0+
- DeepSeek API Key (用于自然语言处理)

## 快速开始

### 1. 克隆项目

```powershell
git clone https://github.com/yourusername/ecommerce-api.git
cd ecommerce-api
```

### 2. 设置虚拟环境

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r backend/requirements.txt
```

### 3. 数据库配置

#### 方式一：使用Docker快速启动MySQL（推荐）

```powershell
# 启动MySQL容器
docker run --name mysql-ecommerce -e MYSQL_ROOT_PASSWORD=your_password -e MYSQL_DATABASE=agent_db -p 3306:3306 -d mysql:8.0

# 测试连接
docker exec -it mysql-ecommerce mysql -uroot -pyour_password -e "SHOW DATABASES;"
```

#### 方式二：使用本地MySQL

1. 确保已安装MySQL 8.0+
2. 创建数据库
```sql
CREATE DATABASE agent_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 系统配置

系统配置支持两种方式：环境变量（推荐）和配置文件。

#### 方式一：使用环境变量（推荐，更安全）

1. 在项目根目录复制`env.example`为`.env`文件：

```powershell
Copy-Item env.example .env
```

2. 编辑`.env`文件，修改相关配置：

```
# 数据库配置
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=agent_db

# AI模型API密钥
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# 管理员配置
ADMIN_PASSWORD=your_admin_password_here
```

#### 方式二：使用配置文件

编辑 `backend/config.json` 文件：

```json
{
  "project": {
    "name": "ECommerceEfficiencyAgent",
    "description": "通过AI能力为电商场景提供智能化功能的效率提升工具",
    "version": "0.1.0",
    "api_v1_str": "/api/v1"
  },
  "cors": {
    "origins": ["*"]
  },
  "database": {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "${DB_PASSWORD}",
    "db": "agent_db",
    "echo": false
  },
  "jwt": {
    "access_token_expire_minutes": 11520
  },
  "ai_models": {
    "default_ai_model": "deepseek",
    "enable_reasoning": true,
    "deepseek": {
      "api_key": "${DEEPSEEK_API_KEY}",
      "api_base": "https://api.deepseek.com",
      "model": "deepseek-chat",
      "http_referer": "https://agent.example.com",
      "x_title": "ECommerceEfficiencyAgent"
    }
  },
  "admin": {
    "initial_admin_password": "${ADMIN_PASSWORD}"
  }
}
```

⚠️ 注意：
- 配置文件中的`${ENV_VAR_NAME}`格式会自动替换为对应环境变量的值
- 生成安全的密钥: `python -c "import secrets; print(secrets.token_hex(32))"`
- 获取DeepSeek API密钥: https://platform.deepseek.com/
- **敏感信息**（如API密钥、密码）建议使用环境变量方式配置，不要直接写入配置文件，以防止意外泄露

### 5. 初始化数据库

直接使用MySQL客户端执行初始化SQL脚本：

```powershell
# 确保已创建数据库
mysql -h localhost -u root -p -e "CREATE DATABASE IF NOT EXISTS agent_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行初始化脚本
mysql -h localhost -u root -p agent_db < backend/app/db/init_db.sql
```

如果使用Docker方式部署的MySQL：

```powershell
# 确保已创建数据库
docker exec -it mysql-ecommerce mysql -uroot -pyour_password -e "CREATE DATABASE IF NOT EXISTS agent_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行初始化脚本
Get-Content backend/app/db/init_db.sql | docker exec -i mysql-ecommerce mysql -uroot -pyour_password agent_db
```

详细的数据库结构和初始化说明请参阅 [数据库配置文档](docs/数据库配置.md)。

### 6. 启动服务器

```powershell
# 开发模式启动
python start_server.py

# 使用指定环境变量文件启动
python start_server.py --env-file path/to/your/.env

# 或指定高级选项
python start_server.py --port 8080 --log-level debug

# 生产模式启动
python start_server.py --production
```

启动后访问: http://localhost:8000/docs

## 测试

运行自动化测试脚本：

```powershell
# 使用默认参数运行所有测试
python tests/test_api_simple.py

# 指定API基础URL
python tests/test_api_simple.py --base-url http://localhost:8000/api/v1
```

更多测试选项请查看测试脚本内的说明 [tests/test_api_simple.py](tests/test_api_simple.py)。

## 常见问题解决

### 数据库连接错误

如果遇到数据库连接错误，请检查：
- 数据库服务是否正常运行
- `.env`文件中的数据库配置是否正确
- MySQL用户是否有足够权限

```powershell
# 检查MySQL状态（Docker方式）
docker ps | findstr mysql-ecommerce
```

### API密钥相关问题

如果AI功能不可用，请确保：
- 已在`.env`文件中配置有效的API密钥
- 网络可以正常访问DeepSeek/OpenRouter API
- API密钥拥有足够的权限和配额

### 环境变量未生效

如果环境变量配置未生效，请尝试：

```powershell
# 检查环境变量是否正确加载
python -c "import os; print(os.environ.get('DEEPSEEK_API_KEY'))"

# 确保python-dotenv已安装
pip install python-dotenv
```

## 文档

完整文档请参考：

- [接口文档](docs/接口文档.md) - 详细API接口说明
- [系统文档](docs/系统文档.md) - 系统架构和技术栈
- [数据库配置](docs/数据库配置.md) - 数据库结构和初始化SQL
- [文档索引](docs/文档索引.md) - 所有可用文档列表

## 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL
- **ORM**：SQLAlchemy
- **认证**：JWT
- **自然语言处理**：DeepSeek API 

## 许可证

MIT
