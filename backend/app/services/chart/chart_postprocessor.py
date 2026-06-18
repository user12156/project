"""Coordinate chart JSON parsing, normalization, templating, and validation."""

import json
from typing import Any

from app.services.chart.chart_constants import CHART_TEMPLATES, DEFAULT_SERIES_COLORS
from app.services.chart.chart_normalizer import ensure_chart_keys, normalize_chart_data, normalize_monthly_axis
from app.services.chart.chart_parser import extract_json_object
from app.services.chart.chart_validator import validate_chart_json


def guess_template(chart_json: dict) -> str:
    title = str(chart_json.get("title", ""))
    x_key = str(chart_json.get("xAxisKey", chart_json.get("xKey", "")))
    data = chart_json.get("data") or []
    sample_labels = " ".join(str(row.get(x_key, "")) for row in data[:12])

    if "월" in title or "월별" in title or "월" in sample_labels or x_key.lower() == "month":
        return "monthly_trend"

    if "지역" in title or x_key.lower() in {"region", "area"}:
        return "regional_bar"

    if "연도" in title or x_key.lower() == "year":
        return "yearly_trend"

    series = chart_json.get("series") or []
    y_axis_ids = {item.get("yAxisId") for item in series if item.get("yAxisId")}
    if len(y_axis_ids) >= 2:
        return "dual_axis"

    return "default"


def apply_template(chart_json: dict) -> dict:
    template_name = chart_json.get("template") or guess_template(chart_json)
    template = CHART_TEMPLATES.get(template_name, CHART_TEMPLATES["default"])

    chart_json["template"] = template_name
    chart_json["options"] = {
        **template,
        **chart_json.get("options", {}),
    }

    return chart_json


def apply_series_colors(chart_json: dict[str, Any]) -> dict[str, Any]:
    series = chart_json.get("series") or []

    for index, item in enumerate(series):
        item["color"] = DEFAULT_SERIES_COLORS[index % len(DEFAULT_SERIES_COLORS)]

    chart_json["series"] = series
    return chart_json


def postprocess_chart_json(chart_json: dict[str, Any]) -> dict[str, Any]:
    chart_json = ensure_chart_keys(chart_json)
    chart_json = apply_template(chart_json)
    chart_json = apply_series_colors(chart_json)

    data = normalize_chart_data(chart_json.get("data") or [])
    x_key = chart_json.get("xAxisKey")

    if chart_json.get("options", {}).get("xAxisMode") == "month_12" and x_key:
        data = normalize_monthly_axis(data, x_key=x_key)

    chart_json["data"] = data

    valid, errors = validate_chart_json(chart_json)
    if not valid:
        chart_json["type"] = "chart_error"
        chart_json["errors"] = errors

    return chart_json


def process_chart_response(answer: str) -> str:
    chart_json = extract_json_object(answer)
    chart_json = postprocess_chart_json(chart_json)
    return json.dumps(chart_json, ensure_ascii=False)
