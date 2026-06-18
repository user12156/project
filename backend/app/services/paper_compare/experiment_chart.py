"""Create charts from paper experiment comparison tables."""

from __future__ import annotations

from typing import Any


def build_experiment_metric_chart(comparison: dict[str, Any]) -> dict[str, Any] | None:
    rows = comparison.get("rows") or []
    metrics = comparison.get("metrics") or []
    if not rows or not metrics:
        return None

    metric_label = _metric_label(metrics[0])
    data = [
        {
            "paper": row.get("논문"),
            _metric_key(metric_label): row.get(metric_label),
        }
        for row in rows
        if isinstance(row.get(metric_label), (int, float))
    ]
    if len(data) < 2:
        return None

    data_key = _metric_key(metric_label)
    return {
        "type": "chart",
        "chartType": "bar",
        "title": f"유사 논문별 {metric_label} 비교",
        "xAxisKey": "paper",
        "columns": [
            {"key": "paper", "label": "논문"},
            {"key": data_key, "label": metric_label},
        ],
        "series": [
            {"dataKey": data_key, "name": metric_label, "yAxisId": "left"},
        ],
        "data": data,
    }


def _metric_label(metric: str) -> str:
    return {
        "accuracy": "Accuracy",
        "f1_score": "F1-score",
        "precision": "Precision",
        "recall": "Recall",
        "mae": "MAE",
        "rmse": "RMSE",
    }.get(metric, metric.replace("_", " ").title())


def _metric_key(label: str) -> str:
    return label.lower().replace("-", "_").replace(" ", "_")
