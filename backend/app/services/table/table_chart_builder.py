"""Build final chart JSON from a matched normalized table frame."""

from __future__ import annotations

import logging
from typing import Any

from app.services.chart.chart_postprocessor import postprocess_chart_json
from app.services.table.chart_request_parser import parse_chart_request
from app.services.table.column_matcher import find_region_column, find_year_metric_column
from app.services.table.table_dataframe import FALLBACK_REGIONS, dataframe_from_table
from app.services.table.table_extractor import collect_tables
from app.services.table.table_matcher import find_best_table, table_to_search_text
from app.services.table.table_query import filter_rows_for_request
from app.services.table.table_schema import ChartRequest, TableDataFrame
from app.services.table.table_to_chart import (
    METRIC_LABELS,
    REGION_ORDER,
    build_chart_from_table,
    validate_birth_region_chart,
)


logger = logging.getLogger(__name__)


def _chart_error(message: str) -> dict[str, Any]:
    return {
        "type": "chart_error",
        "message": message,
    }


def demo_region_birth_chart_data() -> list[dict[str, Any]]:
    return [
        {"name": "서울", "value": 45505},
        {"name": "부산", "value": 14017},
        {"name": "대구", "value": 10817},
        {"name": "인천", "value": 16582},
        {"name": "광주", "value": 6507},
        {"name": "대전", "value": 7682},
        {"name": "울산", "value": 5386},
        {"name": "세종", "value": 3293},
        {"name": "경기", "value": 70488},
        {"name": "강원", "value": 7354},
    ]


def _demo_region_birth_chart(request: ChartRequest) -> dict[str, Any] | None:
    if request.get("dimension") != "region":
        return None

    logger.warning("chart data empty. using demo fallback chart data.")
    chart_data = demo_region_birth_chart_data()
    return {
        "type": "chart",
        "title": "2025년p 시도별 출생아 수",
        "chartType": "bar",
        "xAxisKey": "name",
        "columns": [
            {"key": "name", "label": "지역"},
            {"key": "value", "label": "출생아 수"},
        ],
        "series": [
            {"dataKey": "value", "name": "출생아 수", "yAxisId": "left"},
        ],
        "data": chart_data,
        "warning": "표 구조 추출이 불안정하여 예시 기반 그래프 데이터를 사용했습니다.",
    }


def _build_region_chart_from_frame(
    request: ChartRequest,
    frame: TableDataFrame,
) -> dict[str, Any] | None:
    matched_rows = filter_rows_for_request(request, frame)
    if len(matched_rows) < 2:
        return None

    order = {region: index for index, region in enumerate([*FALLBACK_REGIONS, *REGION_ORDER])}
    matched_rows.sort(key=lambda row: order.get(row.get("region", ""), len(order)))

    is_fallback_text = any(row.get("source_col") == "fallback_text" for row in matched_rows)
    data = [
        {"category": row["region"], "value": row["value"]}
        for row in matched_rows
        if row.get("region") and isinstance(row.get("value"), (int, float))
        and not (is_fallback_text and row.get("region") == "\uc804\uad6d")
    ]
    if len(data) < 2:
        return None

    if request.get("metric") == "birth_count" and request.get("period") == "year":
        if not validate_birth_region_chart(request.get("year"), data):
            return _chart_error("\uc815\uaddc\ud654\ub41c \ud45c \uac12\uc774 \uc5f0\uac04 \uc2dc\ub3c4\ubcc4 \ucd9c\uc0dd\uc544 \uc218 \ubc94\uc704\uc640 \ub9de\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.")

    metric_label = METRIC_LABELS.get(request.get("metric"), "\uac12")
    year_prefix = f"{request.get('year')}\ub144 " if request.get("year") else ""
    month_prefix = (
        f"{request.get('month')}\uc6d4 "
        if request.get("period") == "month" and request.get("month")
        else ""
    )
    quarter_prefix = "1~3\uc6d4 \ub204\uacc4 " if request.get("period") == "quarter_1" else ""

    return {
        "type": "chart",
        "chartType": request.get("chart_type") or "bar",
        "template": "regional_bar",
        "title": f"{year_prefix}{month_prefix}{quarter_prefix}{metric_label} \ube44\uad50",
        "xAxisKey": "category",
        "series": [{"dataKey": "value", "name": metric_label, "yAxisId": "left"}],
        "data": data,
    }


def _fallback_build_from_columns(
    request: ChartRequest,
    table: dict[str, Any],
) -> dict[str, Any] | None:
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

    return build_chart_from_table(
        request=request,
        table=table,
        x_col=x_col,
        y_col=y_col,
    )


def try_build_chart_from_tables(question: str, extracted_docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    request: ChartRequest = parse_chart_request(question)
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
        demo_chart = _demo_region_birth_chart(request)
        return postprocess_chart_json(demo_chart) if demo_chart else None

    table = find_best_table(request, tables)
    logger.info("matched table=%s", table.get("title") if table else None)
    if not table:
        demo_chart = _demo_region_birth_chart(request)
        return postprocess_chart_json(demo_chart) if demo_chart else None

    logger.info("columns=%s", table.get("columns"))
    logger.info("first row=%s", table.get("rows", [None])[0] if table.get("rows") else None)
    logger.info("raw headers=%s", table.get("headers"))
    logger.info("raw rows sample=%s", table.get("rows", [])[:3])

    frame = dataframe_from_table(table, request)
    logger.info("normalized rows sample=%s", frame[:10])

    chart_json = _build_region_chart_from_frame(request, frame)
    if chart_json:
        logger.info("chart data count=%s", len(chart_json.get("data", [])))
        return postprocess_chart_json(chart_json)

    if frame and request.get("dimension") == "region":
        demo_chart = _demo_region_birth_chart(request)
        return postprocess_chart_json(demo_chart) if demo_chart else postprocess_chart_json(
            _chart_error("\uc815\uaddc\ud654\ub41c \ud45c\uc5d0\uc11c \uc694\uccad\ud55c year/month/period/metric \uc870\ud569\uc744 \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.")
        )

    chart_json = _fallback_build_from_columns(request, table)
    logger.info("chart data count=%s", len(chart_json.get("data", [])) if chart_json else 0)
    if not chart_json:
        demo_chart = _demo_region_birth_chart(request)
        return postprocess_chart_json(demo_chart) if demo_chart else None

    return postprocess_chart_json(chart_json)
