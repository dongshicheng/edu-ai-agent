"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage, websocketUrl } from "../../lib/api";
import ChatComposer from "./components/ChatComposer";
import ChatSidebar from "./components/ChatSidebar";
import ChatTranscript from "./components/ChatTranscript";
import type {
  ChatMessage,
  ChatSession,
  UploadedAttachment,
} from "./types";

type SessionListResponse = { sessions: ChatSession[] };
type NewSessionResponse = { session_id: string };
type MessageListResponse = {
  messages: Array<{ id: string; role: "user" | "assistant"; content: string }>;
};
type UploadResponse = { file_id: string; status: UploadedAttachment["status"] };
type SpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

export default function ChatPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<UploadedAttachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState("");
  const scrollContainer = useRef<HTMLDivElement>(null);
  const activeSocket = useRef<WebSocket | null>(null);
  const speechRecognition = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    let active = true;
    async function loadSessions() {
      try {
        const response = await api<SessionListResponse>(
          "/api/v1/chat/sessions",
        );
        let available = response.sessions;
        if (available.length === 0) {
          const created = await api<NewSessionResponse>(
            "/api/v1/chat/sessions",
            { method: "POST" },
          );
          available = [{ id: created.session_id, title: "新对话", updatedAt: "" }];
        }
        if (active) {
          setSessions(available);
          setSessionId(available[0].id);
        }
      } catch (loadError) {
        if (active) setError(errorMessage(loadError));
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadSessions();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    setMessages([]);
    setError("");

    api<MessageListResponse>(
      `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
    )
      .then((response) => {
        if (active) {
          setMessages(
            response.messages.map((message) => ({
              id: message.id,
              role: message.role,
              content: message.content,
            })),
          );
        }
      })
      .catch((loadError: unknown) => {
        if (active) setError(errorMessage(loadError));
      });

    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => {
    const element = scrollContainer.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages]);

  useEffect(
    () => () => {
      activeSocket.current?.close();
      speechRecognition.current?.stop();
    },
    [],
  );

  async function createSession() {
    setError("");
    try {
      const created = await api<NewSessionResponse>("/api/v1/chat/sessions", {
        method: "POST",
      });
      setSessions((current) => [
        { id: created.session_id, title: "新对话", updatedAt: "" },
        ...current,
      ]);
      setSessionId(created.session_id);
      setAttachments([]);
      setMessages([]);
    } catch (createError) {
      setError(errorMessage(createError));
    }
  }

  const uploadFile = useCallback(
    async (file: File) => {
      if (!sessionId) return;
      const temporaryId = crypto.randomUUID();
      setAttachments((current) => [
        ...current,
        {
          id: temporaryId,
          name: file.name,
          status: "uploading",
        },
      ]);

      const form = new FormData();
      form.append("file", file);
      form.append("session_id", sessionId);

      try {
        const uploaded = await api<UploadResponse>("/api/v1/upload/file", {
          method: "POST",
          body: form,
        });
        const record = {
          id: uploaded.file_id,
          name: file.name,
          status: uploaded.status,
        };
        setAttachments((current) =>
          current.map((item) =>
            item.id === temporaryId ? record : item,
          ),
        );

        if (uploaded.status === "processing") {
          let settled = false;
          for (let attempt = 0; attempt < 60; attempt += 1) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            const status = await api<{
              status: string;
              error?: string;
            }>(`/api/v1/upload/status/${encodeURIComponent(uploaded.file_id)}`);
            if (status.status === "completed") {
              const content = await api<{ content: string }>(
                `/api/v1/upload/content/${encodeURIComponent(uploaded.file_id)}`,
              );
              setAttachments((current) =>
                current.map((item) =>
                  item.id === uploaded.file_id
                    ? { ...item, status: "completed", content: content.content }
                    : item,
                ),
              );
              settled = true;
              break;
            }
            if (status.status === "failed") {
              setAttachments((current) =>
                current.map((item) =>
                  item.id === uploaded.file_id
                    ? { ...item, status: "failed" }
                    : item,
                ),
              );
              settled = true;
              break;
            }
          }
          if (!settled) {
            setAttachments((current) =>
              current.map((item) =>
                item.id === uploaded.file_id
                  ? { ...item, status: "failed" }
                  : item,
              ),
            );
            setError(`文件“${file.name}”解析超时，请稍后重试。`);
          }
        }
      } catch (uploadError) {
        setAttachments((current) =>
          current.map((item) =>
            item.id === temporaryId ? { ...item, status: "failed" } : item,
          ),
        );
        setError(errorMessage(uploadError));
      }
    },
    [sessionId],
  );

  function toggleVoiceInput() {
    if (isListening) {
      speechRecognition.current?.stop();
      return;
    }

    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const Recognition =
      speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setError("当前浏览器不支持语音识别，请使用 Chrome 浏览器。");
      return;
    }

    const recognition = new Recognition();
    recognition.lang = "zh-CN";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .map((result) => result[0]?.transcript ?? "")
        .join("");
      if (transcript) {
        setInput((current) => `${current}${current ? " " : ""}${transcript}`);
      }
    };
    recognition.onend = () => {
      setIsListening(false);
      speechRecognition.current = null;
    };
    speechRecognition.current = recognition;
    setError("");
    setIsListening(true);
    try {
      recognition.start();
    } catch (startError) {
      setIsListening(false);
      speechRecognition.current = null;
      setError(errorMessage(startError));
    }
  }

  async function sendMessage() {
    if (
      isStreaming ||
      !sessionId ||
      attachments.some(
        (file) => file.status === "uploading" || file.status === "processing",
      )
    ) {
      return;
    }
    const userText = input.trim();
    const attachedText = attachments
      .filter((file) => file.status === "completed" && file.content)
      .map((file) => `\n\n[附件：${file.name}]\n${file.content}`)
      .join("");
    if (!userText && !attachedText) return;

    const content = `${userText}${attachedText}`.trim();
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content },
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setInput("");
    setAttachments([]);
    setError("");
    setIsStreaming(true);

    try {
      const socket = new WebSocket(
        websocketUrl(`/api/v1/chat/stream/${encodeURIComponent(sessionId)}`),
      );
      activeSocket.current = socket;
      socket.onopen = () => socket.send(JSON.stringify({ content }));
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type: "chunk" | "error" | "done";
            content?: string;
          };
          if (payload.type === "chunk" && payload.content) {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + payload.content }
                  : message,
              ),
            );
          } else if (payload.type === "error") {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content: payload.content ?? "回复生成失败",
                      error: true,
                    }
                  : message,
              ),
            );
            socket.close();
          } else if (payload.type === "done") {
            socket.close();
          }
        } catch (parseError) {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: `无法读取服务器回复：${errorMessage(parseError)}`,
                    error: true,
                  }
                : message,
            ),
          );
          socket.close();
        }
      };
      socket.onerror = () => {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId && !message.content
              ? {
                  ...message,
                  content: "连接后端失败，请检查后端服务和地址配置。",
                  error: true,
                }
              : message,
          ),
        );
      };
      socket.onclose = () => {
        setIsStreaming(false);
        activeSocket.current = null;
      };
    } catch (sendError) {
      setError(errorMessage(sendError));
      setIsStreaming(false);
    }
  }

  async function generateCourseware() {
    if (!sessionId || messages.length === 0 || isGenerating) return;
    setError("");
    setIsGenerating(true);
    try {
      await api(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/intent`, {
        method: "POST",
      });
      const task = await api<{ task_id: string }>("/api/v1/courseware/generate", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          output_types: ["pptx", "docx"],
        }),
      });
      router.push(`/preview/${encodeURIComponent(task.task_id)}`);
    } catch (generationError) {
      setError(errorMessage(generationError));
      setIsGenerating(false);
    }
  }

  return (
    <main className="chat-shell">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        messages={messages}
        isGenerating={isGenerating}
        onCreateSession={() => void createSession()}
        onSelectSession={setSessionId}
        onGenerateCourseware={() => void generateCourseware()}
      />

      <section className="chat-main">
        <ChatTranscript
          messages={messages}
          isLoading={isLoading}
          isStreaming={isStreaming}
          scrollContainer={scrollContainer}
        />
        <ChatComposer
          input={input}
          attachments={attachments}
          error={error}
          isLoading={isLoading}
          isSending={isStreaming}
          isListening={isListening}
          onInputChange={setInput}
          onFiles={(files) => files.forEach((file) => void uploadFile(file))}
          onRemoveAttachment={(attachmentId) =>
            setAttachments((current) =>
              current.filter((item) => item.id !== attachmentId),
            )
          }
          onToggleVoice={toggleVoiceInput}
          onSend={() => void sendMessage()}
        />
      </section>
    </main>
  );
}
