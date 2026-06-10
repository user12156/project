# 서비스: 문장 의미 유사도와 grounding 점수를 위한 semantic reranking을 담당합니다.
"""Semantic sentence scoring and answer grounding helpers."""

import re

from app.core.config import settings
from app.services.embeddings.embedding_model import cosine_similarity, encode_texts


_SENTENCE_RE = re.compile(r"(?<=[.!?。！？\n])\s+|(?<=[다요죠음임함됨])\s+")


def short_sentences(text: str, *, limit: int = 24) -> list[str]:
    candidates = []
    for part in _SENTENCE_RE.split(str(text or "")):
        normalized = part.strip()
        if 18 <= len(normalized) <= 700:
            candidates.append(normalized)
        if len(candidates) >= limit:
            break
    return candidates


def semantic_sentence_scores(question: str, sentences: list[str]) -> list[float] | None:
    if not question or not sentences or not settings.enable_bert_grounding:
        return None

    instruction = settings.bert_grounding_instruction
    query = f"Instruct: {instruction}\nQuery: {question}" if instruction else question
    vectors = encode_texts([query, *sentences])
    if not vectors:
        return None

    query_vector = vectors[0]
    return [round(cosine_similarity(query_vector, sentence_vector), 4) for sentence_vector in vectors[1:]]


def semantic_grounding_score(answer: str, evidence: str) -> float | None:
    if not settings.enable_bert_grounding:
        return None

    answer_sentences = short_sentences(answer, limit=8)
    evidence_sentences = short_sentences(evidence, limit=32)
    if not answer_sentences or not evidence_sentences:
        return None

    instruction = settings.bert_grounding_instruction
    query_sentences = [
        f"Instruct: {instruction}\nQuery: {sentence}" if instruction else sentence
        for sentence in answer_sentences
    ]
    vectors = encode_texts(query_sentences + evidence_sentences)
    if not vectors:
        return None

    answer_vectors = vectors[: len(answer_sentences)]
    evidence_vectors = vectors[len(answer_sentences):]
    best_scores = [
        max(cosine_similarity(answer_vector, evidence_vector) for evidence_vector in evidence_vectors)
        for answer_vector in answer_vectors
    ]
    return round(sum(best_scores) / max(len(best_scores), 1), 4)
