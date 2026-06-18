"""Parse graph requests into reusable chart selection conditions."""

import re
from typing import Any


def detect_period(question: str) -> str:
    text = question or ""
    if "1~3월" in text or "1-3월" in text or "누계" in text:
        return "quarter_1"
    month_match = re.search(r"(\d{1,2})월", text)
    if month_match:
        return "month"
    return "year"


def parse_chart_request(question: str) -> dict[str, Any]:
    text = question or ""
    lowered = text.lower()

    year_match = re.search(r"(20\d{2})", text)
    year = year_match.group(1) if year_match else None
    month_match = re.search(r"(\d{1,2})월", text)
    month = int(month_match.group(1)) if month_match else None

    if "막대" in text or "bar" in lowered:
        chart_type = "bar"
    elif "선" in text or "꺾은선" in text or "line" in lowered:
        chart_type = "line"
    elif "월별" in text or "연도별" in text or "추이" in text:
        chart_type = "line"
    else:
        chart_type = "bar"

    if any(token in text for token in ("시도별", "지역별", "지역", "전국", "서울", "부산", "경기")):
        dimension = "region"
    elif "월별" in text:
        dimension = "month"
    elif "연도별" in text or "추이" in text:
        dimension = "year"
    else:
        dimension = None

    metrics = []
    if "조출생률" in text or "출생률" in text or "birth rate" in lowered:
        metrics.append("crude_birth_rate")
    if "출생" in text or "birth" in lowered:
        metrics.append("birth_count")
    if "사망" in text or "death" in lowered:
        metrics.append("death_count")
    if "혼인" in text or "marriage" in lowered:
        metrics.append("marriage_count")
    if "이혼" in text or "divorce" in lowered:
        metrics.append("divorce_count")
    if "자연증가" in text or "자연 증가" in text or "natural" in lowered:
        metrics.append("natural_increase")

    return {
        "year": year,
        "month": month,
        "dimension": dimension,
        "metric": metrics[0] if metrics else None,
        "metrics": metrics,
        "chart_type": chart_type,
        "period": detect_period(text),
    }
