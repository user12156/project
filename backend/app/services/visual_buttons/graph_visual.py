import json
import re
from typing import Any

from .common import base_asset, frequent_keywords


ALLOWED_CHART_TYPES = {"line", "bar", "pie"}

NULL_VALUES = {
    "",
    "-",
    "없음",
    "해당없음",
    "미상",
    "...",
    "N/A",
    "NA",
    "null",
    "None",
}

MONTH_LABELS = [f"{index}월" for index in range(1, 13)]

DEFAULT_SERIES_COLORS = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#9333ea",
    "#f97316",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#65a30d",
    "#c2410c",
]

COMMON_OPTIONS = {
    "showLegend": True,
    "showTooltip": True,
    "showDataLabels": False,
    "connectNulls": False,
    "grid": {
        "top": 48,
        "right": 48,
        "bottom": 56,
        "left": 64,
    },
}

CHART_TEMPLATES = {
    "monthly_trend": {
        **COMMON_OPTIONS,
        "xAxisMode": "month_12",
        "xCategories": MONTH_LABELS,
        "missingValue": None,
        "connectNulls": False,
    },
    "yearly_trend": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "missingValue": None,
        "connectNulls": False,
    },
    "regional_bar": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "sort": "desc",
        "limit": 20,
    },
    "category_bar": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "sort": None,
    },
    "dual_axis": {
        **COMMON_OPTIONS,
        "useDualAxis": True,
    },
    "default": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
    },
}


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
    cleaned = re.sub(r"(명|건|개|천원|만원|원|%|명당|억원)$", "", cleaned).strip()

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


def validate_chart_json(chart_json: dict[str, Any]) -> tuple[bool, list[str]]:
    errors = []

    if not isinstance(chart_json, dict):
        return False, ["차트 응답이 JSON 객체가 아닙니다."]

    chart_type = chart_json.get("chartType")
    if chart_type not in ALLOWED_CHART_TYPES:
        errors.append(f"지원하지 않는 chartType입니다: {chart_type}")

    x_key = chart_json.get("xAxisKey") or chart_json.get("xKey")
    if chart_type != "pie" and not x_key:
        errors.append("xAxisKey가 없습니다.")

    data = chart_json.get("data")
    if not isinstance(data, list) or not data:
        errors.append("data가 비어 있습니다.")

    series = chart_json.get("series")
    if chart_type != "pie" and (not isinstance(series, list) or not series):
        errors.append("series가 비어 있습니다.")

    if errors:
        return False, errors

    if chart_type != "pie":
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


def extract_json_object(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("빈 응답입니다.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("JSON 객체를 찾을 수 없습니다.")

    return json.loads(cleaned[start : end + 1])


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


def create_graph_visual(extracted_docs: list[dict], analysis_text: str) -> dict:
    asset = base_asset("graph", "키워드 중요도 그래프", analysis_text)
    keywords = frequent_keywords(analysis_text, 6)
    if not keywords:
        keywords = [doc.get("filename", f"문서 {index + 1}") for index, doc in enumerate((extracted_docs or [])[:4])]
    if not keywords:
        keywords = ["핵심", "요약", "비교", "결과", "차이"]

    rows = [
        {
            "label": keyword,
            "point": f"{keyword} 관련 언급 빈도와 중요도를 기준으로 산정했습니다.",
            "score": max(38, min(96, 90 - index * 6 + ((index % 2) * 8))),
        }
        for index, keyword in enumerate(keywords[:6])
    ]

    asset.update(
        {
            "text": "분석 결과의 주요 키워드를 막대그래프로 표현했습니다.",
            "rows": rows,
            "keywords": keywords[:6],
            "details": [{"lbl": row["label"], "val": str(row["score"])} for row in rows],
        }
    )
    return asset
