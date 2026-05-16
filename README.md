# AI赋能的智能简历分析系统 + RAG AI

本项目包含两个核心功能：
1. **智能简历分析系统** - 自动解析PDF简历，提取关键信息，并与岗位需求进行匹配度分析
2. **RAG AI** - 基于本地文档进行问答（LangChain + OpenAI + MCP + FastAPI）

## 智能简历分析系统

### 功能特性

- **简历上传与解析**：支持PDF格式简历，兼容多页简历，自动提取文本
- **关键信息提取**：利用AI模型提取姓名、电话、邮箱、地址、求职意向、期望薪资、工作年限、学历背景、项目经历等
- **简历评分与匹配**：接收岗位需求描述，计算匹配度评分（技能匹配率、工作经验相关性、学历匹配等）
- **结果展示**：结构化展示提取的信息和匹配度评分
- **缓存机制**：对已解析和评分的简历进行缓存，避免重复计算

### 技术架构

- **后端**：FastAPI + Python
- **AI模型**：OpenAI API (gpt-3.5/4)
- **PDF解析**：PyPDFLoader (LangChain)
- **前端**：HTML + CSS + JavaScript

### 快速开始

1. 安装依赖：
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. 配置环境变量（编辑 `.env`）：
```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-3.5-turbo
```

3. 启动服务：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. 访问简历分析页面：
- 本地访问：http://localhost:8000/resume
- API文档：http://localhost:8000/docs

### API接口

#### 简历分析接口
- **POST** `/resume/analyze`
  - 请求：上传PDF文件，可选岗位描述
  - 响应：结构化的简历信息和匹配度评分

## RAG AI (LangChain + OpenAI + MCP + FastAPI)

本项目是一个最小可用的 Python + LangChain RAG 示例（支持 MCP + 多用户 Web）：

- 读取 `data/docs/` 下的本地文档，构建向量数据库（Chroma 持久化）
- 用户提问时，基于相关文档内容进行总结并生成回答（OpenAI API）
- 提供 **MCP Server**（Model Context Protocol）把“文档检索”以 MCP 工具暴露出去
- 提供 **FastAPI Web 服务**：多用户注册/登录（账号密码），每个用户的对话互不干扰（按用户隔离会话与消息）

## 1) 环境准备

1. 安装 Python 3.11+（推荐 3.11/3.12）
2. 在项目根目录创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量（推荐使用 `.env`）：

```bash
copy .env.example .env
```

编辑 `.env`，至少设置：

- `OPENAI_API_KEY=...`
- `OPENAI_BASE_URL=https://api.gptsapi.net/v1`（如需使用 OpenAI 兼容网关；默认已内置该值）

## 2) 放入本地文档

把你的文档放到 `data/docs/`（支持 `txt/md/pdf`）。

## 3) 构建向量库（首次或文档更新后）

```bash
python -m scripts.ingest
```

默认向量库目录：`data/chroma/`

## 4) 启动 Web 服务（多用户登录 + 提问）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

接口概览：

- `POST /auth/register` 注册
- `POST /auth/login` 登录（返回 JWT）
- `POST /chat/ask` 提问（Authorization: Bearer <token>）
- `GET /chat/conversations` 列出当前用户会话
- `GET /chat/conversations/{conversation_id}` 获取会话消息

## 5) 启动 MCP Server（可选但本项目已实现并可被外部 MCP 客户端调用）

```bash
python -m app.mcp_server
```



提示：

- SQLite 数据库默认在 `data/app.db`。
- 账号密码使用 bcrypt 哈希存储。

## 6) Railway 一键部署（公开演示）

本仓库已提供：

- `Dockerfile`
- `railway.toml`
- `.dockerignore`

部署步骤：

1. 将代码推送到 GitHub。
2. Railway 新建项目并选择该仓库。
3. Railway 服务里添加以下环境变量（不要提交到仓库）：
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_CHAT_MODEL`
   - `OPENAI_EMBED_MODEL`
   - `JWT_SECRET`
   - `JWT_EXPIRE_MINUTES`
   - `DOCS_DIR=data/docs`
   - `CHROMA_DIR=data/chroma`
   - `SQLITE_PATH=data/app.db`
4. 在 Railway 给服务添加 Volume，并挂载到 `/app/data`。
5. 部署完成后在 Railway 里点击 `Generate Domain` 获取公网地址。
6. 打开公网地址，登录后上传文档并点击“构建向量库”。

## 7) Docker 打包与分发

已提供 `Dockerfile` 与 `docker-compose.yml`。  
完整步骤见：[DEPLOY_DOCKER.md](DEPLOY_DOCKER.md)

## 8) 前端 GitHub Pages + 后端 Railway

本仓库已支持“前端静态托管到 GitHub Pages，后端 API 部署到 Railway”的拆分部署。

### 8.1 先部署 Railway 后端

1. 按“6) Railway 一键部署”完成后端部署。
2. 在 Railway 环境变量中新增：
   - `CORS_ALLOW_ORIGINS=https://<你的GitHub用户名>.github.io`
   - 如果你用项目页（不是用户主页），可追加逗号分隔，例如  
     `CORS_ALLOW_ORIGINS=https://<你的GitHub用户名>.github.io,https://<你的GitHub用户名>.github.io/<仓库名>`

### 8.2 生成 GitHub Pages 静态站

在仓库根目录运行：

```bash
node scripts/make_pages.cjs
```

会生成 `docs/` 目录（可直接作为 GitHub Pages Source）。

然后编辑：

- `docs/config.js`
- 设置 `window.RAG_API_BASE='https://<你的Railway域名>'`

### 8.3 发布 GitHub Pages

1. 提交并推送代码到 GitHub。
2. 仓库 `Settings -> Pages`。
3. Source 选择 `Deploy from a branch`。
4. Branch 选择 `main`，Folder 选择 `/docs`，保存。
5. 访问 `https://<your-username>.github.io/<repo-name>/`。

## 简历分析系统部署

### Railway 后端部署

1. 按照上述 Railway 一键部署步骤完成后端部署。
2. 确保在环境变量中设置 `CORS_ALLOW_ORIGINS`，包含 GitHub Pages 域名。

### GitHub Pages 前端部署

1. 确保已运行 `node scripts/make_pages.cjs` 生成 docs 目录。
2. 编辑 `docs/config.js`，设置 `window.RAG_API_BASE` 为 Railway 后端地址。
3. 提交并推送到 GitHub。
4. 在仓库 Settings -> Pages 中启用 GitHub Pages。
5. 访问 `https://<your-username>.github.io/<repo-name>/resume.html` 使用简历分析功能。
