import re
from typing import Any


NULL_VALUES = {"", "-", "–", "—", "…", "...", "N/A", "NA", "null", "None", "미상"}


def normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()

    if text in NULL_VALUES:
        return None

    # 괄호 음수: (1,234) -> -1234
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    # 단위/기호 제거
    cleaned = text.replace(",", "")
    cleaned = re.sub(r"(명|건|개|원|천원|만원|억원|%|점|배|년|월)$", "", cleaned).strip()

    # 숫자만 남은 경우 변환
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
            # x축 라벨로 쓰일 가능성이 높은 값은 문자열 유지
            if key.lower() in {"name", "label", "month", "year", "region", "category", "date"}:
                new_row[key] = str(value).strip() if value is not None else None
            else:
                new_row[key] = normalize_value(value)
        normalized.append(new_row)

    return normalized


def normalize_monthly_axis(data: list[dict], x_key: str = "month") -> list[dict]:
    """
    월별 그래프에서 1월~12월 축을 유지하기 위한 함수.
    없는 월은 빈 row로 채운다.
    """
    month_labels = [f"{i}월" for i in range(1, 13)]
    by_month = {}

    for row in data or []:
        month = row.get(x_key)
        if month is None:
            continue

        month_text = str(month).strip()
        match = re.search(r"(\d{1,2})", month_text)
        if not match:
            continue

        month_label = f"{int(match.group(1))}월"
        by_month[month_label] = {
            **row,
            x_key: month_label,
            "monthOrder": int(match.group(1)),
        }

    result = []
    for index, month_label in enumerate(month_labels, start=1):
        result.append(by_month.get(month_label, {x_key: month_label, "monthOrder": index}))

    return result