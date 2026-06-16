"""Select table columns that match parsed chart requests."""

from typing import Any


REGION_COLUMN_CANDIDATES = ["지역", "시도", "시도명", "구분", "항목", "name", "region"]

METRIC_WORDS = {
    "birth_count": ["출생아 수", "출생아", "출생", "birth"],
    "death_count": ["사망자 수", "사망자", "사망", "death"],
    "marriage_count": ["혼인 건수", "혼인", "marriage"],
    "divorce_count": ["이혼 건수", "이혼", "divorce"],
    "natural_increase": ["자연증가", "자연 증가", "natural"],
}


def _column_key(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        return str(column.get("key") or column.get("label") or "")
    return str(column or "")


def _column_label(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        return str(column.get("label") or column.get("key") or "")
    return str(column or "")


def _column_text(column: str | dict[str, Any]) -> str:
    return f"{_column_key(column)} {_column_label(column)}"


def _column_keys(columns: list[str | dict[str, Any]]) -> list[str]:
    return [_column_key(column) for column in columns]


def find_region_column(columns: list[str | dict[str, Any]]) -> str | None:
    for candidate in REGION_COLUMN_CANDIDATES:
        for column in columns:
            text = _column_text(column)
            if candidate == _column_key(column) or candidate in text:
                return _column_key(column)

    keys = _column_keys(columns)
    return keys[0] if keys else None


def find_year_metric_column(
    columns: list[str | dict[str, Any]],
    year: str | None,
    metric: str | None,
    period: str = "year",
) -> str | None:
    if not columns:
        return None

    year_candidates = []
    if year:
        year_candidates = [f"{year}년p", f"{year}년", f"{year}p", year]

    for candidate in year_candidates:
        for column in columns:
            col_text = _column_text(column)
            if candidate not in col_text:
                continue

            if period == "year":
                if any(blocked in col_text for blocked in ("월", "누계", "조출생률", "률", "rate")):
                    continue
                return _column_key(column)

            if period == "month_3":
                if "3월" in col_text and "누계" not in col_text and "1~3월" not in col_text and "1-3월" not in col_text:
                    return _column_key(column)
                continue

            if period == "quarter_1":
                if "1~3월" in col_text or "1-3월" in col_text or "누계" in col_text:
                    return _column_key(column)
                continue

            if period not in {"year", "month_3", "quarter_1"}:
                return _column_key(column)

    for word in METRIC_WORDS.get(metric or "", []):
        for column in columns:
            col_text = _column_text(column)
            if word in col_text and not any(blocked in col_text for blocked in ("조출생률", "률", "rate")):
                return _column_key(column)

    return None
