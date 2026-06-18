# 서비스: 추출된 문서 텍스트를 chunk 단위로 랭킹하여 관련 구간을 선택합니다.
"""Hybrid local chunk ranking for extracted document text."""

import math
from collections import Counter

from app.services.analysis.answer_builder import (
    _clean_text,
    _frequent_terms,
    _metric_candidates,
    _sentences,
)
from app.services.analysis.query_analyzer import (
    _compact_for_match,
    _expanded_query_terms,
    _tokenize_terms,
)
from app.services.analysis.query_relevance import query_relevance_score
from app.services.analysis.scoring_config import CHUNK_RANK_WEIGHTS, QUERY_RELEVANCE_WEIGHTS
from app.services.embeddings.reranker import semantic_sentence_scores


# Chunk window size for ranking. This is independent from answer_builder.MAX_SENTENCE_CHARS.
CHUNK_SIZE = 900
CHUNK_OVERLAP = 160


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
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
    rank_terms = _query_terms_for_rank(question)
    idf = _idf_weights([item["text"] for item in candidates])
    base_ranked = []
    for index, item in enumerate(candidates):
        term_counts = Counter(_tokenize_terms(item["text"]))
        if not term_counts:
            base_ranked.append({**item, "base_score": 0.0, "original_index": index})
            continue

        score = 0.0
        for term in query_terms:
            if not term:
                continue
            tf = term_counts.get(term, 0)
            if tf:
                score += (1 + math.log(tf)) * idf.get(term, 1)

        score += (
            sum(
                min(idf.get(term, 1), CHUNK_RANK_WEIGHTS.frequent_term_cap)
                for term in _frequent_terms(item["text"], 4)
            )
            * CHUNK_RANK_WEIGHTS.frequent_term
        )
        score += len(_metric_candidates(item["text"], 2)) * CHUNK_RANK_WEIGHTS.metric
        compact_text = _compact_for_match(item["text"])
        relevance_score, _, _ = query_relevance_score(
            item["text"],
            query_terms,
            rank_terms=rank_terms,
            semantic_score=0.0,
        )
        score += relevance_score
        if "원본그림" in compact_text or "수식입니다" in item["text"]:
            score += CHUNK_RANK_WEIGHTS.noise_penalty

        base_ranked.append({**item, "base_score": score, "original_index": index})

    base_ranked.sort(key=lambda item: item["base_score"], reverse=True)
    dynamic_top_k = min(15, max(5, int(len(base_ranked) * 0.15)))
    top_candidates = base_ranked[:dynamic_top_k]

    top_semantic_scores = (
        semantic_sentence_scores(
            question,
            [item["text"][:700] for item in top_candidates],
        )
        if question and top_candidates
        else None
    )

    for index, item in enumerate(top_candidates):
        semantic_score = top_semantic_scores[index] if top_semantic_scores else 0.0
        item["semantic_score"] = round(semantic_score, 4)
        item["score"] = round(
            item["base_score"] + semantic_score * QUERY_RELEVANCE_WEIGHTS.semantic,
            4,
        )

    top_candidates.sort(
        key=lambda item: (item["score"], item.get("semantic_score", 0.0)),
        reverse=True,
    )
    for item in top_candidates:
        item.pop("base_score", None)
        item.pop("original_index", None)

    return top_candidates[:limit]
