from app.services.llm_gateway import chat_completion

INTERACTIVE_PROMPT = """你是一位教育互动内容设计师。根据以下教学主题，生成一个自包含的 HTML5 互动页面。

主题：{topic}
要求：{requirements}

生成要求：
1. 输出完整的 HTML 文件，包含内联的 CSS 和 JavaScript
2. 不依赖任何外部库或 CDN
3. 页面应具有教学互动功能（如小测验、拖拽排序、动画演示等）
4. 界面美观，使用中文
5. 适合在浏览器中直接打开使用

直接输出 HTML 代码，不要包含 ```html 标记。"""


async def generate_interactive_html(
    topic: str,
    requirements: str = "创建一个与主题相关的互动小测验",
) -> str:
    """Generate self-contained HTML5 interactive content."""
    prompt = INTERACTIVE_PROMPT.format(topic=topic, requirements=requirements)
    messages = [
        {"role": "system", "content": "你是一位专业的教育互动内容设计师。直接输出完整的HTML代码。"},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(messages, max_tokens=8000)

    # Clean up if wrapped in code blocks
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    return result
