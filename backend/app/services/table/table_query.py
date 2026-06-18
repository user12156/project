"""Query normalized table rows according to a parsed chart request."""

from __future__ import annotations

from app.services.table.table_schema import ChartRequest, TableDataFrame


def filter_rows_for_request(request: ChartRequest, frame: TableDataFrame) -> TableDataFrame:
    if request.get("dimension") != "region":
        return []

    period = request.get("period") or "year"
    return [
        row
        for row in frame
        if row.get("year") == request.get("year")
        and row.get("metric") == request.get("metric")
        and row.get("period") == period
        and (period != "month" or row.get("month") == request.get("month"))
    ]

