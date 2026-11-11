import json
from typing import Any, AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

_openai_client: AsyncOpenAI | None = None


def _raise_if_html_gateway_body(text: str) -> None:
    """网关误配为站点首页时，接口正文为整页 HTML；避免当作模型回复展示。"""
    s = text.lstrip()
    if len(s) < 12:
        return
    low = s[:32].lower()
    if low.startswith("<!doctype html") or low.startswith("<html"):
        raise ValueError(
            "LLM 接口返回了网页（HTML）而非 JSON，多因 OPENAI_BASE_URL 未指向 OpenAI 兼容 API。"
            "请使用 https://你的网关域名/v1（必须含 /v1），不要使用控制台首页。"
            "若 .env 里只写了域名，保存后重启后端，程序会自动补全 /v1。"
        )


def _extract_delta_text(delta: Any) -> str | None:
    """从流式 chunk 的 delta 中取出文本；兼容 dict / 对象及部分网关的非标准 content 结构。"""
    if delta is None:
        return None
    if isinstance(delta, dict):
        c = delta.get("content")
    else:
        c = getattr(delta, "content", None)
    if isinstance(c, str) and c:
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for item in c:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(str(item["text"]))
                elif isinstance(item.get("text"), str):
                    parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts) if parts else None
    return None


def _text_from_stream_chunk(chunk: Any) -> str | None:
    """从单次流式事件中解析出文本；兼容 SDK 对象、dict、以及部分网关返回的 JSON 字符串。"""
    if chunk is None:
        return None
    if isinstance(chunk, (bytes, bytearray)):
        try:
            chunk = chunk.decode("utf-8")
        except Exception:
            return None
    if isinstance(chunk, str):
        line = chunk.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if line in ("[DONE]", "", "{}"):
            return None
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return None
        return _text_from_stream_chunk(parsed)
    if isinstance(chunk, dict):
        choices = chunk.get("choices") or []
        if not choices:
            return None
        first = choices[0]
        if isinstance(first, dict):
            delta = first.get("delta")
        else:
            delta = getattr(first, "delta", None)
        return _extract_delta_text(delta)
    ch = getattr(chunk, "choices", None)
    if not ch:
        return None
    if isinstance(ch, str):
        try:
            parsed = json.loads(ch)
        except json.JSONDecodeError:
            return None
        return _text_from_stream_chunk({"choices": parsed if isinstance(parsed, list) else [parsed]})
    try:
        first = ch[0]
    except (IndexError, TypeError):
        return None
    if isinstance(first, dict):
        delta = first.get("delta")
        return _extract_delta_text(delta)
    delta = getattr(first, "delta", None)
    return _extract_delta_text(delta)


def _message_content_from_chat_response(response: Any) -> str:
    """解析非流式 chat 返回：兼容 SDK 对象、dict、以及部分网关返回的 JSON 字符串。"""
    if response is None:
        return ""
    if isinstance(response, str):
        s = response.strip()
        if not s:
            return ""
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            _raise_if_html_gateway_body(s)
            return s
        return _message_content_from_chat_response(parsed)
    if isinstance(response, dict):
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        msg = first.get("message")
        if isinstance(msg, dict):
            out = (msg.get("content") or "") or ""
            _raise_if_html_gateway_body(out)
            return out
        delta = first.get("delta")
        if isinstance(delta, dict):
            return (delta.get("content") or "") or ""
        return ""
    try:
        choices = getattr(response, "choices", None)
    except Exception:
        return ""
    if not choices:
        return ""
    try:
        first = choices[0]
        msg = getattr(first, "message", None)
        if msg is not None:
            content = getattr(msg, "content", None)
            if isinstance(content, str):
                _raise_if_html_gateway_body(content)
                return content
            if content is not None:
                out = str(content)
                _raise_if_html_gateway_body(out)
                return out
    except (IndexError, AttributeError, TypeError):
        pass
    return ""


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _openai_client


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Non-streaming chat completion."""
    client = get_openai_client()
    model = model or settings.primary_model
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _message_content_from_chat_response(response) or ""


async def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Streaming chat completion. Yields content chunks.

    若流式响应中未出现任何文本 delta（部分兼容层实现不完整），回退为一次性补全，
    避免出现仅收到 done、无 chunk 的现象。
    """
    client = get_openai_client()
    model = model or settings.primary_model
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    yielded = False
    async for chunk in stream:
        text = _text_from_stream_chunk(chunk)
        if text:
            yielded = True
            yield text

    if not yielded:
        full = await chat_completion(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        if full:
            yield full


async def chat_completion_json(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Chat completion with JSON response format."""
    client = get_openai_client()
    model = model or settings.primary_model
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    text = _message_content_from_chat_response(response)
    return text if text else "{}"
