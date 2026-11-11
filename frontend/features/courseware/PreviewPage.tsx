"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API_BASE, api, errorMessage } from "../../lib/api";

type TaskStatus = {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  result_urls: Record<string, string>;
  error?: string | null;
};

export default function PreviewPage() {
  const params = useParams<{ taskId: string }>();
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const response = await api<TaskStatus>(
          `/api/v1/courseware/status/${encodeURIComponent(params.taskId)}`,
        );
        if (!active) return;
        if ("error" in response && !response.status) {
          setError(response.error || "找不到该生成任务。");
          return;
        }
        setTask(response);
        if (response.status === "pending" || response.status === "processing") {
          timer = setTimeout(() => void poll(), 2000);
        }
      } catch (pollError) {
        if (active) setError(errorMessage(pollError));
      }
    }

    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [params.taskId]);

  const progress = Math.round(Math.max(0, Math.min(1, task?.progress ?? 0)) * 100);

  return (
    <main className="page-shell">
      <div className="page-content">
        <header className="page-heading">
          <Link className="icon-button" href="/chat" aria-label="返回聊天">
            ←
          </Link>
          <h1>课件预览</h1>
        </header>

        <section className="panel">
          <h2>生成状态</h2>
          <div className="panel-body">
            {error ? (
              <p className="inline-error">{error}</p>
            ) : !task ? (
              <p className="status-text">加载中…</p>
            ) : task.status === "pending" ? (
              <p className="status-text">等待生成…</p>
            ) : task.status === "processing" ? (
              <>
                <div
                  className="progress-track"
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="progress-value"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="status-text">正在生成课件… {progress}%</p>
              </>
            ) : task.status === "completed" ? (
              <>
                <p className="success-text">生成完成！</p>
                <div className="preview-actions">
                  {task.result_urls.pptx && (
                    <a
                      className="primary-button"
                      href={`${API_BASE}${task.result_urls.pptx}`}
                    >
                      下载 PPT
                    </a>
                  )}
                  {task.result_urls.docx && (
                    <a
                      className="secondary-button"
                      href={`${API_BASE}${task.result_urls.docx}`}
                    >
                      下载教案
                    </a>
                  )}
                </div>
              </>
            ) : (
              <>
                <p className="inline-error">生成失败</p>
                <p className="status-text">{task.error || "未知错误"}</p>
              </>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
