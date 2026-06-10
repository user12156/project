# 서비스: 문서 내용을 PDF 미리보기로 렌더링하는 변환과 프리뷰 생성 보조 모듈입니다.
import io
import os
from functools import lru_cache
from pathlib import Path


PREVIEW_TEXT_LIMIT = 60000
PREVIEW_MAX_PAGES = 30


def _font_candidates() -> list[Path]:
    configured = os.getenv("PREVIEW_FONT_PATH", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.extend(
        [
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/malgunbd.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"),
        ]
    )
    return candidates


@lru_cache(maxsize=8)
def _load_preview_font(size: int):
    from PIL import ImageFont

    for candidate in _font_candidates():
        if candidate and candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _measure_text(draw, text: str, font) -> float:
    try:
        return float(draw.textlength(text, font=font))
    except Exception:
        return float(draw.textbbox((0, 0), text, font=font)[2])


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue

        current = ""
        for char in paragraph:
            candidate = current + char
            if current and _measure_text(draw, candidate, font) > max_width:
                lines.append(current.rstrip())
                current = char.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def _preview_lines(draw, text: str, body_font, table_font, max_width: int) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            output.append(("", "body"))
            continue
        style = "table" if line.startswith("[표") or " | " in line else "body"
        font = table_font if style == "table" else body_font
        for wrapped in _wrap_text(draw, line, font, max_width):
            output.append((wrapped, style))
    return output


def render_text_preview_pdf(filename: str, text: str, *, source_format: str = "document") -> bytes:
    """Render extracted document text into a deployable PDF preview.

    The PDF is image-based so Korean text previews consistently across Linux
    Docker and Windows without relying on a proprietary HWP renderer.
    """

    from PIL import Image, ImageDraw

    safe_filename = Path(filename).name or "document"
    body_text = (text or "").strip() or "문서에서 추출 가능한 본문 텍스트를 찾지 못했습니다."
    truncated = len(body_text) > PREVIEW_TEXT_LIMIT
    body_text = body_text[:PREVIEW_TEXT_LIMIT]
    if truncated:
        body_text += "\n\n[미리보기는 문서 앞부분만 표시합니다. LLM 분석은 추출된 전체 문서 텍스트를 기준으로 수행됩니다.]"

    width, height = 1240, 1754
    margin_x, margin_y = 90, 88
    body_top = 170
    body_bottom = height - 90
    line_gap = 12
    title_font = _load_preview_font(36)
    meta_font = _load_preview_font(22)
    body_font = _load_preview_font(26)
    table_font = _load_preview_font(22)

    scratch = Image.new("RGB", (width, height), "white")
    scratch_draw = ImageDraw.Draw(scratch)
    lines = _preview_lines(scratch_draw, body_text, body_font, table_font, width - (margin_x * 2))
    line_height = max(34, int(_measure_text(scratch_draw, "가", body_font) * 1.65))

    pages: list[Image.Image] = []
    line_index = 0
    total_lines = len(lines)
    while line_index < total_lines and len(pages) < PREVIEW_MAX_PAGES:
        page = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(page)

        draw.text((margin_x, margin_y), safe_filename, fill="#0f172a", font=title_font)
        draw.text(
            (margin_x, margin_y + 50),
            f"{source_format} 파싱 기반 원본 미리보기",
            fill="#64748b",
            font=meta_font,
        )
        draw.line((margin_x, body_top - 22, width - margin_x, body_top - 22), fill="#dbe7f0", width=2)

        y = body_top
        while line_index < total_lines and y + line_height <= body_bottom:
            line, style = lines[line_index]
            if line:
                if style == "table":
                    draw.rectangle((margin_x - 8, y - 4, width - margin_x + 8, y + line_height + 3), fill="#f8fafc")
                draw.text(
                    (margin_x, y),
                    line,
                    fill="#334155" if style == "table" else "#1e293b",
                    font=table_font if style == "table" else body_font,
                )
            y += line_height + line_gap
            line_index += 1

        pages.append(page)

    if line_index < total_lines and pages:
        draw = ImageDraw.Draw(pages[-1])
        draw.rectangle((margin_x, body_bottom - 46, width - margin_x, body_bottom + 10), fill="white")
        draw.text(
            (margin_x, body_bottom - 40),
            "미리보기 페이지 제한으로 이후 내용은 생략되었습니다.",
            fill="#b45309",
            font=meta_font,
        )

    output = io.BytesIO()
    pages = pages or [scratch]
    pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=150.0)
    return output.getvalue()
