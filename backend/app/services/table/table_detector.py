"""Detect table markers such as [표 1], 표 1, and [Table 1]."""

import re
from typing import Any


TABLE_WORD = "\uD45C"
TABLE_PATTERN = rf"(?:\[\s*{TABLE_WORD}\s*\d+\s*\]|{TABLE_WORD}\s*\d+|\[\s*Table\s*\d+\s*\])"
TABLE_MARKER_RE = re.compile(TABLE_PATTERN, re.IGNORECASE)


def _table_title(marker_line: str, following_text: str, marker: str) -> str:
    after_marker = marker_line.split(marker, 1)[-1].strip(" :-\t")
    if after_marker:
        return after_marker[:120]

    for line in following_text.splitlines():
        cleaned = line.strip()
        if cleaned and not TABLE_MARKER_RE.search(cleaned):
            return cleaned[:120]
    return marker


def detect_tables_from_text(text: str, filename: str = "document") -> list[dict[str, Any]]:
    source = str(text or "")
    matches = list(TABLE_MARKER_RE.finditer(source))
    tables = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        segment = source[start:end].strip()
        marker = match.group(0)
        marker_line = segment.splitlines()[0] if segment else marker
        title = _table_title(marker_line, "\n".join(segment.splitlines()[1:]), marker)
        tables.append(
            {
                "id": f"{filename}:{marker}",
                "marker": marker,
                "title": title,
                "text": segment,
                "filename": filename,
            }
        )

    return tables


def _doc_text_candidates(doc: dict[str, Any]) -> list[str]:
    candidates = [str(doc.get("text") or "")]

    for unit in doc.get("source_units", []) or []:
        candidates.append(str(unit.get("text") or ""))

    for asset in doc.get("visual_assets", []) or []:
        candidates.append(str(asset.get("table_text") or ""))
        candidates.append(str(asset.get("ocr_text") or ""))
        candidates.append(str(asset.get("text") or ""))

    return [candidate for candidate in candidates if candidate.strip()]


def detect_tables_from_docs(extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tables = []
    seen: set[tuple[str, str]] = set()

    for doc in extracted_docs or []:
        filename = str(doc.get("filename") or "document")
        for text in _doc_text_candidates(doc):
            for table in detect_tables_from_text(text, filename=filename):
                dedupe_key = (table.get("id", ""), table.get("text", "")[:200])
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                tables.append(table)

    return tables
