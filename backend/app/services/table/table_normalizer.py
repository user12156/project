"""Normalize table values and field names for chart generation."""

import re
from typing import Any


def normalize_number(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()
    if not text or text in {"-", "–", "—", "N/A", "NA", "null", "None"}:
        return None

    negative = text.startswith("(") and text.endswith(")")
    cleaned = text.strip("()").replace(",", "")
    cleaned = re.sub(r"(명|건|개|천명|천원|만원|원|%)$", "", cleaned).strip()

    if re.fullmatch(r"[-+]?\d+", cleaned):
        number = int(cleaned)
        return -abs(number) if negative else number
    if re.fullmatch(r"[-+]?\d+\.\d+", cleaned):
        number = float(cleaned)
        return -abs(number) if negative else number
    return value


def normalize_key(label: str, index: int = 0) -> str:
    text = str(label or "").strip().lower()
    if any(token in text for token in ("연도", "년도", "year")):
        return "year"
    if any(token in text for token in ("월", "month")):
        return "month"
    if any(token in text for token in ("출생", "birth")):
        return "birth"
    if any(token in text for token in ("사망", "death")):
        return "death"
    if any(token in text for token in ("자연", "증가", "natural")):
        return "natural"
    if any(token in text for token in ("구분", "분류", "항목", "category", "label")):
        return "category"
    if any(token in text for token in ("값", "수", "건수", "value")):
        return "value" if index == 0 else f"value{index + 1}"

    cleaned = re.sub(r"[^0-9a-zA-Z가-힣_]+", "_", text).strip("_")
    return cleaned or f"value{index + 1}"


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for key, value in row.items():
        if key in {"year", "month", "category", "label"}:
            normalized[key] = str(value).strip() if value is not None else None
        else:
            normalized[key] = normalize_number(value)
    return normalized
