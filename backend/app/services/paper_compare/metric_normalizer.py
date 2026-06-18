"""Normalize experiment metric names across papers."""

from __future__ import annotations

import re


METRIC_ALIASES = {
    "accuracy": ["accuracy", "acc", "acc.", "정확도", "top-1 acc", "top1 acc"],
    "f1_score": ["f1", "f1-score", "f1 score", "f1점수"],
    "precision": ["precision", "정밀도"],
    "recall": ["recall", "재현율"],
    "mae": ["mae", "mean absolute error"],
    "rmse": ["rmse", "root mean squared error"],
}


METRIC_LABELS = {
    "accuracy": "Accuracy",
    "f1_score": "F1-score",
    "precision": "Precision",
    "recall": "Recall",
    "mae": "MAE",
    "rmse": "RMSE",
}


LOWER_IS_BETTER = {"mae", "rmse"}


def normalize_metric_name(metric: str) -> str:
    compact = _compact(metric)
    for canonical, aliases in METRIC_ALIASES.items():
        if any(_compact(alias) == compact or _compact(alias) in compact for alias in aliases):
            return canonical
    return compact.replace("-", "_").replace(" ", "_") or "metric"


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def higher_is_better(metric: str) -> bool:
    return metric not in LOWER_IS_BETTER


def parse_score(value: str) -> float | None:
    cleaned = str(value or "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _compact(value: str) -> str:
    return re.sub(r"[\s._-]+", "", str(value or "").lower())
