import Link from "next/link";
import type { ChatMessage, ChatSession } from "../types";

type ChatSidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string;
  messages: ChatMessage[];
  isGenerating: boolean;
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
  onGenerateCourseware: () => void;
};

export default function ChatSidebar({
  sessions,
  activeSessionId,
  messages,
  isGenerating,
  onCreateSession,
  onSelectSession,
  onGenerateCourseware,
}: ChatSidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">AI 教学助手</div>
      <div className="sidebar-action">
        <button className="new-chat" onClick={onCreateSession}>
          <span aria-hidden="true">＋</span> 新建对话
        </button>
      </div>
      <nav className="session-list" aria-label="历史对话">
        {sessions.map((session) => (
          <button
            className={`session-item${session.id === activeSessionId ? " active" : ""}`}
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            title={session.title}
          >
            <span aria-hidden="true">▤</span>
            <span className="session-title">{session.title}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <button
          className="sidebar-link"
          disabled={!activeSessionId || messages.length === 0 || isGenerating}
          onClick={onGenerateCourseware}
        >
          <span aria-hidden="true">✦</span>
          {isGenerating ? "正在准备..." : "生成课件"}
        </button>
        <Link className="sidebar-link" href="/knowledge">
          <span aria-hidden="true">▣</span> 知识库管理
        </Link>
      </div>
    </aside>
  );
}
