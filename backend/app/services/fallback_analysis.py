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
from app.services.analysis.scoring_config import CHUNK_RANK_WEIGHTS
from app.services.analysis.topic_modeling import extract_topics
from app.services.translation import force_korean_analysis_text

KEYWORD_TRANSLATIONS = {
    "accuracy": "정확도",
    "cnn": "합성곱 신경망",
    "convolutional neural network": "합성곱 신경망",
    "deep learning model": "딥러닝 모델",
    "deep learning models": "딥러닝 모델",
    "logistic regression": "로지스틱 회귀",
    "machine learning": "머신러닝",
    "model category": "모델 분류",
    "sensitivity": "민감도",
    "specificity": "특이도",
    "time-series": "시계열",
}


def _english_heavy(text: str) -> bool:
    letters = [char for char in str(text or "") if char.isalpha()]
    if not letters:
        return False
    korean_count = sum(1 for char in letters if "가" <= char <= "힣")
    english_count = sum(1 for char in letters if ("a" <= char.lower() <= "z"))
    return english_count >= 20 and english_count > korean_count * 1.4


def _korean_user_text(text: str, *, source_label: str = "문서 근거") -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    translated = force_korean_analysis_text(cleaned)
    if translated and not _english_heavy(translated):
        return translated
    if _english_heavy(cleaned):
        second_pass = force_korean_analysis_text(cleaned[:900])
        if second_pass and not _english_heavy(second_pass):
            return second_pass
        return f"{source_label}: 영문 원문에서 확인된 핵심 내용을 기준으로 정리했습니다. 로컬 번역기가 처리하지 못한 전문 용어는 원문 키워드에 함께 표시했습니다."
    return translated or cleaned


def _keyword_text(keyword: object) -> str:
    raw = str(keyword or "").strip()
    if not raw:
        return ""
    normalized = raw.lower().strip(" :;,.()[]{}")
    return KEYWORD_TRANSLATIONS.get(normalized) or raw


def _focused_relevant_text(relevant_chunks: list[dict], fallback_text: str) -> str:
    if not relevant_chunks:
        return fallback_text

    top_score = float(relevant_chunks[0].get("score") or 0)
    if top_score <= 0:
        focused_chunks = relevant_chunks[:1]
    else:
        min_score = top_score * CHUNK_RANK_WEIGHTS.focused_score_ratio
        focused_chunks = [
            chunk
            for chunk in relevant_chunks
            if float(chunk.get("score") or 0) >= min_score
        ] or relevant_chunks[:1]

    return "\n".join(chunk["text"] for chunk in focused_chunks if chunk.get("text")) or fallback_text


def _analysis_payload(
    *,
    summary: str,
    intent: str,
    keywords: list[str] | None = None,
    metrics: list[str] | None = None,
    topics: list[dict] | None = None,
    document_keywords: list[str] | None = None,
    document_metrics: list[str] | None = None,
    document_topics: list[dict] | None = None,
    documents: list[dict] | None = None,
    relevant_chunks: list[dict] | None = None,
) -> dict:
    return {
        "summary": summary,
        "intent": intent,
        "keywords": keywords or [],
        "metrics": metrics or [],
        "topics": topics or [],
        "document_keywords": document_keywords or [],
        "document_metrics": document_metrics or [],
        "document_topics": document_topics or [],
        "documents": documents or [],
        "relevant_chunks": relevant_chunks or [],
    }


def _fallback_response(question: str, payload: dict) -> dict:
    return {
        "answer": build_concise_fallback_answer(question, payload),
        **payload,
    }


def build_analysis_answer(question: str, extracted_docs: list[dict]) -> dict:
    cleaned_docs = []
    for doc in extracted_docs:
        cleaned_text = _clean_text(doc.get("text", ""))
        if cleaned_text:
            cleaned_docs.append({**doc, "text": cleaned_text})

    combined_text = "\n".join(doc["text"] for doc in cleaned_docs if doc["text"])
    intent = _question_intent(question)

    if not combined_text.strip():
        summary = (
            "업로드 파일은 받았지만 추출 가능한 본문 텍스트가 거의 없습니다. "
            "이미지라면 OCR 설치가 필요할 수 있고, 구형 HWP는 HWPX 변환이 더 안정적입니다."
        )
        return _fallback_response(
            question,
            _analysis_payload(summary=summary, intent=intent),
        )

    relevant_chunks = rank_relevant_chunks(question, cleaned_docs, 6)
    relevant_text = _focused_relevant_text(relevant_chunks, combined_text)
    summary_points = _extractive_summary(relevant_text, question, 4)
    terms = _frequent_terms(relevant_text)
    metrics = _metric_candidates(relevant_text)
    topics = extract_topics(relevant_text)
    if relevant_text == combined_text:
        document_terms = terms
        document_metrics = metrics
        document_topics = topics
    else:
        document_terms = _frequent_terms(combined_text)
        document_metrics = _metric_candidates(combined_text)
        document_topics = extract_topics(combined_text)
    summary = " ".join(summary_points) or combined_text[:600]

    payload = _analysis_payload(
        summary=summary,
        intent=intent,
        keywords=terms,
        metrics=metrics,
        topics=topics,
        document_keywords=document_terms,
        document_metrics=document_metrics,
        document_topics=document_topics,
        documents=[_doc_brief(doc) for doc in cleaned_docs],
        relevant_chunks=relevant_chunks,
    )
    return _fallback_response(question, payload)


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
    sections.append(_korean_user_text(summary[:900], source_label="핵심 요약") if summary else "요약할 본문이 부족합니다.")

    metrics = fallback_answer.get("metrics") or []
    if metrics:
        sections.extend(["", "[수치 후보]"])
        sections.extend(f"- {_korean_user_text(metric, source_label='수치 근거')}" for metric in metrics[:8])

    keywords = fallback_answer.get("keywords") or []
    if keywords:
        keyword_items = [_keyword_text(keyword) for keyword in keywords[:10]]
        keyword_items = [keyword for keyword in keyword_items if keyword]
        keyword_label = "[핵심 키워드]"
        sections.extend(["", keyword_label, ", ".join(keyword_items)])

    if relevant_chunks:
        sections.extend(["", "[근거 구간]"])
        for chunk in relevant_chunks[:3]:
            source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', '?')}"
            focused = _top_sentences(chunk.get("text", ""), 1, question)
            preview = (focused[0] if focused else _clean_text(chunk.get("text", "")))[:360]
            sections.append(f"- {chunk.get('filename', '문서')} {source_label}: {_korean_user_text(preview, source_label='근거 구간')}")

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
