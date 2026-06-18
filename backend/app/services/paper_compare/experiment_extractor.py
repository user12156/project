"""Extract experiment result candidates from paper text."""

from __future__ import annotations

import re
from typing import Any

from app.services.paper_compare.metric_normalizer import (
    higher_is_better,
    metric_label,
    normalize_metric_name,
    parse_score,
)


SECTION_MARKERS = (
    "Experiment",
    "Experimental Results",
    "Results",
    "Evaluation",
    "Performance Comparison",
    "Ablation Study",
    "실험 결과",
    "성능 평가",
    "비교 실험",
)


METRIC_PATTERN = re.compile(
    r"(?P<metric>Accuracy|Acc\.?|Top-1\s*Acc|F1(?:-score|\s*score)?|Precision|Recall|MAE|RMSE|정확도|정밀도|재현율)"
    r"[^0-9%]{0,30}(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%?)",
    re.IGNORECASE,
)


def extract_experiment_results(paper: dict[str, Any]) -> dict[str, Any]:
    text = str(paper.get("text") or "")
    section = extract_experiment_section(text)
    metrics = _extract_metrics(section or text)
    return {
        "paper_title": _paper_title(paper, text),
        "task": _extract_task(text),
        "dataset": _extract_dataset(section or text),
        "model": _extract_model(section or text, paper),
        "metrics": metrics,
        "feature": _extract_feature(section or text),
    }


def extract_experiment_section(text: str, limit: int = 4000) -> str:
    lowered = text.lower()
    starts = [lowered.find(marker.lower()) for marker in SECTION_MARKERS if lowered.find(marker.lower()) >= 0]
    if not starts:
        return ""
    start = min(starts)
    return text[start:start + limit]


def _extract_metrics(text: str) -> list[dict[str, Any]]:
    metrics = []
    seen = set()
    for match in METRIC_PATTERN.finditer(text):
        canonical = normalize_metric_name(match.group("metric"))
        value = parse_score(match.group("value"))
        if value is None or canonical in seen:
            continue
        seen.add(canonical)
        metrics.append(
            {
                "metric": canonical,
                "label": metric_label(canonical),
                "value": value,
                "unit": match.group("unit") or "",
                "higher_is_better": higher_is_better(canonical),
            }
        )
    return metrics


def _paper_title(paper: dict[str, Any], text: str) -> str:
    title = str(paper.get("title") or "").strip()
    if title:
        return title
    match = re.search(r"(?:Title|제목)\s*[:：]\s*([^\n]{4,120})", text, re.IGNORECASE)
    if match:
        return _strip_after_heading_marker(match.group(1)).strip()
    return str(paper.get("filename") or "논문").strip()


def _extract_task(text: str) -> str:
    if re.search(r"classification|분류", text, re.IGNORECASE):
        return "분류"
    if re.search(r"detection|탐지|검출", text, re.IGNORECASE):
        return "탐지"
    if re.search(r"prediction|예측", text, re.IGNORECASE):
        return "예측"
    return "문서에서 명확히 확인되지 않음"


def _extract_dataset(text: str) -> str:
    match = re.search(r"(CIFAR-10|CIFAR-100|ImageNet|MNIST|COCO|SQuAD|통계청|KOSIS|[A-Z][A-Za-z0-9_-]{2,}\s*dataset)", text)
    return match.group(1).strip() if match else "문서에서 명확히 확인되지 않음"


def _extract_model(text: str, paper: dict[str, Any]) -> str:
    match = re.search(r"(Proposed\s+Model|ResNet|CNN|BERT|LSTM|Transformer|제안\s*모델|개선\s*모델)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return str(paper.get("filename") or "문서 모델").strip()


def _extract_feature(text: str) -> str:
    if re.search(r"residual|잔차", text, re.IGNORECASE):
        return "잔차 연결 사용"
    if re.search(r"proposed|제안|개선", text, re.IGNORECASE):
        return "개선 모델"
    if re.search(r"baseline|기본", text, re.IGNORECASE):
        return "기준 모델"
    return "실험 특징 확인 필요"


def _strip_after_heading_marker(value: str) -> str:
    return re.split(r"\s+(?:초록|요약|abstract|서론|introduction)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
