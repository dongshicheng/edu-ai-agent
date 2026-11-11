import type { RefObject } from "react";
import type { ChatMessage } from "../types";

type ChatTranscriptProps = {
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  scrollContainer: RefObject<HTMLDivElement>;
};

export default function ChatTranscript({
  messages,
  isLoading,
  isStreaming,
  scrollContainer,
}: ChatTranscriptProps) {
  return (
    <div className="message-list" ref={scrollContainer}>
      {isLoading ? (
        <div className="welcome">正在加载对话…</div>
      ) : messages.length === 0 ? (
        <div className="welcome">
          <div className="welcome-icon" aria-hidden="true">
            ✧
          </div>
          <div>
            <h2>欢迎使用 AI 教学助手</h2>
            <p>描述您的教学目标，我将帮您生成专业课件和教案</p>
          </div>
        </div>
      ) : (
        messages.map((message) => (
          <article
            className={`message ${message.role}${message.error ? " error" : ""}`}
            key={message.id}
          >
            <div className="message-bubble">
              {message.content || (isStreaming ? "正在思考…" : "")}
            </div>
          </article>
        ))
      )}
    </div>
  );
}
