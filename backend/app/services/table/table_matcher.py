"""Find the table most related to a parsed chart request."""

import json
from typing import Any

from app.services.table.chart_request_parser import parse_chart_request


METRIC_KEYWORDS = {
    "birth_count": ["출생아", "출생아 수", "출생"],
    "death_count": ["사망자", "사망자 수", "사망"],
    "marriage_count": ["혼인", "혼인 건수"],
    "divorce_count": ["이혼", "이혼 건수"],
    "natural_increase": ["자연증가", "자연 증가"],
}

DIMENSION_KEYWORDS = {
    "region": ["시도별", "지역", "전국", "서울", "부산", "경기"],
    "month": ["월별", "1월", "2월", "3월", "월"],
    "year": ["연도별", "2024년", "2025년", "2026년", "연도"],
}

REGION_TABLE_TITLE_BY_METRIC = {
    "birth_count": "\uc2dc\ub3c4\ubcc4\ucd9c\uc0dd\uc544\uc218",
    "death_count": "\uc2dc\ub3c4\ubcc4\uc0ac\ub9dd\uc790\uc218",
    "marriage_count": "\uc2dc\ub3c4\ubcc4\ud63c\uc778\uac74\uc218",
    "divorce_count": "\uc2dc\ub3c4\ubcc4\uc774\ud63c\uac74\uc218",
}

NATIONWIDE_TABLE_TITLE_BY_METRIC = {
    "birth_count": "\uc804\uad6d\ucd9c\uc0dd\uc544\uc218",
    "death_count": "\uc804\uad6d\uc0ac\ub9dd\uc790\uc218",
    "marriage_count": "\uc804\uad6d\ud63c\uc778\uac74\uc218",
    "divorce_count": "\uc804\uad6d\uc774\ud63c\uac74\uc218",
}


def _column_text(column: str | dict[str, Any]) -> str:
    if isinstance(column, dict):
        return f"{column.get('key', '')} {column.get('label', '')}"
    return str(column or "")


def _table_haystack(table: dict[str, Any]) -> str:
    title = str(table.get("title") or "")
    columns = " ".join(_column_text(column) for column in table.get("columns", []))
    rows_text = " ".join(
        " ".join(str(value) for value in row.values())
        for row in table.get("rows", [])[:5]
        if isinstance(row, dict)
    )
    raw_text = str(table.get("text") or "")[:1200]
    return f"{title} {columns} {rows_text} {raw_text}"


def table_to_search_text(table: dict[str, Any]) -> str:
    parts = []

    title = table.get("title")
    if title:
        parts.append(str(title))

    headers = table.get("headers")
    if headers:
        parts.append(str(headers))

    columns = table.get("columns")
    if columns:
        parts.append(str(columns))

    rows = table.get("rows")
    if rows:
        parts.append(str(rows[:5]))

    text = table.get("text")
    if text:
        parts.append(str(text)[:1200])

    return " ".join(parts).replace(" ", "")


def _compact_text(text: str) -> str:
    return "".join(str(text or "").split())


def _region_target_title(request: dict[str, Any]) -> str | None:
    if request.get("dimension") != "region":
        return None
    return REGION_TABLE_TITLE_BY_METRIC.get(request.get("metric"))


def _is_nationwide_table(request: dict[str, Any], text: str) -> bool:
    if request.get("dimension") != "region":
        return False
    compact = _compact_text(text)
    region_title = _region_target_title(request)
    if region_title and region_title in compact:
        return False
    nationwide_title = NATIONWIDE_TABLE_TITLE_BY_METRIC.get(request.get("metric"))
    return bool(nationwide_title and nationwide_title in compact)


def _fallback_title_match(request: dict[str, Any], tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    metric = request.get("metric")
    dimension = request.get("dimension")
    region_title = _region_target_title(request)

    for table in tables or []:
        search_text = table_to_search_text(table)
        compact = _compact_text(search_text)

        if region_title and region_title not in compact:
            continue
        if _is_nationwide_table(request, search_text):
            continue

        if metric == "birth_count" and "출생아" in search_text:
            if dimension == "region" and any(
                keyword in search_text
                for keyword in ("시도별", "지역별", "행정구역별", "전국", "서울", "부산")
            ):
                return table

        if metric == "crude_birth_rate" and ("조출생률" in search_text or "출생률" in search_text):
            if dimension == "region" and any(
                keyword in search_text
                for keyword in ("시도별", "지역별", "행정구역별", "전국", "서울", "부산")
            ):
                return table

    return None


def find_best_table(request: dict[str, Any] | str, tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    if isinstance(request, str):
        request = parse_chart_request(request)

    region_title = _region_target_title(request)
    if region_title:
        for table in tables or []:
            compact = _compact_text(table_to_search_text(table))
            if region_title in compact:
                return table

    best_table = None
    best_score = 0
    metric_words = METRIC_KEYWORDS.get(request.get("metric"), [])
    dimension_words = DIMENSION_KEYWORDS.get(request.get("dimension"), [])

    for table in tables or []:
        haystack = _table_haystack(table)
        if _is_nationwide_table(request, haystack):
            continue

        title = str(table.get("title") or "")
        score = 0

        if any(word in haystack for word in metric_words):
            score += 5
        if any(word in haystack for word in dimension_words):
            score += 5
        if request.get("year") and request["year"] in haystack:
            score += 3
        if "시도별" in title and request.get("dimension") == "region":
            score += 4

        if score > best_score:
            best_score = score
            best_table = table

    if best_table and best_score >= 5:
        return best_table

    return _fallback_title_match(request, tables)


def find_related_table(query: str, extracted_tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    best_table = find_best_table(parse_chart_request(query), extracted_tables)
    if best_table:
        return best_table

    parsed_tables = [table for table in extracted_tables or [] if table.get("rows")]
    return parsed_tables[0] if len(parsed_tables) == 1 else None


def table_to_prompt_doc(table: dict[str, Any]) -> dict[str, Any]:
    table_json = {
        "title": table.get("title"),
        "columns": table.get("columns", []),
        "rows": table.get("rows", []),
    }
    return {
        "filename": table.get("filename") or table.get("title") or "matched_table",
        "format": "table_json",
        "text": "아래 표만 사용해 그래프 JSON 생성\n\n" + json.dumps(table_json, ensure_ascii=False),
        "matched_table": table_json,
        "visual_assets": [],
    }
