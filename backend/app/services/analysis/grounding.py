# 서비스: 답변의 근거를 검증하고 숫자/키워드/의미적 grounding 점수를 계산합니다.
import re
from dataclasses import dataclass

from app.core.config import settings
from app.services.embeddings.reranker import semantic_grounding_score


_WORD_RE = re.compile(r"[^\W_]{2,}", re.UNICODE)
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:\d{1,3}(?:,\d{3})+|\d+\.\d+|(?:19|20)\d{2}|\d+\s*%)(?![A-Za-z0-9_%])"
)
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "about",
    "document",
    "context",
    "analysis",
    "summary",
    "user",
    "request",
    "page",
    "file",
    "section",
    "문서",
    "분석",
    "내용",
    "요약",
    "근거",
    "관련",
    "주요",
    "결과",
    "자료",
    "정보",
    "사용자",
    "질문",
    "핵심",
    "중요",
    "정리",
    "공표",
    "확인",
    "기준",
    "경우",
    "현재",
    "전체",
    "해당",
    "통해",
    "대한",
    "관한",
    "보입니다",
    "했습니다",
    "있습니다",
}


@dataclass
class GroundingResult:
    passed: bool
    reason: str = ""
    unsupported_numbers: list[str] | None = None
    unsupported_terms: list[str] | None = None
    method: str = "keyword"
    semantic_score: float | None = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "unsupported_numbers": self.unsupported_numbers or [],
            "unsupported_terms": self.unsupported_terms or [],
            "method": self.method,
            "semantic_score": self.semantic_score,
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _compact(text: str) -> str:
    return re.sub(r"[\s,]+", "", str(text or "")).lower()


def _numbers(text: str) -> list[str]:
    seen = set()
    values = []
    for match in _NUMBER_RE.finditer(text or ""):
        value = match.group(0).strip()
        key = _compact(value)
        if key and key not in seen:
            seen.add(key)
            values.append(value)
    return values


def _terms(text: str) -> set[str]:
    terms = set()
    for raw in _WORD_RE.findall(_normalize(text)):
        if raw.isdigit() or raw in _STOPWORDS:
            continue
        if len(raw) < 3:
            continue
        terms.add(raw)
    return terms


def _evidence_text(extracted_docs: list[dict], relevant_chunks: list[dict], metrics: list[str]) -> str:
    parts = []
    parts.extend(str(doc.get("text", "")) for doc in extracted_docs or [])
    parts.extend(str(chunk.get("text", "")) for chunk in relevant_chunks or [])
    parts.extend(str(metric) for metric in metrics or [])
    return "\n".join(part for part in parts if part)


def validate_grounding(
    answer: str,
    extracted_docs: list[dict],
    relevant_chunks: list[dict] | None = None,
    metrics: list[str] | None = None,
) -> dict:
    evidence = _evidence_text(extracted_docs, relevant_chunks or [], metrics or [])
    if not _normalize(evidence):
        return GroundingResult(False, "No document evidence was available.").to_dict()

    compact_evidence = _compact(evidence)
    unsupported_numbers = [
        value for value in _numbers(answer) if _compact(value) not in compact_evidence
    ]
    if unsupported_numbers:
        return GroundingResult(
            False,
            "The answer contains numbers not found in the uploaded documents.",
            unsupported_numbers=unsupported_numbers[:8],
            method="number",
        ).to_dict()

    answer_terms = _terms(answer)
    if not answer_terms:
        return GroundingResult(True).to_dict()

    evidence_terms = _terms(evidence)
    unsupported_terms = sorted(answer_terms - evidence_terms)
    support_ratio = 1 - (len(unsupported_terms) / max(len(answer_terms), 1))
    supported_terms = answer_terms & evidence_terms

    if len(answer_terms) >= 12 and support_ratio < 0.22 and len(supported_terms) < 5:
        semantic_score = semantic_grounding_score(answer, evidence)
        if semantic_score is not None and semantic_score >= settings.bert_grounding_threshold:
            return GroundingResult(
                True,
                method="bert",
                semantic_score=semantic_score,
            ).to_dict()

        return GroundingResult(
            False,
            "The answer has low overlap with uploaded document terms.",
            unsupported_terms=unsupported_terms[:12],
            method="bert" if settings.enable_bert_grounding else "keyword",
            semantic_score=semantic_score,
        ).to_dict()

    return GroundingResult(True).to_dict()
