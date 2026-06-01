import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings


_WORD_RE = re.compile(r"[^\W_]{2,}", re.UNICODE)
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:\d{1,3}(?:,\d{3})+|\d+\.\d+|(?:19|20)\d{2}|\d+\s*%)(?![A-Za-z0-9_%])"
)
_SENTENCE_RE = re.compile(r"(?<=[.!?。！？\n])\s+|(?<=[다요죠음임함됨])\s+")

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


def _sentences(text: str, *, limit: int = 24) -> list[str]:
    candidates = []
    for part in _SENTENCE_RE.split(str(text or "")):
        normalized = part.strip()
        if 18 <= len(normalized) <= 700:
            candidates.append(normalized)
        if len(candidates) >= limit:
            break
    return candidates


@lru_cache(maxsize=1)
def _embedding_model():
    if not settings.enable_bert_grounding:
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        return SentenceTransformer(settings.bert_grounding_model)
    except Exception:
        return None


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _semantic_grounding_score(answer: str, evidence: str) -> float | None:
    model = _embedding_model()
    if model is None:
        return None

    answer_sentences = _sentences(answer, limit=8)
    evidence_sentences = _sentences(evidence, limit=32)
    if not answer_sentences or not evidence_sentences:
        return None
    instruction = settings.bert_grounding_instruction
    query_sentences = [
        f"Instruct: {instruction}\nQuery: {sentence}" if instruction else sentence
        for sentence in answer_sentences
    ]

    try:
        embeddings = model.encode(
            query_sentences + evidence_sentences,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception:
        return None

    vectors = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
    answer_vectors = vectors[: len(answer_sentences)]
    evidence_vectors = vectors[len(answer_sentences):]
    best_scores = [
        max(_cosine(answer_vector, evidence_vector) for evidence_vector in evidence_vectors)
        for answer_vector in answer_vectors
    ]
    return round(sum(best_scores) / max(len(best_scores), 1), 4)


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

    if len(answer_terms) >= 12 and support_ratio < 0.35:
        semantic_score = _semantic_grounding_score(answer, evidence)
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
