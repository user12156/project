"""Extract structured tables from uploaded document units."""

from typing import Any

from app.services.table.table_detector import detect_tables_from_docs
from app.services.table.table_parser import parse_tables


def extract_tables(extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return parse_tables(detect_tables_from_docs(extracted_docs))
