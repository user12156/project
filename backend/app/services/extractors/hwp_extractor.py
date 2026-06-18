# 서비스: HWP/HWPX 문서 추출과 이미지/텍스트 병합 처리를 지원합니다.
"""HWP and HWPX extraction helpers."""

import io
import re
import struct
import subprocess
import tempfile
import zipfile
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

from app.core.config import settings
from app.services.analysis.answer_builder import _clean_text
from app.services.extractors.image_extractor import IMAGE_EXTENSIONS


def _decode_xml_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp949"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_xml_text(raw: bytes) -> str:
    try:
        root = ElementTree.fromstring(raw)
        return " ".join(text.strip() for text in root.itertext() if text and text.strip())
    except ElementTree.ParseError:
        pass

    # 일부 공공기관 HWPX는 본문 XML에 잘못 이스케이프된 문자나 제어 문자가
    # 포함되어 표준 XML 파서가 전체 section을 버립니다. 텍스트 노드는 별도로
    # 복구해 문서 전체가 빈 본문으로 처리되지 않게 합니다.
    decoded = _decode_xml_bytes(raw)
    decoded = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", decoded)
    text_nodes = re.findall(
        r"<(?:[A-Za-z_][\w.-]*:)?(?:t|text)\b[^>]*>(.*?)</(?:[A-Za-z_][\w.-]*:)?(?:t|text)>",
        decoded,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not text_nodes:
        return ""

    recovered = []
    for node in text_nodes:
        node = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", node, flags=re.DOTALL)
        node = re.sub(r"<[^>]+>", " ", node)
        cleaned = unescape(node).strip()
        if cleaned:
            recovered.append(cleaned)
    return " ".join(recovered)


def _is_hwpx_content_xml(name: str) -> bool:
    normalized = name.replace("\\", "/").lower()
    return normalized.endswith(".xml") and (
        "contents/" in normalized
        or "bodytext/" in normalized
        or "/section" in normalized
        or normalized.startswith("section")
    )


def _hwpx_encryption_algorithm(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest = archive.read("META-INF/manifest.xml")
    except (KeyError, zipfile.BadZipFile):
        return ""

    try:
        root = ElementTree.fromstring(manifest)
    except ElementTree.ParseError:
        return ""

    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "algorithm":
            continue
        algorithm = (
            node.attrib.get("algorithm-name")
            or node.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}algorithm-name")
            or ""
        )
        if algorithm:
            return algorithm

    return "encrypted" if b"encryption-data" in manifest else ""


def _parse_hwpx_bytes(data: bytes) -> tuple[str, list[dict]]:
    content_texts = []
    fallback_texts = []
    images = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                lower_name = name.lower()
                if lower_name.endswith(".xml"):
                    try:
                        raw = archive.read(name)
                    except KeyError:
                        continue
                    extracted = _extract_xml_text(raw)
                    if extracted:
                        if _is_hwpx_content_xml(name):
                            content_texts.append(extracted)
                        else:
                            fallback_texts.append(extracted)

                if any(lower_name.endswith(ext) for ext in IMAGE_EXTENSIONS) or lower_name.endswith(".svg"):
                    try:
                        images.append({"name": name, "bytes": archive.read(name)})
                    except KeyError:
                        continue
    except zipfile.BadZipFile:
        return "", []

    texts = content_texts or fallback_texts
    combined = "\n".join(_clean_text(text) for text in texts if text)
    return combined, images


def _parse_hwpx_with_java(jar_path: str, data: bytes) -> tuple[str, list[dict]]:
    if not jar_path or not Path(jar_path).is_file():
        return "", []

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".hwpx") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        proc = subprocess.run(
            ["java", "-jar", jar_path, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return "", []
        return _clean_text(proc.stdout or ""), []
    except Exception:
        return "", []
    finally:
        try:
            if "tmp_path" in locals() and Path(tmp_path).exists():
                Path(tmp_path).unlink()
        except Exception:
            pass


def _parse_hwp_bytes(data: bytes) -> tuple[str, list[dict]]:
    try:
        import hwplib
    except ModuleNotFoundError:
        return "", []

    try:
        if hasattr(hwplib, "HWPDocument"):
            doc = hwplib.HWPDocument(io.BytesIO(data))
            text_parts = []
            for para in getattr(doc, "paragraphs", []) or []:
                try:
                    text_parts.append(" ".join(part.text for part in para if getattr(part, "text", None)))
                except Exception:
                    continue
            return _clean_text("\n".join(text_parts)), []

        if hasattr(hwplib, "HwpDocument"):
            doc = hwplib.HwpDocument(io.BytesIO(data))
            return _clean_text(str(doc)), []
    except Exception:
        return "", []

    return "", []


def parse_document(file_bytes: bytes, filename: str = "document") -> dict:
    ext = Path(filename).suffix.lower()
    if ext == ".hwpx":
        encryption_algorithm = _hwpx_encryption_algorithm(file_bytes)
        if encryption_algorithm:
            return {
                "filename": filename,
                "format": "hwpx",
                "text": "",
                "images": [],
                "encrypted": True,
                "encryption_algorithm": encryption_algorithm,
            }

        jar_path = settings.hwpx_jar
        if jar_path:
            try:
                text, images = _parse_hwpx_with_java(jar_path, file_bytes)
                if text or images:
                    return {"filename": filename, "format": "hwpx", "text": text, "images": images}
            except Exception:
                pass

        text, images = _parse_hwpx_bytes(file_bytes)
        return {"filename": filename, "format": "hwpx", "text": text, "images": images}

    if ext == ".hwp":
        text, images = _parse_hwp_bytes(file_bytes)
        return {"filename": filename, "format": "hwp", "text": text, "images": images}

    try:
        text, images = _parse_hwpx_bytes(file_bytes)
        if text or images:
            return {"filename": filename, "format": "zip-xml", "text": text, "images": images}
    except Exception:
        pass

    return {"filename": filename, "format": "unknown", "text": "", "images": []}


def extract_hwp(content: bytes) -> str:
    try:
        import olefile
    except ModuleNotFoundError:
        return "HWP 바이너리 문서는 olefile 패키지 또는 HWPX 변환이 필요합니다."

    try:
        ole = olefile.OleFileIO(io.BytesIO(content))
    except Exception:
        return "HWP 파일 구조를 열 수 없습니다. HWPX로 변환 후 다시 업로드해주세요."

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
                header_value = struct.unpack_from("<I", raw, offset)[0]
                offset += 4
                tag_id = header_value & 0x3FF
                size = (header_value >> 20) & 0xFFF
                if size == 0xFFF:
                    if offset + 4 > len(raw):
                        break
                    size = struct.unpack_from("<I", raw, offset)[0]
                    offset += 4

                payload = raw[offset:offset + size]
                offset += size

                if tag_id == 67 and payload:
                    chunks.append(payload.decode("utf-16le", errors="ignore"))

        text = _clean_text(" ".join(chunks))
        return text or "HWP 본문 텍스트를 찾지 못했습니다. HWPX로 변환하면 더 안정적으로 분석할 수 있습니다."
    except Exception:
        return "HWP 본문 추출 중 오류가 발생했습니다. HWPX로 변환 후 다시 업로드해주세요."
    finally:
        ole.close()
