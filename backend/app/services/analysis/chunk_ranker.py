# 서비스: 추출된 문서 텍스트를 chunk 단위로 랭킹하여 관련 구간을 선택합니다.
"""Hybrid local chunk ranking for extracted document text."""

import math
from collections import Counter

from app.services.analysis.query_analyzer import (
    _compact_for_match,
    _expanded_query_terms,
    _sentence_query_overlap,
    _tokenize_terms,
)
from app.services.embeddings.reranker import semantic_sentence_scores


CHUNK_SIZE = 900
CHUNK_OVERLAP = 160


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    from app.services.analysis.answer_builder import _clean_text, _sentences

    cleaned = _clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    current = ""
    for sentence in _sentences(cleaned) or [cleaned]:
        if len(sentence) > chunk_size:
            step = max(chunk_size - overlap, 1)
            chunks.extend(sentence[index:index + chunk_size] for index in range(0, len(sentence), step))
            current = ""
            continue

        next_text = f"{current} {sentence}".strip()
        if len(next_text) <= chunk_size:
            current = next_text
            continue

        if current:
            chunks.append(current)
            current = f"{current[-overlap:]} {sentence}".strip() if overlap else sentence
        else:
            current = sentence

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk.strip()]


def _idf_weights(chunks: list[str]) -> dict[str, float]:
    token_sets = [set(_tokenize_terms(chunk)) for chunk in chunks]
    total = len(token_sets)
    document_frequency = Counter(token for tokens in token_sets for token in tokens)
    return {
        token: math.log((total + 1) / (count + 1)) + 1
        for token, count in document_frequency.items()
    }


def _query_terms_for_rank(question: str) -> list[str]:
    return list(_expanded_query_terms(question))


def rank_relevant_chunks(question: str, extracted_docs: list[dict], limit: int = 6) -> list[dict]:
    from app.services.analysis.answer_builder import (
        _frequent_terms,
        _metric_candidates,
        _sentences,
    )

    candidates: list[dict] = []
    for doc in extracted_docs:
        source_units = doc.get("source_units") or [
            {
                "source_label": doc.get("source_label") or doc.get("format", "document"),
                "page_number": doc.get("page_number"),
                "section_index": doc.get("section_index"),
                "text": doc.get("text", ""),
            }
        ]
        chunk_index = 1
        for unit in source_units:
            for chunk in _chunk_text(unit.get("text", "")):
                if not _sentences(chunk):
                    continue
                candidates.append(
                    {
                        "filename": doc.get("filename", "unknown"),
                        "format": doc.get("format", "unknown"),
                        "chunk_index": chunk_index,
                        "source_label": unit.get("source_label") or doc.get("format", "document"),
                        "page_number": unit.get("page_number"),
                        "section_index": unit.get("section_index"),
                        "text": chunk,
                    }
                )
                chunk_index += 1

    if not candidates:
        return []

    query_terms = _expanded_query_terms(question) if question else set(
        _tokenize_terms(" ".join(_frequent_terms(" ".join(item["text"] for item in candidates), 8)))
    )
    compact_question = _compact_for_match(question)
    rank_terms = _query_terms_for_rank(question)
    important_phrases = (
        "시도별혼인건수",
        "시도별이혼건수",
        "시도별사망자수",
        "시도별출생아수",
        "시도별조혼인율",
        "시도별조이혼율",
        "시도별합계출산율",
        "혼인종류별혼인건수",
        "혼인건수",
        "이혼건수",
        "사망자수",
        "출생아수",
        "자연증가",
        "합계출산율",
    )
    idf = _idf_weights([item["text"] for item in candidates])
    semantic_scores = semantic_sentence_scores(
        question,
        [item["text"][:700] for item in candidates],
    ) if question else None

    ranked = []
    for index, item in enumerate(candidates):
        term_counts = Counter(_tokenize_terms(item["text"]))
        if not term_counts:
            continue

        score = 0.0
        for term in query_terms:
            if not term:
                continue
            tf = term_counts.get(term, 0)
            if tf:
                score += (1 + math.log(tf)) * idf.get(term, 1)

        score += sum(min(idf.get(term, 1), 3) for term in _frequent_terms(item["text"], 4)) * 0.15
        score += len(_metric_candidates(item["text"], 2)) * 1.4
        compact_text = _compact_for_match(item["text"])
        for phrase in important_phrases:
            if phrase in compact_question and phrase in compact_text:
                score += 25
        score += sum(1.2 for term in rank_terms if term in compact_text)
        matched_count, coverage = _sentence_query_overlap(item["text"], query_terms)
        score += matched_count * 1.8 + coverage * 5.0
        semantic_score = semantic_scores[index] if semantic_scores else 0.0
        score += semantic_score * 18.0
        if "원본그림" in compact_text or "수식입니다" in item["text"]:
            score -= 8

        ranked.append({**item, "score": round(score, 4), "semantic_score": round(semantic_score, 4)})

    ranked.sort(key=lambda item: (item["score"], item.get("semantic_score", 0.0)), reverse=True)
    return ranked[:limit]
