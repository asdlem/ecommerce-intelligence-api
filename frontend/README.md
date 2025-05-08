# 电商智能API前端项目

## 项目概述

本项目是电商智能API的前端界面，采用模仿谷歌风格的现代化设计。用户可通过自然语言提问的方式查询电商数据，系统将自动转换为SQL查询并返回结果。

## 目录结构

```
frontend/
  ├── public/              # 静态资源
  ├── src/
  │   ├── components/      # 公共组件
  │   ├── pages/           # 页面组件
  │   ├── services/        # API服务
  │   ├── utils/           # 工具函数
  │   ├── types/           # TypeScript类型定义
  │   ├── App.tsx          # 应用入口
  │   ├── index.tsx        # 渲染入口
  │   └── index.css        # 全局样式
  ├── package.json         # 项目依赖
  └── tsconfig.json        # TypeScript配置
```

## 开发规范

### 代码风格

- 使用TypeScript进行开发，确保类型安全
- 遵循函数式组件和Hooks的React编写方式
- 使用ES6+语法特性
- 文件命名采用PascalCase (组件) 或 camelCase (非组件)

### UI设计规范

- 采用Google风格配色方案：
  - 主色调: #4285F4 (蓝色)
  - 辅助色: #34A853 (绿色), #FBBC05 (黄色), #EA4335 (红色)
- 圆角设计和卡片式布局
- 响应式设计，适配不同屏幕尺寸
- Material UI组件库作为基础UI框架

### 文件组织

- 组件应尽可能小且专注于单一职责
- 共享组件放在`components`目录
- 页面级组件放在`pages`目录
- API调用封装在`services`目录
- 类型定义放在`types`目录
- 工具函数和通用逻辑放在`utils`目录

### 样式约定

- 使用Material UI的`sx`属性进行样式定义
- 复杂组件可使用`styled`API创建样式化组件
- 避免使用内联样式
- 使用主题变量确保样式一致性

### Git提交规范

- 使用语义化的提交信息
- 前缀使用：feat, fix, docs, style, refactor, test, chore
- 示例: `feat: 添加用户登录页面` 或 `fix: 修复查询结果展示问题`

## 启动项目

### 安装依赖

```powershell
# 确保在frontend目录下运行
cd frontend
npm install
```

### 开发模式启动

```powershell
npm start
```

应用将在 http://localhost:3000 启动。

### 生产构建

```powershell
npm run build
```

构建文件将生成在 `build` 目录下。

## 后端API接口文档

### 基础信息

- 基础URL: `http://localhost:8000/api`
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

### Windows开发注意事项

- 在Windows系统中开发时，请使用PowerShell运行命令
- 确保在frontend目录下运行npm命令，不要在项目根目录运行
- 使用正向斜杠(/)而非反斜杠(\\)表示路径，以避免转义问题

## 常见问题

### Q: 组件样式不正确怎么办？
A: 检查是否正确使用了Material UI v7的新API，特别是Grid组件的变化。

### Q: API请求失败怎么办？
A: 确保后端服务已启动，且API基础URL配置正确。检查认证token是否正确设置。

### Q: 如何添加新页面？
A: 在pages目录下创建新组件，然后在routes.tsx中添加路由配置。
