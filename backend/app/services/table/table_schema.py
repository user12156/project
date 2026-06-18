"""Shared table data shapes used by the deterministic chart pipeline."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


ChartDimension = Literal["region", "month", "year"]
ChartMetric = Literal[
    "birth_count",
    "death_count",
    "marriage_count",
    "divorce_count",
    "natural_increase",
    "crude_birth_rate",
]
ChartPeriod = Literal["year", "month", "quarter_1"]


class ChartRequest(TypedDict, total=False):
    year: str | None
    month: int | None
    dimension: ChartDimension | None
    metric: ChartMetric | None
    metrics: list[ChartMetric]
    chart_type: str
    period: ChartPeriod


class TableRecord(TypedDict, total=False):
    title: str
    filename: str | None
    text: str
    headers: list[Any] | None
    columns: list[Any]
    rows: list[dict[str, Any]]


class NormalizedTableRow(TypedDict, total=False):
    region: str
    year: str | None
    month: int | None
    period: ChartPeriod
    metric: ChartMetric | str
    value: int | float
    source_col: str


TableDataFrame = list[NormalizedTableRow]

