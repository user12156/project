"""Group similar papers before comparing experiment results."""

from __future__ import annotations

import re
from typing import Any

from app.services.embeddings.embedding_model import cosine_similarity, encode_texts


def group_similar_papers(papers: list[dict[str, Any]], threshold: float = 0.75) -> list[list[dict[str, Any]]]:
    if len(papers) <= 1:
        return [papers] if papers else []

    profiles = [_paper_profile(paper) for paper in papers]
    vectors = encode_texts(profiles)
    if not vectors:
        return [papers]

    groups: list[list[dict[str, Any]]] = []
    used: set[int] = set()
    for index, paper in enumerate(papers):
        if index in used:
            continue
        group = [paper]
        used.add(index)
        for other_index in range(index + 1, len(papers)):
            if other_index in used:
                continue
            if cosine_similarity(vectors[index], vectors[other_index]) >= threshold:
                group.append(papers[other_index])
                used.add(other_index)
        groups.append(group)
    return groups


def _paper_profile(paper: dict[str, Any]) -> str:
    text = str(paper.get("text") or "")
    title = str(paper.get("title") or paper.get("filename") or "")
    abstract = _extract_abstract(text)
    keywords = _extract_keywords(text)
    return " ".join(part for part in [title, abstract, keywords] if part).strip()


def _extract_abstract(text: str) -> str:
    match = re.search(r"(?:abstract|초록|요약)\s*[:：]?\s*(.{80,1200}?)(?:\n\s*\n|keywords?|키워드|서론|introduction)", text, re.IGNORECASE | re.DOTALL)
    return " ".join(match.group(1).split()) if match else " ".join(text[:1200].split())


def _extract_keywords(text: str) -> str:
    match = re.search(r"(?:keywords?|키워드)\s*[:：]\s*([^\n]{3,300})", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""
