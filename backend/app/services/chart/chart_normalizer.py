"""Normalize chart values, keys, and category axes."""

import re
from typing import Any

from app.services.chart.chart_constants import MONTH_LABELS, NULL_VALUES


def normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()
    if text in NULL_VALUES:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    cleaned = text.replace(",", "")
    cleaned = re.sub(r"(명|건|개|천원|만원|원|%|명당|달러)$", "", cleaned).strip()

    if re.fullmatch(r"-?\d+", cleaned):
        number = int(cleaned)
        return -number if negative else number

    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        number = float(cleaned)
        return -number if negative else number

    return value


def normalize_chart_data(data: list[dict]) -> list[dict]:
    normalized = []

    for row in data or []:
        new_row = {}
        for key, value in row.items():
            if key.lower() in {"name", "label", "month", "year", "region", "category", "date"}:
                new_row[key] = str(value).strip() if value is not None else None
            else:
                new_row[key] = normalize_value(value)
        normalized.append(new_row)

    return normalized


def normalize_monthly_axis(data: list[dict], x_key: str = "month") -> list[dict]:
    by_month = {}

    for row in data or []:
        month = row.get(x_key)
        if month is None:
            continue

        match = re.search(r"(\d{1,2})", str(month).strip())
        if not match:
            continue

        month_number = int(match.group(1))
        if not 1 <= month_number <= 12:
            continue

        month_label = f"{month_number}월"
        by_month[month_label] = {
            **row,
            x_key: month_label,
            "monthOrder": month_number,
        }

    result = []
    for index, month_label in enumerate(MONTH_LABELS, start=1):
        result.append(by_month.get(month_label, {x_key: month_label, "monthOrder": index}))

    return result


def ensure_chart_keys(chart_json: dict) -> dict:
    if "xAxisKey" not in chart_json and "xKey" in chart_json:
        chart_json["xAxisKey"] = chart_json["xKey"]

    for item in chart_json.get("series", []) or []:
        if "dataKey" not in item and "key" in item:
            item["dataKey"] = item["key"]

        if "name" not in item and "label" in item:
            item["name"] = item["label"]

        if "yAxisId" not in item:
            item["yAxisId"] = "left"

    return chart_json
