"""Validate chart JSON before it is returned to the client."""

from typing import Any

from app.services.chart.chart_constants import ALLOWED_CHART_TYPES


def validate_chart_json(chart_json: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(chart_json, dict):
        return False, ["차트 응답이 JSON 객체가 아닙니다."]

    if chart_json.get("type") == "chart_error":
        return True, []

    chart_type = chart_json.get("chartType")
    if chart_type not in ALLOWED_CHART_TYPES:
        errors.append(f"지원하지 않는 chartType입니다: {chart_type}")

    x_key = chart_json.get("xAxisKey") or chart_json.get("xKey")
    if not x_key:
        errors.append("xAxisKey가 없습니다.")

    data = chart_json.get("data")
    if not isinstance(data, list) or not data:
        errors.append("data가 비어 있습니다.")

    series = chart_json.get("series")
    if not isinstance(series, list) or not series:
        errors.append("series가 비어 있습니다.")

    if errors:
        return False, errors

    for index, row in enumerate(data):
        if x_key not in row:
            errors.append(f"{index}번째 data row에 xAxisKey '{x_key}'가 없습니다.")

    for item in series:
        data_key = item.get("dataKey") or item.get("key")
        if not data_key:
            errors.append("series 항목에 dataKey가 없습니다.")
            continue

        if not any(data_key in row for row in data):
            errors.append(f"series dataKey '{data_key}'가 data에 존재하지 않습니다.")

    return len(errors) == 0, errors
