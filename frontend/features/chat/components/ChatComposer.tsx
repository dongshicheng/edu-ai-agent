"use client";

import { type ChangeEvent, type DragEvent, useRef, useState } from "react";
import type { UploadedAttachment } from "../types";

const ACCEPTED_FILES =
  ".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.mp4,.avi,.mov";

type ChatComposerProps = {
  input: string;
  attachments: UploadedAttachment[];
  error: string;
  isLoading: boolean;
  isSending: boolean;
  isListening: boolean;
  onInputChange: (value: string) => void;
  onFiles: (files: File[]) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onToggleVoice: () => void;
  onSend: () => void;
};

export default function ChatComposer({
  input,
  attachments,
  error,
  isLoading,
  isSending,
  isListening,
  onInputChange,
  onFiles,
  onRemoveAttachment,
  onToggleVoice,
  onSend,
}: ChatComposerProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    onFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    onFiles(Array.from(event.dataTransfer.files));
  }

  const hasPendingUpload = attachments.some(
    (file) => file.status === "uploading" || file.status === "processing",
  );
  const hasCompletedAttachment = attachments.some(
    (file) => file.status === "completed" && file.content,
  );

  return (
    <footer className="composer">
      <div className="composer-inner">
        <div
          className={`dropzone${isDragging ? " dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInput.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              fileInput.current?.click();
            }
          }}
        >
          拖拽或点击上传文件（PDF / Word / 图片 / 视频）
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            accept={ACCEPTED_FILES}
            multiple
            onChange={handleFileChange}
            onClick={(event) => event.stopPropagation()}
          />
        </div>
        {attachments.length > 0 && (
          <div className="file-list">
            {attachments.map((file) => (
              <div className="file-row" key={file.id}>
                <span>{file.name}</span>
                <span className="file-status">
                  {file.status === "uploading" && "上传中…"}
                  {file.status === "processing" && "解析中…"}
                  {file.status === "completed" && "已完成"}
                  {file.status === "failed" && "失败"}
                  {file.status === "unsupported" && "不支持解析"}
                </span>
                <button
                  className="icon-button"
                  type="button"
                  aria-label={`移除 ${file.name}`}
                  onClick={() => onRemoveAttachment(file.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        {error && <p className="inline-error">{error}</p>}
        <form
          className="compose-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSend();
          }}
        >
          <input
            className="text-input"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="描述您的教学需求，例如：帮我制作一份高中物理《牛顿第二定律》的课件..."
            disabled={isSending || isLoading}
          />
          <button
            className="icon-button"
            type="button"
            title={isListening ? "停止语音输入" : "开始语音输入"}
            aria-label={isListening ? "停止语音输入" : "开始语音输入"}
            onClick={onToggleVoice}
            disabled={isSending || isLoading}
          >
            {isListening ? "■" : "麦"}
          </button>
          <button
            className="primary-button"
            type="submit"
            disabled={
              isSending ||
              isLoading ||
              hasPendingUpload ||
              (!input.trim() && !hasCompletedAttachment)
            }
            aria-label="发送"
          >
            发送
          </button>
        </form>
      </div>
    </footer>
  );
}
