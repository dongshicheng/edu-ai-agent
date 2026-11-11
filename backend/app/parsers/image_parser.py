import base64
from app.models.parse_result import ParseResult
from app.services.llm_gateway import get_openai_client, _message_content_from_chat_response
from app.config import settings


async def parse_image(file_path: str) -> ParseResult:
    """Parse image using GPT-4o vision API."""
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = file_path.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
    mime = mime_map.get(ext, "jpeg")

    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.primary_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请详细描述这张图片的内容。如果包含文字，请提取所有文字。如果是教学相关的图表或示意图，请详细解释其含义。请用中文回答。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{mime};base64,{image_data}",
                        },
                    },
                ],
            }
        ],
        max_tokens=2000,
    )

    description = _message_content_from_chat_response(response) or ""

    return ParseResult(
        text=description,
        images=[{"description": description, "path": file_path}],
        source_type="image",
        metadata={"filename": file_path},
    )
