"""Align extracted experiment results into a comparison table."""

from __future__ import annotations

from typing import Any

from app.services.paper_compare.experiment_extractor import extract_experiment_results
from app.services.paper_compare.metric_normalizer import metric_label


def build_experiment_comparison(papers: list[dict[str, Any]]) -> dict[str, Any] | None:
    results = [extract_experiment_results(paper) for paper in papers]
    metric_keys = _common_or_available_metrics(results)
    if not metric_keys:
        return None

    rows = []
    for result in results:
        metric_values = {metric["metric"]: metric["value"] for metric in result.get("metrics", [])}
        row = {
            "논문": result.get("paper_title", "논문"),
            "데이터셋": result.get("dataset", ""),
            "모델": result.get("model", ""),
            "특징": result.get("feature", ""),
        }
        for metric in metric_keys:
            row[metric_label(metric)] = metric_values.get(metric)
        rows.append(row)

    return {
        "rows": rows,
        "metrics": metric_keys,
        "results": results,
    }


def _common_or_available_metrics(results: list[dict[str, Any]]) -> list[str]:
    metric_sets = [
        {metric["metric"] for metric in result.get("metrics", [])}
        for result in results
        if result.get("metrics")
    ]
    if not metric_sets:
        return []
    common = set.intersection(*metric_sets) if len(metric_sets) > 1 else metric_sets[0]
    selected = common or set.union(*metric_sets)
    preferred = ["accuracy", "f1_score", "precision", "recall", "mae", "rmse"]
    return [metric for metric in preferred if metric in selected] + sorted(selected - set(preferred))
