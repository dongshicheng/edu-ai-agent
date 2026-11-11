"use client";

import Link from "next/link";
import { type ChangeEvent, type FormEvent, useState } from "react";
import { api, errorMessage } from "../../lib/api";

type SearchResult = {
  content: string;
  score: number;
  metadata: Record<string, string>;
};

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setIsUploading(true);
    setStatus(`正在上传 ${file.name}…`);
    setError("");

    const form = new FormData();
    form.append("file", file);
    try {
      const response = await api<{ filename: string; chunks: number }>(
        "/api/v1/knowledge/ingest",
        { method: "POST", body: form },
      );
      setStatus(
        `${response.filename} 已写入知识库（${response.chunks} 个文本片段）`,
      );
    } catch (uploadError) {
      setStatus("");
      setError(errorMessage(uploadError));
    } finally {
      setIsUploading(false);
    }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = query.trim();
    if (!term) return;
    setIsSearching(true);
    setError("");
    try {
      const response = await api<{ results: SearchResult[] }>(
        `/api/v1/knowledge/search?query=${encodeURIComponent(term)}&top_k=5`,
      );
      setResults(response.results ?? []);
    } catch (searchError) {
      setError(errorMessage(searchError));
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="page-content">
        <header className="page-heading">
          <Link className="icon-button" href="/chat" aria-label="返回聊天">
            ←
          </Link>
          <h1>知识库管理</h1>
        </header>

        <section className="panel">
          <h2>上传文档</h2>
          <div className="panel-body">
            <label className="upload-panel">
              <span aria-hidden="true">⇧</span>
              <p>支持 PDF、Word、TXT 等格式</p>
              <input
                className="file-picker"
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                disabled={isUploading}
                onChange={uploadFile}
              />
            </label>
            {status && <p className="status-text">{status}</p>}
            {error && <p className="inline-error">{error}</p>}
          </div>
        </section>

        <section className="panel">
          <h2>语义搜索</h2>
          <div className="panel-body">
            <form className="search-form" onSubmit={search}>
              <input
                className="search-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="输入搜索内容..."
              />
              <button
                className="primary-button"
                type="submit"
                disabled={isSearching || !query.trim()}
              >
                {isSearching ? "搜索中…" : "⌕ 搜索"}
              </button>
            </form>
            {results.map((result, index) => (
              <article className="result-card" key={`${index}-${result.content.slice(0, 24)}`}>
                <p>{result.content}</p>
                <p className="result-meta">
                  相似度：{(result.score * 100).toFixed(1)}% | 来源：
                  {result.metadata?.source || "未知"}
                </p>
              </article>
            ))}
            {!isSearching && query.trim() && results.length === 0 && !error && (
              <p className="status-text">暂无搜索结果。</p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
