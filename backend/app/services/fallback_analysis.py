# 서비스: LLM 분석 실패 시 로컬 요약/키워드/수치 후보/근거 기반 fallback 응답을 생성합니다.
"""Fast local fallback analysis for PaperMate.

This module owns non-LLM answers. Document extraction stays in
document_processing.py, while this file builds quick summaries, keywords,
metrics, and source-grounded fallback responses.
"""

from app.services.analysis.answer_builder import (
    _clean_text,
    _doc_brief,
    _extractive_summary,
    _frequent_terms,
    _metric_candidates,
    _top_sentences,
)
from app.services.analysis.chunk_ranker import rank_relevant_chunks
from app.services.analysis.query_analyzer import _intent_intro, _intent_label, _question_intent
from app.services.analysis.topic_modeling import extract_topics


def build_analysis_answer(question: str, extracted_docs: list[dict]) -> dict:
    cleaned_docs = [
        {
            **doc,
            "text": _clean_text(doc.get("text", "")),
        }
        for doc in extracted_docs
        if _clean_text(doc.get("text", ""))
    ]
    combined_text = "\n".join(doc["text"] for doc in cleaned_docs if doc["text"])
    intent = _question_intent(question)
    relevant_chunks = rank_relevant_chunks(question, cleaned_docs, 6)
    relevant_text = "\n".join(chunk["text"] for chunk in relevant_chunks) or combined_text
    summary_points = _extractive_summary(relevant_text, question, 4)
    terms = _frequent_terms(combined_text)
    metrics = _metric_candidates(combined_text)
    topics = extract_topics(combined_text)

    if not combined_text.strip():
        summary = (
            "업로드 파일은 받았지만 추출 가능한 본문 텍스트가 거의 없습니다. "
            "이미지라면 OCR 설치가 필요할 수 있고, 구형 HWP는 HWPX 변환이 더 안정적입니다."
        )
    else:
        summary = " ".join(summary_points) or combined_text[:600]

    comparison = [_doc_brief(doc) for doc in cleaned_docs]

    return {
        "answer": build_concise_fallback_answer(question, {
            "summary": summary,
            "intent": intent,
            "keywords": terms,
            "metrics": metrics,
            "topics": topics,
            "documents": comparison,
            "relevant_chunks": relevant_chunks,
        }),
        "summary": summary,
        "intent": intent,
        "keywords": terms,
        "metrics": metrics,
        "topics": topics,
        "documents": comparison,
        "relevant_chunks": relevant_chunks,
    }


def build_concise_fallback_answer(question: str, fallback_answer: dict) -> str:
    intent = fallback_answer.get("intent") or _question_intent(question)
    relevant_chunks = fallback_answer.get("relevant_chunks") or []
    sections = [
        _intent_intro(question, intent),
        "",
        "현재 문서에서 확인되는 근거만 빠르게 정리했습니다.",
        f"분석 기준: {_intent_label(intent)}",
        "",
        "[핵심 요약]",
    ]

    summary = _clean_text(fallback_answer.get("summary", ""))
    sections.append(summary[:900] if summary else "요약할 본문이 부족합니다.")

    metrics = fallback_answer.get("metrics") or []
    if metrics:
        sections.extend(["", "[수치 후보]"])
        sections.extend(f"- {metric}" for metric in metrics[:8])

    keywords = fallback_answer.get("keywords") or []
    if keywords:
        sections.extend(["", "[중요 키워드]", ", ".join(keywords[:10])])

    if relevant_chunks:
        sections.extend(["", "[근거 구간]"])
        for chunk in relevant_chunks[:3]:
            source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', '?')}"
            focused = _top_sentences(chunk.get("text", ""), 1, question)
            preview = (focused[0] if focused else _clean_text(chunk.get("text", "")))[:360]
            sections.append(f"- {chunk.get('filename', '문서')} {source_label}: {preview}")

    return "\n".join(section for section in sections if str(section).strip())


def build_empty_context_answer(
    question: str,
    fallback_answer: dict,
    has_uploaded_files: bool,
    filenames: list[str],
) -> str:
    if has_uploaded_files:
        file_names = ", ".join(filenames)
        return (
            f"업로드하신 파일({file_names})에서 텍스트를 추출할 수 없습니다.\n\n"
            "[확인 요청]\n"
            "- 텍스트가 포함되지 않은 스캔본 이미지이거나, 아직 지원되지 않는 형식일 수 있습니다.\n"
            "- 텍스트 복사가 가능한 PDF, HWPX, TXT, CSV 등을 업로드해주세요."
        )

    return (
        f"{_intent_intro(question, fallback_answer.get('intent') or _question_intent(question))}\n\n"
        "현재 분석할 문서 본문이 없습니다.\n\n"
        "[필요한 자료]\n"
        "- 질문에 맞는 문서를 먼저 업로드해주세요.\n"
        "- 문서를 업로드하면 핵심 요약, 중요 문장 발췌, 수치 후보, 표/그래프 생성을 진행합니다."
    )
