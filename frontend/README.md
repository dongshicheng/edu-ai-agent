# 前端目录说明

## 目录结构

```text
app/                         Next.js 路由入口和全局布局
features/
  chat/                      会话、消息、附件和语音输入
    components/               聊天页拆分出的界面组件
    types.ts                  聊天功能使用的数据类型
  knowledge/                  知识库上传与搜索
  courseware/                 课件生成状态与下载
lib/api.ts                    全站共用的 HTTP、WebSocket 请求和错误处理
styles/globals.css            全站基础样式和页面样式
```

## 页面如何组织

`app/` 中的 `page.tsx` 是路由适配层，只负责把 URL 映射到对应功能：

- `/`：重定向到聊天页
- `/chat`：加载 `features/chat/ChatPage.tsx`
- `/knowledge`：加载 `features/knowledge/KnowledgePage.tsx`
- `/preview/[taskId]`：加载 `features/courseware/PreviewPage.tsx`

页面逻辑放在 `features/`，避免把业务代码和 Next.js 路由配置混在一起。聊天页的侧栏、消息区和输入区分别位于 `features/chat/components/`。

## 常用命令

在此目录执行：

```bash
npm run dev       # 开发模式
npm run lint      # 代码检查
npm run build     # 生产构建
npm run start     # 启动生产构建
```

后端默认地址是 `http://localhost:8000`。需要切换时，在本地 `.env.local` 中设置 `NEXT_PUBLIC_API_BASE_URL`；不要把 `.env.local` 或密钥提交到版本库。
