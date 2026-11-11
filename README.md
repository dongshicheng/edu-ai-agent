# 多模态AI互动式教学智能体

这是一个面向教育场景的多模态 AI 互动式教学智能体，旨在帮助教师和学生在一个统一平台中完成知识问答、资料上传、内容理解与课程生成等工作。

通过自然语言交互、知识库检索和多类型文件处理能力，系统能够将教研内容、课程资料和学习问答连接起来，打造更智能、更沉浸式的教学体验。

## 产品定位

这是一个以“AI 教师助手”为核心的教育智能体产品，聚焦以下关键能力：

- 多轮对话式教学问答
- 多模态资料解析（PDF、DOCX、图片等）
- 知识库构建与检索增强
- 课程内容生成与课件输出
- 会话式教学交互与任务管理

它适用于课堂辅助、教案生成、学习支持、知识库问答和内容复用场景。

## 核心能力

### 1. 多模态互动

支持上传和解析不同类型的教学材料，包括：

- PDF
- DOCX
- 图片
- 文本资料
- 视频/多媒体内容扩展

借助解析器与 RAG 能力，系统能够把这些资料转化为可检索、可理解的知识内容。

### 2. 智能教学问答

用户可以在会话中提出问题，系统通过：

- 历史会话上下文
- LLM 推理
- 知识库检索
- 资料理解

来生成更贴合教学场景的回答。

### 3. 教育知识库

项目支持将教学资料整理进知识库，随后基于语义检索进行：

- 文档问答
- 资料总结
- 知识定位
- 课程内容补充

### 4. 课程生成与教案支持

系统支持从教学目标出发生成：

- 课程内容结构
- 讲义总结
- PPT 输出
- 教学材料草稿

这使其不仅适合作为问答助手，也可扩展为课程生成平台。

### 5. 流式聊天体验

前端通过 WebSocket 与后端建立实时连接，支持：

- 流式文本生成
- 实时返回回答片段
- 更自然的 AI 对话体验

## 技术架构

### 后端

- Python
- FastAPI
- SQLAlchemy
- SQLite（默认）
- ChromaDB
- OpenAI / ZhipuAI

### 前端

- Next.js
- React
- TypeScript
- Tailwind CSS

### 核心能力链路

```text
用户输入
  ↓
FastAPI 接口
  ↓
会话管理 + 消息存储
  ↓
LLM / RAG / 文件解析
  ↓
AI 生成内容
  ↓
前端实时展示
```

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/              # API 接口：聊天、知识库、上传、课件
│   │   ├── db/               # 数据库初始化与连接
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   ├── parsers/          # PDF / DOCX / 图片等解析器
│   │   ├── prompts/          # 提示词与教学场景模板
│   │   ├── services/         # LLM、RAG、聊天、生成任务逻辑
│   │   ├── config.py         # 配置管理
│   │   └── main.py           # FastAPI 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── uploads/
│   ├── chroma_data/
│   └── knowledge_base/
├── frontend/
│   ├── app/
│   ├── features/
│   ├── lib/
│   ├── styles/
│   ├── package.json
│   └── next.config.mjs
├── README.md
└── .env.example
```

## 典型使用场景

### 学生端

- 提问课程知识点
- 上传讲义、作业、资料
- 获取个性化解答
- 获取学习总结

### 教师端

- 创建教学会话
- 上传教材与案例
- 构建知识库
- 自动生成教案、讲义或课件内容

### 内容运营 / 教研端

- 整合课程资料
- 重复利用已有内容
- 快速生成教学素材
- 提升内容生产效率

## 快速开始

### 1. 安装依赖

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

前端：

```bash
cd frontend
npm install
```

### 2. 配置环境变量

在 `backend/` 下创建 `.env` 文件，可按需配置：

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
ZHIPU_API_KEY=your_key
PRIMARY_MODEL=gpt-4o
SECONDARY_MODEL=glm-4
FRONTEND_URL=http://localhost:3000
```

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 启动前端

```bash
cd frontend
npm run dev
```

访问地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`

## 产品价值

本产品的核心价值在于把教育场景中的知识、对话和生成能力统一到一个智能体中：

- 降低教师备课成本
- 提升学习支持效率
- 扩展知识库利用能力
- 让教育内容更具交互性和智能性

它不是单纯的聊天机器人，而是一个围绕教学任务设计的 AI 工作台。

## 未来方向

项目具备很强的扩展潜力，后续可以进一步升级为：

- 课程推荐与学习路径规划
- 学情分析与个性化辅导
- 多角色教学助手（教师 / 学生 / 助教）
- 多语言支持与本地化教学内容生成
- 更完善的任务编排和工作流引擎

## 结语

本项目试图将多模态 AI、知识库与教育场景融合在一起，构建一个更适合教学协作与知识增值的智能体平台。

它既具备“AI 聊天助手”的灵活性，也具备“教育内容生产和知识管理”的实用性，是一个以教学为核心的 AI 产品原型。 
