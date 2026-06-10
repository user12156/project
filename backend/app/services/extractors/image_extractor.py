# 서비스: 이미지 파일 검사, OCR, 멀티모달 이미지 업로드 지원을 담당합니다.
"""Image inspection, OCR, and uploaded-image multimodal metadata."""

import base64
import io
import json
import mimetypes
import urllib.error
import urllib.request

from app.core.config import settings
from app.services.analysis.answer_builder import _clean_text
from app.services.visual_buttons.image.extraction import summarize_uploaded_image


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
CLAUDE_SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _image_metadata(content: bytes) -> tuple[object | None, str]:
    try:
        from PIL import Image
    except ModuleNotFoundError:
        return None, "이미지 분석을 위해 Pillow 패키지가 필요합니다. requirements.txt 설치 후 다시 시도해주세요."

    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        return None, "이미지 파일을 열 수 없습니다."

    return image, f"이미지 파일입니다. 크기: {image.width}x{image.height}px, 형식: {image.format}."


def _image_payload(content: bytes, image) -> tuple[bytes, str]:
    image_format = getattr(image, "format", None) or "PNG"
    guessed_mime = mimetypes.types_map.get(f".{image_format.lower()}")
    mime_type = guessed_mime or f"image/{image_format.lower().replace('jpg', 'jpeg')}"
    if mime_type in CLAUDE_SUPPORTED_MIME_TYPES:
        return content, mime_type

    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG")
    return output.getvalue(), "image/png"


def _claude_vision(content: bytes, image, description: str) -> str:
    if not settings.anthropic_api_key:
        return ""

    image_bytes, mime_type = _image_payload(content, image)
    payload = {
        "model": settings.anthropic_vision_model,
        "max_tokens": 700,
        "temperature": 0.1,
        "system": (
            "You are PaperMate's Korean image understanding assistant. "
            "Describe only what is visible in the image. Return natural Korean."
        ),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "이 이미지를 한국어로 분석해줘. "
                            "텍스트, 표/그래프 여부, 주요 객체, 문서 분석에 쓸 근거를 간결하게 정리해줘. "
                            "보이지 않는 내용은 추측하지 마."
                        ),
                    },
                ],
            }
        ],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return f"{description} Claude Vision 호출 실패: HTTP {exc.code}."
    except Exception:
        return ""

    parts = result.get("content") or []
    text = " ".join(str(part.get("text", "")) for part in parts if part.get("type") == "text")
    text = _clean_text(text)
    return f"{description} Claude Vision 분석: {text}" if text else ""


def _qwen_vision(content: bytes, image, description: str) -> str:
    if not settings.local_vlm_enabled:
        return ""
    # 로컬 Qwen2.5-VL 서버/런타임 연결 지점입니다. 아직 연결 정보가 없으면 OCR로 폴백합니다.
    return ""


def _tesseract_ocr(image, description: str) -> str:
    try:
        import pytesseract
    except ModuleNotFoundError:
        return f"{description} 이미지 속 텍스트까지 발췌하려면 OCR 엔진(pytesseract/Tesseract)이 필요합니다."

    try:
        ocr_text = _clean_text(pytesseract.image_to_string(image, lang="kor+eng"))
    except Exception:
        return f"{description} OCR 실행 파일(Tesseract)이 설치되어 있지 않아 이미지 속 문자는 아직 읽을 수 없습니다."

    if not ocr_text:
        return f"{description} OCR로 읽힌 텍스트가 없습니다."
    return f"{description} OCR 추출 텍스트: {ocr_text}"


def understand_image(content: bytes) -> str:
    image, description = _image_metadata(content)
    if image is None:
        return description

    claude_answer = _claude_vision(content, image, description)
    if claude_answer:
        return claude_answer

    qwen_answer = _qwen_vision(content, image, description)
    if qwen_answer:
        return qwen_answer

    return _tesseract_ocr(image, description)


def inspect_image(content: bytes) -> str:
    return understand_image(content)


def extract_uploaded_image_assets(filename: str, content: bytes) -> list[dict]:
    return summarize_uploaded_image(filename, content, source_label=filename)
