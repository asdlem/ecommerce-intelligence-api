# 电商智能API项目

## 项目概述

本项目是一个电商智能API系统，包含前端和后端两部分。用户可以通过自然语言提问的方式查询电商数据，系统会自动将自然语言转换为SQL查询并返回结果。前端采用模仿谷歌风格的现代化设计。

### 主要功能

- 用户认证（注册、登录）
- 自然语言转SQL查询
- 数据可视化展示
- 历史查询记录
- 智能推荐和建议

### 技术栈

- **前端**：React + TypeScript + Material UI v7
- **后端**：Python + FastAPI
- **数据库**：PostgreSQL

### 最近优化

- **流式解释生成**: 实现解释生成的流式输出功能，使用户可以看到解释内容逐步生成，提升交互体验
- **用户界面优化**: 移动解释按钮至结果表格下方，更符合用户操作逻辑；解决解释生成过程中页面滚动限制问题
- **性能优化**: 将SQL查询与解释生成分离，大幅提高查询响应速度
- **用户体验**: 添加了按需加载解释功能，让用户可以自行决定是否需要详细解释
- **防阻塞**: 增加API超时时间至60秒，解决长时间查询的超时问题
- **界面简化**: 移除多余的执行SQL按钮，简化用户操作流程
- **查询流程优化**: 优化流程为"查询→立即显示结果→按需解释"的模式

## 目录结构

```
project/
  ├── frontend/           # 前端代码
  │   ├── public/         # 静态资源
  │   ├── src/            # 源代码
  │   └── package.json    # 依赖配置
  ├── backend/            # 后端代码
  │   ├── app/            # 应用代码
  │   └── requirements.txt # 依赖配置
  ├── scripts/            # 辅助脚本
  ├── docs/               # 文档
  └── tests/              # 测试
```

## 开发规范

### 前端开发规范

#### 代码风格

- 使用TypeScript进行开发，确保类型安全
- 遵循函数式组件和Hooks的React编写方式
- 使用ES6+语法特性
- 文件命名采用PascalCase (组件) 或 camelCase (非组件)

#### UI设计规范

- 采用Google风格配色方案：
  - 主色调: #4285F4 (蓝色)
  - 辅助色: #34A853 (绿色), #FBBC05 (黄色), #EA4335 (红色)
- 圆角设计和卡片式布局
- 响应式设计，适配不同屏幕尺寸
- Material UI组件库作为基础UI框架

#### 文件组织

- 组件应尽可能小且专注于单一职责
- 共享组件放在`components`目录
- 页面级组件放在`pages`目录
- API调用封装在`services`目录
- 类型定义放在`types`目录
- 工具函数和通用逻辑放在`utils`目录

### 后端开发规范

- 使用Python类型提示功能
- API路由采用RESTful设计规则
- 统一错误处理和响应格式
- 使用异步处理长时间运行的查询

### Git提交规范

- 使用语义化的提交信息
- 前缀使用：feat, fix, docs, style, refactor, test, chore
- 示例: `feat: 添加用户登录页面` 或 `fix: 修复查询结果展示问题`

## 安装与运行

### 前端

```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式启动
npm start
```

前端将在 http://localhost:3000 启动。

### 后端

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python start_server.py
```

后端API将在 http://localhost:8000 启动。

## 后端API接口文档

### 基础信息

- 基础URL: `http://localhost:8000/api/v1`
- 认证方式: Bearer Token

### 认证相关接口

#### 用户注册

- **URL**: `/auth/register`
- **方法**: POST
- **请求体**:
  ```json
  {
    "username": "string",
    "email": "string",
    "password": "string"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "string",
    "token_type": "string",
    "user": {
      "id": 0,
      "username": "string",
      "email": "string",
      "is_active": true
    }
  }
  ```

#### 用户登录

- **URL**: `/auth/login`
- **方法**: POST
- **请求体**: 表单数据 (application/x-www-form-urlencoded)
  ```
  username: string
  password: string
  ```
- **响应**:
  ```json
  {
    "access_token": "string",
    "token_type": "string",
    "user": {
      "id": 0,
      "username": "string",
      "email": "string",
      "is_active": true
    }
  }
  ```

#### 获取当前用户信息

- **URL**: `/auth/me`
- **方法**: GET
- **认证**: 需要Bearer Token
- **响应**:
  ```json
  {
    "id": 0,
    "username": "string",
    "email": "string",
    "is_active": true
  }
  ```

### 数据查询相关接口

#### 自然语言转SQL

- **URL**: `/data/nl2sql`
- **方法**: POST
- **认证**: 需要Bearer Token
- **请求体**:
  ```json
  {
    "query": "string"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "sql": "string",
      "suggestions": ["string"]
    }
  }
  ```

#### 执行自然语言查询

- **URL**: `/data/nl2sql-query`
- **方法**: POST
- **认证**: 需要Bearer Token
- **请求体**:
  ```json
  {
    "query": "string",
    "need_visualization": true,
    "include_suggestions": true
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "query": "string",
      "sql": "string",
      "results": [],
      "row_count": 0,
      "explanation": "string",
      "visualization": {
        "chart_type": "string",
        "x_field": "string",
        "y_field": "string",
        "series_field": "string",
        "config": {}
      },
      "suggestions": ["string"]
    },
    "total": 0
  }
  ```

#### 直接执行SQL查询

- **URL**: `/data/query`
- **方法**: POST
- **认证**: 需要Bearer Token
- **请求体**:
  ```json
  {
    "query": "string",
    "max_rows": 100
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": [],
    "total": 0
  }
  ```

#### 获取数据库表列表

- **URL**: `/data/tables`
- **方法**: GET
- **认证**: 需要Bearer Token
- **响应**:
  ```json
  {
    "success": true,
    "data": ["table1", "table2"],
    "total": 2
  }
  ```

#### 获取查询历史

- **URL**: `/data/history`
- **方法**: GET
- **认证**: 需要Bearer Token
- **查询参数**:
  ```
  limit: number (默认 10)
  offset: number (默认 0)
  query_type: string (可选)
  ```
- **响应**:
  ```json
  {
    "history": [
      {
        "id": 0,
        "query": "string",
        "query_type": "string",
        "timestamp": "string",
        "status": "string",
        "model": "string",
        "processing_time": 0
      }
    ]
  }
  ```

#### 清除查询缓存

- **URL**: `/data/cache`
- **方法**: DELETE
- **认证**: 需要Bearer Token
- **响应**:
  ```json
  {
    "success": true,
    "message": "Cache cleared successfully"
  }
  ```

## 注意事项

### Material UI v7 兼容性

本项目使用 Material UI v7，需要注意以下几点：

1. Grid组件变更：
   - v7中`Grid`组件使用`size`属性代替之前的`xs`、`sm`、`md`等属性
   - 示例: `<Grid size={{ xs: 12, sm: 6, md: 3 }}>`

2. 错误示例与正确示例对比:
   ```jsx
   // 错误示例 (v5/v6风格)
   <Grid item xs={12} sm={6} md={3}></Grid>
   
   // 正确示例 (v7风格)
   <Grid size={{ xs: 12, sm: 6, md: 3 }}></Grid>
   ```

### 常见问题排查

#### API请求问题

1. 确认后端服务是否正常运行
2. 检查API基础URL配置（应为`/api/v1`而非`/api`）
3. 验证认证令牌是否正确发送
4. 对于登录请求，确保使用正确的表单格式（URLSearchParams）
5. 使用浏览器开发者工具网络面板检查请求和响应

#### 前端组件渲染问题

1. 检查控制台是否有错误信息
2. 确认使用的是Material UI v7兼容的组件API
3. 验证数据结构是否与组件期望的格式一致

## 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 联系与支持

如有问题或建议，请提交Issue或联系项目维护者。

