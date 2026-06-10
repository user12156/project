# 서비스: 문서 텍스트 전처리, 표/이미지 감지, 미리보기 생성 로직을 담고 있습니다.
import io
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.document_conversion import render_text_preview_pdf


PREVIEW_CACHE: dict[tuple[str, int], bytes] = {}
PREVIEW_EXTENSIONS = {".hwp", ".hwpx"}
BOX_NOISE_PATTERN = re.compile(r"[\u25a0-\u25ff\u2b00-\u2bff\ufffd]+")
TEXT_NOISE_PATTERN = re.compile(r"[\u0100-\u024f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\ue000-\uf8ff]+")
IMAGE_META_PATTERN = re.compile(
    r"(?:원본\s*그림|그림의\s*이름|그림의\s*크기|image|picture|figure)",
    re.IGNORECASE,
)
TABLE_HINT_PATTERN = re.compile(r"(?:^|\s)(?:표|table)\s*\d*|[│┃┌┐└┘├┤┬┴┼]", re.IGNORECASE)
HWPX_PARAGRAPH_TAGS = {"p", "para"}
HWPX_TABLE_TAGS = {"tbl", "table"}
HWPX_IMAGE_TAGS = {"pic", "image", "img", "ole", "container", "shapeobject"}


def _local_name(tag: str) -> str:
    return str(tag or "").rsplit("}", 1)[-1].split(":")[-1].lower()


def _clean_preview_line(text: str) -> str:
    text = str(text or "").replace("\r", "\n")
    text = BOX_NOISE_PATTERN.sub(" ", text)
    text = TEXT_NOISE_PATTERN.sub(" ", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]+", " ", text)
    text = re.sub(r"\^\s*\(?\d+\)?", " ", text)
    text = re.sub(r"[·•◦]{2,}", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _is_low_signal_line(line: str) -> bool:
    if not line:
        return True
    letters = re.findall(r"[A-Za-z가-힣0-9]", line)
    return len(letters) < 2


def _is_table_like(raw_line: str, cleaned_line: str) -> bool:
    if TABLE_HINT_PATTERN.search(cleaned_line):
        return True
    return raw_line.count("\t") >= 2 or raw_line.count("|") >= 2


def _join_hwpx_texts(parts: list[str]) -> str:
    tokens = [_clean_preview_line(part) for part in parts]
    tokens = [token for token in tokens if token]
    if not tokens:
        return ""
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:!?%)\]\}])", r"\1", text)
    text = re.sub(r"([(\[\{])\s+", r"\1", text)
    text = re.sub(r"\s+([~-])\s+", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _extract_hwpx_blocks(root: ElementTree.Element) -> list[str]:
    blocks: list[str] = []
    image_index = 0
    table_index = 0

    def walk(node: ElementTree.Element) -> None:
        nonlocal image_index, table_index
        name = _local_name(node.tag)

        if name in HWPX_TABLE_TAGS:
            table_index += 1
            blocks.append(f"[표 {table_index}]")
            return

        if name in HWPX_IMAGE_TAGS:
            image_index += 1
            blocks.append(f"[이미지 {image_index}]")
            return

        if name in HWPX_PARAGRAPH_TAGS:
            paragraph = _join_hwpx_texts([text for text in node.itertext() if text and text.strip()])
            if paragraph:
                blocks.append(paragraph)
            return

        for child in list(node):
            walk(child)

    walk(root)
    return blocks


def _structure_preview_text(text: str) -> str:
    image_index = 0
    table_index = 0
    output: list[str] = []
    previous_placeholder = ""

    for raw_line in str(text or "").replace("\r", "\n").splitlines():
        cleaned = _clean_preview_line(raw_line)
        placeholder = ""

        if IMAGE_META_PATTERN.search(raw_line) or IMAGE_META_PATTERN.search(cleaned):
            if previous_placeholder.startswith("[이미지 "):
                placeholder = previous_placeholder
            else:
                image_index += 1
                placeholder = f"[이미지 {image_index}]"
        elif _is_table_like(raw_line, cleaned):
            if previous_placeholder.startswith("[표 "):
                placeholder = previous_placeholder
            else:
                table_index += 1
                placeholder = f"[표 {table_index}]"

        if placeholder:
            if placeholder != previous_placeholder:
                output.append(placeholder)
            previous_placeholder = placeholder
            continue

        previous_placeholder = ""
        if _is_low_signal_line(cleaned):
            if output and output[-1] != "":
                output.append("")
            continue
        output.append(cleaned)

    structured = "\n".join(output)
    structured = re.sub(r"\n{3,}", "\n\n", structured)
    return structured.strip()


def _extract_hwpx_preview_text(content: bytes) -> str:
    blocks: list[str] = []
    fallback_texts: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                lower_name = name.lower()
                if not lower_name.endswith(".xml"):
                    continue
                if not any(part in lower_name for part in ("contents/", "section", "bodytext")):
                    continue
                try:
                    root = ElementTree.fromstring(archive.read(name))
                except ElementTree.ParseError:
                    continue
                extracted_blocks = _extract_hwpx_blocks(root)
                if extracted_blocks:
                    blocks.extend(extracted_blocks)
                else:
                    fallback_texts.append(_join_hwpx_texts([text for text in root.itertext() if text and text.strip()]))
    except Exception:
        return ""

    if not blocks:
        blocks = [text for text in fallback_texts if text]
    return _structure_preview_text("\n".join(blocks))


def _extract_hwp_preview_text(content: bytes) -> str:
    try:
        import olefile
    except ModuleNotFoundError:
        return ""

    try:
        ole = olefile.OleFileIO(io.BytesIO(content))
    except Exception:
        return ""

    try:
        header = ole.openstream("FileHeader").read()
        is_compressed = bool(header[36] & 1) if len(header) > 36 else False
        section_names = sorted(
            "/".join(path)
            for path in ole.listdir()
            if len(path) == 2 and path[0] == "BodyText" and path[1].startswith("Section")
        )

        chunks: list[str] = []
        for section_name in section_names:
            raw = ole.openstream(section_name).read()
            if is_compressed:
                import zlib

                raw = zlib.decompress(raw, -15)

            offset = 0
            while offset + 4 <= len(raw):
                header_value = int.from_bytes(raw[offset:offset + 4], "little")
                offset += 4
                tag_id = header_value & 0x3FF
                size = (header_value >> 20) & 0xFFF
                if size == 0xFFF:
                    if offset + 4 > len(raw):
                        break
                    size = int.from_bytes(raw[offset:offset + 4], "little")
                    offset += 4

                payload = raw[offset:offset + size]
                offset += size
                if tag_id == 67 and payload:
                    chunks.append(payload.decode("utf-16le", errors="ignore"))
        return _structure_preview_text("\n".join(chunks))
    except Exception:
        return ""
    finally:
        ole.close()


def _convert_with_office(filename: str, content: bytes) -> bytes | None:
    """Use an installed office renderer when available, keeping preview separate from analysis."""

    command = os.getenv("DOCUMENT_PREVIEW_OFFICE_COMMAND", "soffice").strip() or "soffice"
    suffix = Path(filename).suffix.lower() or ".document"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / f"preview{suffix}"
            output_dir = Path(tmpdir) / "out"
            output_dir.mkdir(parents=True, exist_ok=True)
            input_path.write_bytes(content)

            subprocess.run(
                [
                    command,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(input_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=settings.hwp_parser_timeout_seconds,
            )
            pdf_files = list(output_dir.glob("*.pdf"))
            if not pdf_files:
                return None
            return pdf_files[0].read_bytes()
    except Exception:
        return None


def _fallback_text_preview(filename: str, content: bytes) -> bytes:
    extension = Path(filename).suffix.lower()
    if extension == ".hwpx":
        text = _extract_hwpx_preview_text(content)
        source_format = "HWPX preview"
    else:
        text = _extract_hwp_preview_text(content)
        source_format = "HWP preview"

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="원본 미리보기 렌더러가 없고 문서 본문 텍스트도 추출하지 못했습니다.",
        )
    return render_text_preview_pdf(filename, text, source_format=source_format)


def create_document_preview_pdf(filename: str, content: bytes) -> bytes:
    extension = Path(filename).suffix.lower()
    if extension not in PREVIEW_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HWP/HWPX 파일만 PDF 미리보기를 생성할 수 있습니다.",
        )

    cache_key = (filename, hash(content))
    cached_pdf = PREVIEW_CACHE.get(cache_key)
    if cached_pdf:
        return cached_pdf

    pdf_bytes = _convert_with_office(filename, content) or _fallback_text_preview(filename, content)
    if len(PREVIEW_CACHE) > 20:
        PREVIEW_CACHE.clear()
    PREVIEW_CACHE[cache_key] = pdf_bytes
    return pdf_bytes
