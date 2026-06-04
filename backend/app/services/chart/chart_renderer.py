import json
import re
from typing import Any

from app.services.chart.chart_normalizer import (
    normalize_chart_data,
    normalize_monthly_axis,
)
from app.services.chart.chart_spec import (
    ensure_chart_keys,
    validate_chart_json,
)
from app.services.chart.chart_templates import (
    DEFAULT_SERIES_COLORS,
    apply_template,
)


def extract_json_object(text: str) -> dict[str, Any]:
    """
    LLM 응답에서 JSON 객체만 안전하게 추출.
    ```json ... ``` 형태도 처리.
    """
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
    """
    여러 선/막대가 같은 색으로 나오는 문제를 막기 위해
    series 순서대로 기본 색상을 강제로 배정한다.
    """
    series = chart_json.get("series") or []

    for index, item in enumerate(series):
        item["color"] = DEFAULT_SERIES_COLORS[index % len(DEFAULT_SERIES_COLORS)]

    chart_json["series"] = series
    return chart_json


def postprocess_chart_json(chart_json: dict[str, Any]) -> dict[str, Any]:
    chart_json = ensure_chart_keys(chart_json)
    chart_json = apply_template(chart_json)
    chart_json = apply_series_colors(chart_json)

    data = chart_json.get("data") or []
    data = normalize_chart_data(data)

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
    """
    llm_analysis.py에서 OpenAI 응답을 받은 직후 호출.
    반환값은 다시 JSON 문자열.
    """
    chart_json = extract_json_object(answer)
    chart_json = postprocess_chart_json(chart_json)
    return json.dumps(chart_json, ensure_ascii=False)