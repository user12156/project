"""Extract structured table candidates from uploaded document units."""

import logging
from typing import Any

from app.services.table.table_detector import detect_tables_from_docs
from app.services.table.table_parser import parse_tables


logger = logging.getLogger(__name__)


def extract_tables(extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return parse_tables(detect_tables_from_docs(extracted_docs))


def collect_tables(extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect parsed tables, raw table payloads, and document text fallback candidates."""

    raw_tables: list[dict[str, Any]] = []

    for doc_index, doc in enumerate(extracted_docs or []):
        logger.info(
            "doc[%s] filename=%s text_len=%s source_units=%s visual_assets=%s raw_tables=%s",
            doc_index,
            doc.get("filename"),
            len(str(doc.get("text") or "")),
            len(doc.get("source_units", []) or []),
            len(doc.get("visual_assets", []) or []),
            len(doc.get("tables", []) or []),
        )

        for table in doc.get("tables", []) or []:
            copied = dict(table)
            copied["filename"] = doc.get("filename")
            raw_tables.append(copied)

        text = str(doc.get("text") or "")
        if text:
            raw_tables.append(
                {
                    "title": doc.get("filename") or "document_text",
                    "text": text,
                    "headers": None,
                    "columns": [],
                    "rows": [],
                    "filename": doc.get("filename"),
                }
            )

    return [*extract_tables(extracted_docs), *raw_tables]
