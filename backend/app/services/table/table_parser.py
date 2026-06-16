"""Parse detected table text into structured rows."""

import re
from typing import Any

from app.services.table.table_normalizer import normalize_number


NUMBER_PATTERN = re.compile(r"\(?[-+]?\d[\d,]*(?:\.\d+)?\)?")
YEAR_ROW_PATTERN = re.compile(
    r"^\s*(?P<year>\d{4})(?:[.\-/]\s*(?P<month>\d{1,2})p?)?\s+(?P<rest>.+)$",
    re.IGNORECASE,
)


def _split_cells(line: str) -> list[str]:
    if "|" in line:
        return [cell.strip() for cell in line.split("|") if cell.strip()]
    return [cell.strip() for cell in re.split(r"\s+", line.strip()) if cell.strip()]


def _column_key(label: str, index: int = 0) -> str:
    text = str(label or "").strip()
    lowered = text.lower()
    if any(token in text for token in ("시도", "지역", "전국", "서울", "부산")) or lowered in {"region", "area"}:
        return "region"
    if any(token in text for token in ("연도", "년도")) or lowered == "year":
        return "year"
    if "출생" in text or "birth" in lowered:
        return "birth"
    if "사망" in text or "death" in lowered:
        return "death"
    if "자연" in text or "natural" in lowered:
        return "natural"

    cleaned = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", text).strip("_")
    return cleaned or f"value{index + 1}"


def _unique_keys(labels: list[str]) -> list[str]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    for index, label in enumerate(labels):
        base_key = _column_key(label, index)
        count = seen.get(base_key, 0)
        seen[base_key] = count + 1
        keys.append(base_key if count == 0 else f"{base_key}_{count + 1}")
    return keys


def _columns(keys: list[str], labels: list[str]) -> list[dict[str, str]]:
    return [{"key": key, "label": label} for key, label in zip(keys, labels)]


def _value_header_labels(cells: list[str], numeric_count: int) -> list[str]:
    tokens = cells[1:]
    labels: list[str] = []
    index = 0

    while index < len(tokens):
        current = tokens[index]
        next_token = tokens[index + 1] if index + 1 < len(tokens) else ""
        if next_token in {"수", "건수"}:
            labels.append(f"{current} {next_token}")
            index += 2
        else:
            labels.append(current)
            index += 1

    if len(labels) >= numeric_count:
        return labels[:numeric_count]
    return [*labels, *[f"value{index + 1}" for index in range(len(labels), numeric_count)]]


def _parse_year_rows(table: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    row_matches: list[tuple[str, str | None, list[str]]] = []
    max_numeric_count = 0

    for line in lines:
        match = YEAR_ROW_PATTERN.match(line)
        if not match:
            continue
        numbers = NUMBER_PATTERN.findall(match.group("rest"))
        if not numbers:
            continue
        row_matches.append((match.group("year"), match.group("month"), numbers))
        max_numeric_count = max(max_numeric_count, len(numbers))

    if not row_matches:
        return None

    header_labels: list[str] = []
    for line in lines[:6]:
        if line.startswith("[표") or line.startswith("[Table"):
            continue
        cells = _split_cells(line)
        if len(cells) >= max_numeric_count + 1 and not re.match(r"^\d{4}", cells[0]):
            header_labels = _value_header_labels(cells, max_numeric_count)
            break

    if not header_labels and re.search(r"출생|사망|자연|인구동태", table.get("text", "")):
        header_labels = ["출생아 수", "사망자 수", "자연증가"][:max_numeric_count]
    if not header_labels:
        header_labels = [f"value{index + 1}" for index in range(max_numeric_count)]

    value_keys = _unique_keys(header_labels)
    rows = []
    has_month = any(month for _, month, _ in row_matches)
    for year, month, numbers in row_matches:
        row: dict[str, Any] = {"year": year}
        if month:
            row["month"] = f"{int(month)}월"
        for index, value in enumerate(numbers[: len(value_keys)]):
            row[value_keys[index]] = normalize_number(value)
        rows.append(row)

    axis_columns = [{"key": "year", "label": "연도"}]
    if has_month:
        axis_columns.append({"key": "month", "label": "월"})

    return {
        **table,
        "columns": [*axis_columns, *_columns(value_keys, header_labels)],
        "rows": rows,
    }


def _is_labeled_data_row(cells: list[str]) -> bool:
    if len(cells) < 2:
        return False
    first = cells[0]
    if first.startswith("[표") or first in {"시도별", "지역", "구분", "연도"}:
        return False
    if re.fullmatch(r"\d{4}.*", first):
        return False
    numeric_values = [normalize_number(cell) for cell in cells[1:]]
    return any(isinstance(value, (int, float)) for value in numeric_values)


def _parse_labeled_rows(table: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    split_lines = [_split_cells(line) for line in lines]
    data_indexes = [index for index, cells in enumerate(split_lines) if _is_labeled_data_row(cells)]
    if not data_indexes:
        return None

    first_data_index = data_indexes[0]
    max_value_count = max(len(split_lines[index]) - 1 for index in data_indexes)

    header_cells: list[str] = []
    for index in range(first_data_index - 1, -1, -1):
        cells = split_lines[index]
        if len(cells) >= max_value_count + 1 and not _is_labeled_data_row(cells):
            header_cells = cells
            break

    if header_cells:
        x_label = header_cells[0]
        value_labels = header_cells[1 : max_value_count + 1]
    else:
        x_label = "지역"
        value_labels = [f"value{index + 1}" for index in range(max_value_count)]

    x_key = _column_key(x_label)
    if x_key not in {"region", "category"}:
        x_key = "region"

    value_keys = _unique_keys(value_labels)
    rows = []
    for index in data_indexes:
        cells = split_lines[index]
        row: dict[str, Any] = {x_key: cells[0]}
        for value_index, key in enumerate(value_keys):
            source_index = value_index + 1
            if source_index >= len(cells):
                row[key] = None
                continue
            row[key] = normalize_number(cells[source_index])
        rows.append(row)

    return {
        **table,
        "columns": [{"key": x_key, "label": x_label}, *_columns(value_keys, value_labels)],
        "rows": rows,
    }


def parse_table(table: dict[str, Any]) -> dict[str, Any]:
    text = str(table.get("text") or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    labeled_table = _parse_labeled_rows(table, lines)
    if labeled_table:
        return labeled_table

    year_table = _parse_year_rows(table, lines)
    if year_table:
        return year_table

    return {**table, "columns": [], "rows": []}


def parse_tables(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [parse_table(table) for table in tables]
