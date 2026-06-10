# 서비스: TXT, CSV, MD, DOCX 텍스트 추출 기능을 제공합니다.
"""TXT, CSV, Markdown, and DOCX text extraction."""

import io
import zipfile
from typing import Iterable
from xml.etree import ElementTree

from app.services.analysis.answer_builder import _clean_text


TEXT_EXTENSIONS = {".txt", ".md", ".csv"}


def extract_text(content: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _iter_zip_xml_text(content: bytes, wanted_suffixes: Iterable[str]) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            lower_name = name.lower()
            if not lower_name.endswith(".xml"):
                continue
            if wanted_suffixes and not any(lower_name.endswith(suffix) for suffix in wanted_suffixes):
                continue
            try:
                root = ElementTree.fromstring(archive.read(name))
            except ElementTree.ParseError:
                continue
            for node in root.iter():
                if node.text and node.text.strip():
                    texts.append(node.text.strip())
    return _clean_text(" ".join(texts))


def extract_docx(content: bytes) -> str:
    return _iter_zip_xml_text(content, ("word/document.xml",))
