"""Structured document comparison data models and extractors."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass
class CompareResult:
    topic: str
    purpose: str
    data_source: str
    methodology: str
    findings: str
    limitations: str


FIELD_LABELS = {
    "topic": "주제",
    "purpose": "연구목적",
    "data_source": "사용데이터",
    "methodology": "분석방법",
    "findings": "주요결과",
    "limitations": "한계점",
}


FIELD_PATTERNS = {
    "purpose": (
        r"(?:연구\s*)?목적[^.。!?]*[.。!?]?",
        r"(?:본\s*)?연구(?:는|의)?[^.。!?]*(?:목적|규명|평가|분석)[^.。!?]*[.。!?]?",
        r"(?:aim|objective|purpose)[^.。!?]*[.。!?]?",
    ),
    "data_source": (
        r"(?:데이터|자료|표본|통계청|dataset|data)[^.。!?]*(?:\d{4}[^.。!?]*)?[.。!?]?",
        r"\d{4}\s*(?:~|-|부터|에서)\s*\d{4}[^.。!?]*[.。!?]?",
    ),
    "methodology": (
        r"(?:회귀분석|시계열\s*분석|패널\s*분석|실증\s*분석|분석\s*방법|방법론)[^.。!?]*[.。!?]?",
        r"(?:regression|time\s*series|panel|methodology|method)[^.。!?]*[.。!?]?",
    ),
    "findings": (
        r"(?:결과|결론|주요\s*결과|분석\s*결과|시사점)[^.。!?]*(?:영향|효과|확인|나타|보였|존재|크)[^.。!?]*[.。!?]?",
        r"(?:finding|result|conclusion)[^.。!?]*[.。!?]?",
    ),
    "limitations": (
        r"(?:한계|제한점|향후\s*연구|부족|limitations?)[^.。!?]*[.。!?]?",
    ),
}


def compare_result_to_dict(result: CompareResult) -> dict[str, str]:
    return asdict(result)


def extract_compare_result(doc: dict) -> CompareResult:
    text = _normalize_text(doc.get("text", ""))
    filename = str(doc.get("filename") or doc.get("source_name") or "문서").strip()
    return CompareResult(
        topic=_extract_topic(text, filename),
        purpose=_extract_field(text, "purpose", "문서에서 연구 목적을 명확히 찾지 못했습니다."),
        data_source=_extract_field(text, "data_source", "문서에서 사용 데이터 정보를 명확히 찾지 못했습니다."),
        methodology=_extract_field(text, "methodology", "문서에서 분석 방법을 명확히 찾지 못했습니다."),
        findings=_extract_field(text, "findings", "문서에서 주요 결과를 명확히 찾지 못했습니다."),
        limitations=_extract_field(text, "limitations", "문서에서 한계점을 명확히 찾지 못했습니다."),
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _extract_topic(text: str, filename: str) -> str:
    title_match = re.search(r"(?:제목|Title)\s*[:：]\s*([^。.!?\n]{4,80})", text, re.IGNORECASE)
    if title_match:
        return _trim_value(_strip_after_heading_marker(title_match.group(1)))

    first_sentence = re.split(r"[。.!?]\s+", text, maxsplit=1)[0].strip()
    if 8 <= len(first_sentence) <= 80 and not re.search(r"^(초록|abstract|요약|서론)\b", first_sentence, re.IGNORECASE):
        return _trim_value(first_sentence)

    stem = re.sub(r"\.[A-Za-z0-9]+$", "", filename)
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem or "문서 주제"


def _extract_field(text: str, field: str, fallback: str) -> str:
    for pattern in FIELD_PATTERNS.get(field, ()):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _trim_value(match.group(0))
            if value:
                return value
    return fallback


def _trim_value(value: str, limit: int = 90) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip(" -:：\t\r\n")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _strip_after_heading_marker(value: str) -> str:
    return re.split(r"\s+(?:초록|요약|abstract|서론|introduction)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
