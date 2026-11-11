import subprocess
import os
import base64
import tempfile
from app.models.parse_result import ParseResult
from app.services.llm_gateway import get_openai_client, _message_content_from_chat_response
from app.config import settings


def extract_keyframes(video_path: str, max_frames: int = 5) -> list[str]:
    """Extract keyframes from video using ffmpeg."""
    tmpdir = tempfile.mkdtemp()
    output_pattern = os.path.join(tmpdir, "frame_%03d.jpg")

    # Get video duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True,
    )
    duration = float(result.stdout.strip()) if result.stdout.strip() else 60

    interval = max(duration / (max_frames + 1), 1)

    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vf", f"fps=1/{interval}",
         "-frames:v", str(max_frames), "-q:v", "2", output_pattern,
         "-y", "-loglevel", "error"],
        capture_output=True,
    )

    frames = sorted(
        [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".jpg")]
    )
    return frames


def extract_audio(video_path: str) -> str | None:
    """Extract audio track from video."""
    tmpdir = tempfile.mkdtemp()
    audio_path = os.path.join(tmpdir, "audio.mp3")

    result = subprocess.run(
        ["ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3",
         "-q:a", "4", audio_path, "-y", "-loglevel", "error"],
        capture_output=True,
    )
    return audio_path if result.returncode == 0 and os.path.exists(audio_path) else None


async def analyze_frames(frame_paths: list[str]) -> str:
    """Analyze keyframes using GPT-4o vision."""
    client = get_openai_client()

    content = [
        {"type": "text", "text": "这是从一个教学视频中提取的关键帧。请分析这些帧的内容，描述视频可能在讲解什么主题，提取所有可见的文字和图表信息。请用中文回答。"},
    ]

    for path in frame_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    response = await client.chat.completions.create(
        model=settings.primary_model,
        messages=[{"role": "user", "content": content}],
        max_tokens=3000,
    )
    return _message_content_from_chat_response(response) or ""


async def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Whisper API."""
    client = get_openai_client()
    with open(audio_path, "rb") as f:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="zh",
        )
    return transcript.text


async def parse_video(file_path: str) -> ParseResult:
    """Parse video by extracting keyframes + audio transcription."""
    parts = []
    images = []

    # Extract and analyze keyframes
    try:
        frames = extract_keyframes(file_path)
        if frames:
            analysis = await analyze_frames(frames)
            parts.append(f"## 视频画面分析\n\n{analysis}")
            images = [{"description": analysis, "path": p} for p in frames]
    except Exception as e:
        parts.append(f"[关键帧提取失败: {e}]")

    # Transcribe audio
    try:
        audio_path = extract_audio(file_path)
        if audio_path:
            transcript = await transcribe_audio(audio_path)
            parts.append(f"## 音频转录\n\n{transcript}")
    except Exception as e:
        parts.append(f"[音频转录失败: {e}]")

    return ParseResult(
        text="\n\n".join(parts),
        images=images,
        source_type="video",
        metadata={"filename": file_path},
    )
