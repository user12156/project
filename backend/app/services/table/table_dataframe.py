"""Convert extracted table candidates into a normalized row-frame.

The project does not require pandas at runtime. This module uses a simple
list-of-dicts "DataFrame" shape so the rest of the pipeline can query one
standard form whether the source was structured rows or loose table text.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.chart.chart_normalizer import normalize_value
from app.services.table.column_matcher import find_region_column
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


logger = logging.getLogger(__name__)


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


def table_to_fallback_text(table: TableRecord) -> str:
    parts = []
    for key in ("title", "headers", "columns", "rows", "text"):
        value = table.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def cut_to_table_body(clean: str) -> str:
    markers = [
        "[\ud45c2]\uc2dc\ub3c4\ubcc4\ucd9c\uc0dd\uc544\uc218",
        "\ub204\uacc4\uc804\ub144\ub204\uacc4\ube44",
        "\uc804\uad6d238,317",
        "\uc804\uad6d238317",
    ]
    positions = []
    for marker in markers:
        pos = clean.find(marker)
        if pos >= 0:
            positions.append(pos)
    if positions:
        return clean[max(positions):]
    return clean


def _cut_to_spaced_table_body(text: str) -> str:
    markers = [
        r"\[\s*\ud45c\s*2\s*\]\s*\uc2dc\ub3c4\ubcc4\s*\ucd9c\uc0dd\uc544\s*\uc218",
        r"\ub204\uacc4\s*\uc804\ub144\ub204\uacc4\ube44",
        r"\uc804\uad6d\s*238,317",
        r"\uc804\uad6d\s*238317",
    ]
    positions = []
    for marker in markers:
        match = re.search(marker, text)
        if match:
            positions.append(match.start())
    if positions:
        return text[max(positions):]
    return text


def fallback_region_birth_rows_from_text(text: str, request: ChartRequest | None = None) -> TableDataFrame:
    """Best-effort fallback for regional birth charts when table cells are missing."""

    rows: TableDataFrame = []
    spaced = re.sub(r"\s+", " ", str(text or "")).strip()
    spaced = _cut_to_spaced_table_body(spaced)
    request = request or {}
    metric = request.get("metric") or "birth_count"
    year = str(request.get("year") or "")
    month = request.get("month")
    period = request.get("period") or "year"
    regions = [region for region in FALLBACK_REGIONS if region != "\uc804\uad6d"]

    for index, region in enumerate(regions):
        start_match = re.search(rf"{re.escape(region)}\s*-?\d[\d,]*(?:\.\d+)?", spaced)
        if not start_match:
            continue
        start = start_match.start()

        end_candidates = []
        for next_region in regions[index + 1:]:
            next_match = re.search(
                rf"{re.escape(next_region)}\s*-?\d[\d,]*(?:\.\d+)?",
                spaced[start + len(region):],
            )
            if next_match:
                end_candidates.append(start + len(region) + next_match.start())

        end = min(end_candidates) if end_candidates else len(spaced)
        segment = spaced[start + len(region):end]
        numbers = re.findall(r"-?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)", segment)
        values = [parse_number(number) for number in numbers]
        values = [value for value in values if value is not None]
        if not values:
            continue

        value_index = 0
        if year == "2024" and period == "year":
            value_index = 0
        elif year == "2025" and period == "year":
            value_index = 1
        elif year == "2025" and month == 3:
            value_index = 2
        elif year == "2025" and period in ("quarter_1", "1~3\uc6d4"):
            value_index = 3
        elif year == "2026" and month == 2:
            value_index = 4
        elif year == "2026" and month == 3:
            value_index = 5
        elif year == "2026" and metric == "crude_birth_rate":
            value_index = 6
        elif year == "2026" and period in ("quarter_1", "1~3\uc6d4"):
            value_index = 7

        if value_index >= len(values):
            continue

        value = values[value_index]
        if value is None:
            continue

        rows.append(
            {
                "region": region,
                "year": year or None,
                "month": month,
                "period": period,
                "metric": metric,
                "value": value,
                "source_col": f"fallback_text_index_{value_index}",
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
        fallback_rows = fallback_region_birth_rows_from_text(table_to_fallback_text(table), request)
        logger.info("fallback rows count=%s", len(fallback_rows))
        logger.info("fallback rows sample=%s", fallback_rows[:5])
        return fallback_rows

    return []
