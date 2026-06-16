"""Convert extracted table candidates into a normalized row-frame.

The project does not require pandas at runtime. This module uses a simple
list-of-dicts "DataFrame" shape so the rest of the pipeline can query one
standard form whether the source was structured rows or loose table text.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.chart.chart_normalizer import normalize_value
from app.services.table.column_matcher import find_region_column
from app.services.table.table_matcher import table_to_search_text
from app.services.table.table_schema import ChartRequest, TableDataFrame, TableRecord
from app.services.table.table_to_chart import normalize_region


FALLBACK_REGIONS = [
    "\uc804\uad6d",
    "\uc11c\uc6b8",
    "\ubd80\uc0b0",
    "\ub300\uad6c",
    "\uc778\ucc9c",
    "\uad11\uc8fc",
    "\ub300\uc804",
    "\uc6b8\uc0b0",
    "\uc138\uc885",
    "\uacbd\uae30",
    "\uac15\uc6d0",
    "\ucda9\ubd81",
    "\ucda9\ub0a8",
    "\uc804\ubd81",
    "\uc804\ub0a8",
    "\uacbd\ubd81",
    "\uacbd\ub0a8",
    "\uc81c\uc8fc",
]


def column_key(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        return str(column.get("key") or column.get("label") or "")
    return str(column or "")


def column_text(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        parts = [
            column.get("key"),
            column.get("label"),
            column.get("header"),
            column.get("title"),
            column.get("name"),
        ]
        return " ".join(str(part) for part in parts if part)
    return str(column or "")


def infer_metric(column_text_value: str, table_title: str, default_metric: str | None = None) -> str | None:
    text = f"{table_title} {column_text_value}".lower()
    if any(token in text for token in ("\uc870\ucd9c\uc0dd\ub960", "\ucd9c\uc0dd\ub960", "birth rate")):
        return "crude_birth_rate"
    if any(token in text for token in ("\ucd9c\uc0dd", "birth")):
        return "birth_count"
    if any(token in text for token in ("\uc0ac\ub9dd", "death")):
        return "death_count"
    if any(token in text for token in ("\ud63c\uc778", "marriage")):
        return "marriage_count"
    if any(token in text for token in ("\uc774\ud63c", "divorce")):
        return "divorce_count"
    if any(token in text for token in ("\uc790\uc5f0\uc99d\uac00", "\uc790\uc5f0 \uc99d\uac00", "natural")):
        return "natural_increase"
    return default_metric


def infer_period(column_text_value: str) -> tuple[str, int | None]:
    if any(token in column_text_value for token in ("1~3\uc6d4", "1-3\uc6d4", "\ub204\uacc4")):
        return "quarter_1", None

    month_match = re.search(r"(\d{1,2})\uc6d4", column_text_value)
    if month_match:
        return "month", int(month_match.group(1))

    return "year", None


def parse_number(value: str) -> int | float | None:
    normalized = str(value or "").replace(",", "").strip()
    try:
        return int(normalized)
    except ValueError:
        try:
            return float(normalized)
        except ValueError:
            return None


def fallback_region_birth_rows_from_text(text: str) -> TableDataFrame:
    """Best-effort fallback for regional birth charts when table cells are missing."""

    rows: TableDataFrame = []
    clean = re.sub(r"\s+", "", str(text or ""))

    for region in FALLBACK_REGIONS:
        match = re.search(rf"{re.escape(region)}([0-9][0-9,]*(?:\.\d+)?)", clean)
        if not match:
            continue

        value = parse_number(match.group(1))
        if value is None:
            continue

        rows.append(
            {
                "region": region,
                "year": None,
                "month": None,
                "period": "year",
                "metric": "birth_count",
                "value": value,
                "source_col": "fallback_text",
            }
        )

    return rows


def dataframe_from_table(table: TableRecord, request: ChartRequest) -> TableDataFrame:
    columns = table.get("columns", []) or []
    rows = table.get("rows", []) or []
    if not columns and rows and isinstance(rows[0], dict):
        columns = list(rows[0].keys())

    frame: TableDataFrame = []
    region_col = find_region_column(columns)
    title = str(table.get("title") or "")

    if region_col:
        for row in rows:
            if not isinstance(row, dict):
                continue

            region = normalize_region(row.get(region_col))
            if not region:
                continue

            for column in columns:
                key = column_key(column)
                if not key or key == region_col:
                    continue

                header_text = column_text(column)
                year_match = re.search(r"(20\d{2})", header_text)
                if not year_match:
                    continue

                metric = infer_metric(header_text, title, request.get("metric"))
                if not metric:
                    continue

                value = normalize_value(row.get(key))
                if not isinstance(value, (int, float)):
                    continue

                period, month = infer_period(header_text)
                frame.append(
                    {
                        "region": region,
                        "year": year_match.group(1),
                        "month": month,
                        "period": period,
                        "metric": metric,
                        "value": value,
                        "source_col": key,
                    }
                )

    if frame:
        return frame

    if request.get("dimension") == "region" and request.get("metric") == "birth_count":
        fallback_rows = fallback_region_birth_rows_from_text(table_to_search_text(table))
        for row in fallback_rows:
            row["year"] = request.get("year")
            row["month"] = request.get("month")
            row["period"] = request.get("period") or "year"
            row["metric"] = request.get("metric") or "birth_count"
        return fallback_rows

    return []

