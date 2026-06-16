"""Build chart JSON from extracted document tables before using an LLM."""

import logging
import re
from typing import Any

from app.services.chart.chart_normalizer import normalize_value
from app.services.chart.chart_postprocessor import postprocess_chart_json
from app.services.table.chart_request_parser import parse_chart_request
from app.services.table.column_matcher import find_region_column, find_year_metric_column
from app.services.table.table_extractor import extract_tables
from app.services.table.table_matcher import find_best_table, table_to_search_text
from app.services.table.table_to_chart import (
    METRIC_LABELS,
    REGION_ORDER,
    build_chart_from_table,
    normalize_region,
    validate_birth_region_chart,
)


logger = logging.getLogger(__name__)


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


def _parse_fallback_number(value: str) -> int | float | None:
    normalized = str(value or "").replace(",", "").strip()
    try:
        return int(normalized)
    except ValueError:
        try:
            return float(normalized)
        except ValueError:
            return None


def fallback_region_birth_rows_from_text(text: str) -> list[dict[str, Any]]:
    """Best-effort fallback for regional birth charts when table rows are missing."""

    rows: list[dict[str, Any]] = []
    clean = re.sub(r"\s+", "", str(text or ""))

    for region in FALLBACK_REGIONS:
        match = re.search(rf"{re.escape(region)}([0-9][0-9,]*(?:\.\d+)?)", clean)
        if not match:
            continue

        value = _parse_fallback_number(match.group(1))
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


def collect_tables(extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    parsed_tables = extract_tables(extracted_docs)
    return [*parsed_tables, *raw_tables]


def _column_key(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        return str(column.get("key") or column.get("label") or "")
    return str(column or "")


def _column_text(column: str | dict[str, Any]) -> str:
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


def _infer_metric(column_text: str, table_title: str) -> str | None:
    text = f"{table_title} {column_text}"
    if "조출생률" in text or "출생률" in text or "birth rate" in text.lower():
        return "crude_birth_rate"
    if "출생" in text or "birth" in text.lower():
        return "birth_count"
    if "사망" in text or "death" in text.lower():
        return "death_count"
    if "혼인" in text or "marriage" in text.lower():
        return "marriage_count"
    if "이혼" in text or "divorce" in text.lower():
        return "divorce_count"
    if "자연증가" in text or "자연 증가" in text or "natural" in text.lower():
        return "natural_increase"
    return None


def _infer_period(column_text: str) -> tuple[str, int | None]:
    if "1~3월" in column_text or "1-3월" in column_text or "누계" in column_text:
        return "quarter_1", None

    month_match = re.search(r"(\d{1,2})월", column_text)
    if month_match:
        return "month", int(month_match.group(1))

    return "year", None


def _normalize_table_rows(table: dict[str, Any], default_metric: str | None = None) -> list[dict[str, Any]]:
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    if not columns and rows and isinstance(rows[0], dict):
        columns = list(rows[0].keys())

    region_col = find_region_column(columns)
    title = str(table.get("title") or "")
    normalized_rows: list[dict[str, Any]] = []

    if not region_col:
        return normalized_rows

    for row in rows or []:
        if not isinstance(row, dict):
            continue

        region = normalize_region(row.get(region_col))
        if not region:
            continue

        for column in columns:
            key = _column_key(column)
            if not key or key == region_col:
                continue

            column_text = _column_text(column)
            year_match = re.search(r"(20\d{2})", column_text)
            if not year_match:
                continue

            metric = _infer_metric(column_text, title) or default_metric
            if not metric:
                continue

            value = normalize_value(row.get(key))
            if not isinstance(value, (int, float)):
                continue

            period, month = _infer_period(column_text)
            normalized_rows.append(
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

    return normalized_rows


def _build_chart_from_normalized_rows(
    request: dict[str, Any],
    normalized_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if request.get("dimension") != "region":
        return None

    matched_rows = [
        row
        for row in normalized_rows
        if row.get("year") == request.get("year")
        and row.get("metric") == request.get("metric")
        and row.get("period") == request.get("period")
        and (request.get("period") != "month" or row.get("month") == request.get("month"))
    ]

    if len(matched_rows) < 2:
        return None

    order = {region: index for index, region in enumerate([*FALLBACK_REGIONS, *REGION_ORDER])}
    matched_rows.sort(key=lambda row: order.get(row["region"], len(REGION_ORDER)))
    is_fallback_text = any(row.get("source_col") == "fallback_text" for row in matched_rows)
    data = [
        {"category": row["region"], "value": row["value"]}
        for row in matched_rows
        if not (is_fallback_text and row.get("region") == "\uc804\uad6d")
    ]
    if len(data) < 2:
        return None

    if request.get("metric") == "birth_count" and request.get("period") == "year":
        if not validate_birth_region_chart(request.get("year"), data):
            return {
                "type": "chart_error",
                "message": "정규화된 표 값이 연간 시도별 출생아 수 범위와 맞지 않습니다.",
            }

    metric_label = METRIC_LABELS.get(request.get("metric"), "값")
    year_prefix = f"{request.get('year')}년 " if request.get("year") else ""
    month_prefix = f"{request.get('month')}월 " if request.get("period") == "month" and request.get("month") else ""
    quarter_prefix = "1~3월 누계 " if request.get("period") == "quarter_1" else ""

    return {
        "type": "chart",
        "chartType": request.get("chart_type") or "bar",
        "template": "regional_bar",
        "title": f"{year_prefix}{month_prefix}{quarter_prefix}{metric_label} 비교",
        "xAxisKey": "category",
        "series": [{"dataKey": "value", "name": metric_label, "yAxisId": "left"}],
        "data": data,
    }


def try_build_chart_from_tables(question: str, extracted_docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    request = parse_chart_request(question)
    logger.info("parsed request=%s", request)

    if not request.get("metric") or not request.get("dimension"):
        return None

    tables = collect_tables(extracted_docs)
    logger.info("tables count=%s", len(tables))
    for index, candidate in enumerate(tables):
        logger.info("table[%s] title=%s", index, candidate.get("title"))
        logger.info("table[%s] headers=%s", index, candidate.get("headers"))
        logger.info("table[%s] rows sample=%s", index, candidate.get("rows", [])[:3])
        logger.info("table[%s] search_text=%s", index, table_to_search_text(candidate)[:500])

    if not tables:
        logger.info("matched table=%s", None)
        return None

    table = find_best_table(request, tables)
    logger.info("matched table=%s", table.get("title") if table else None)
    if not table:
        return None

    logger.info("columns=%s", table.get("columns"))
    logger.info("first row=%s", table.get("rows", [None])[0] if table.get("rows") else None)
    logger.info("raw headers=%s", table.get("headers"))
    logger.info("raw rows sample=%s", table.get("rows", [])[:3])

    normalized_rows = _normalize_table_rows(table, default_metric=request.get("metric"))
    if (
        not normalized_rows
        and request.get("dimension") == "region"
        and request.get("metric") == "birth_count"
    ):
        fallback_rows = fallback_region_birth_rows_from_text(table_to_search_text(table))
        for row in fallback_rows:
            row["year"] = request.get("year")
            row["month"] = request.get("month")
            row["period"] = request.get("period") or "year"
            row["metric"] = request.get("metric")
        normalized_rows = fallback_rows
        logger.warning("fallback normalized rows=%s", normalized_rows[:10])

    logger.info("normalized rows sample=%s", normalized_rows[:10])
    normalized_chart = _build_chart_from_normalized_rows(request, normalized_rows)
    if normalized_chart:
        logger.info("chart data count=%s", len(normalized_chart.get("data", [])))
        return postprocess_chart_json(normalized_chart)
    if normalized_rows and request.get("dimension") == "region":
        return postprocess_chart_json(
            {
                "type": "chart_error",
                "message": "정규화된 표에서 요청한 year/month/period/metric 조합을 찾지 못했습니다.",
            }
        )

    columns = table.get("columns", [])
    x_col = None
    if request.get("dimension") == "region":
        x_col = find_region_column(columns)
    elif request.get("dimension") == "month":
        x_col = "month" if any((column.get("key") if isinstance(column, dict) else column) == "month" for column in columns) else None
    elif request.get("dimension") == "year":
        x_col = "year" if any((column.get("key") if isinstance(column, dict) else column) == "year" for column in columns) else None

    y_col = find_year_metric_column(
        columns=columns,
        year=request.get("year"),
        metric=request.get("metric"),
        period=request.get("period") or "year",
    )
    logger.info("selected x_col=%s y_col=%s", x_col, y_col)

    if not x_col or not y_col:
        return None

    chart_json = build_chart_from_table(
        request=request,
        table=table,
        x_col=x_col,
        y_col=y_col,
    )
    logger.info("chart data count=%s", len(chart_json.get("data", [])) if chart_json else 0)

    if not chart_json:
        return None

    return postprocess_chart_json(chart_json)
