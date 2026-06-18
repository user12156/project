# 서비스: 문서 분석 전체 파이프라인을 조율하고 로컬/LLM 분석, grounding 검증, fallback 선택을 담당합니다.
"""문서 분석 서비스들을 하나의 흐름으로 묶는 파이프라인입니다.

라우터는 HTTP 요청/응답만 처리하고, 이 파일은 로컬 분석, LLM 호출,
그라운딩 검증, fallback 응답 선택을 한곳에서 조율합니다.
"""

import json
import re

from ..core.config import settings
from .fallback_analysis import (
    build_analysis_answer,
    build_concise_fallback_answer,
    build_empty_context_answer,
)
from .analysis.grounding import validate_grounding
from .analysis.compare_builder import build_document_compare_answer
from .analysis.query_analyzer import is_compare_request
from .chart.chart_asset import create_graph_visual
from .llm.service import analyze_with_llm
from .table.table_chart_builder import try_build_chart_from_tables
from .translation import translate_analysis_payload
from .visual_buttons.table_visual import create_table_visual
from .web_search import search_results_to_docs, wants_web_search, web_search


def _is_visual_request(question: str) -> bool:
    text = (question or "").lower()
    return any(
        keyword in text
        for keyword in (
            "그래프",
            "차트",
            "표",
            "시각화",
            "추이",
            "그려",
            "그려줘",
            "만들어",
            "chart",
            "graph",
            "table",
            "visual",
            "json",
        )
    )


def _extract_json_object(text: str) -> dict | None:
    cleaned = str(text or "").replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(cleaned[start:index + 1])
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _visual_numbers(config: dict) -> list[str]:
    values = []

    def visit(value):
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            values.append(str(value))
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {
                    "color",
                    "theme",
                    "headerBackground",
                    "headerTextColor",
                    "cellBackground",
                    "cellTextColor",
                    "borderColor",
                }:
                    continue
                visit(item)

    visit(config.get("data", []))
    return values


def _compact_number(value: str) -> str:
    return re.sub(r"[,\s]+", "", str(value or ""))


def _validate_visual_config(config: dict, extracted_docs: list[dict]) -> bool:
    evidence = _compact_number("\n".join(doc.get("text", "") for doc in extracted_docs))
    numbers = [number for number in _visual_numbers(config) if re.search(r"\d", number)]
    return bool(numbers) and all(_compact_number(number) in evidence for number in numbers)


def _local_visual_config(question: str, extracted_docs: list[dict]) -> dict | None:
    if not _is_visual_request(question):
        return None

    source_text = "\n\n".join(
        str(doc.get("text") or "").strip()
        for doc in extracted_docs
        if str(doc.get("text") or "").strip()
    )
    lowered = str(question or "").lower()
    wants_table = "표" in question or "table" in lowered
    wants_chart = any(
        keyword in lowered or keyword in question
        for keyword in ("그래프", "차트", "막대", "선그래프", "추이", "graph", "chart", "bar", "line")
    )

    if wants_chart:
        chart = try_build_chart_from_tables(question, extracted_docs)
        if chart and chart.get("type") != "chart_error":
            return chart
        return create_graph_visual(extracted_docs, source_text)

    if wants_table:
        return create_table_visual(extracted_docs, source_text)

    return None


def _local_visual_payload(
    visual_config: dict,
    fallback_answer: dict,
    *,
    selected_provider: str,
    llm_key_received: bool,
    llm_key_source: str,
) -> dict:
    return {
        **fallback_answer,
        "answer": json.dumps(visual_config, ensure_ascii=False),
        "keywords": fallback_answer.get("keywords", []),
        "metrics": fallback_answer.get("metrics", []),
        "topics": fallback_answer.get("topics", []),
        "relevant_chunks": fallback_answer.get("relevant_chunks", []),
        "intent": "시각화",
        "llm_used": False,
        "llm_key_received": llm_key_received,
        "llm_key_source": llm_key_source,
        "provider": selected_provider,
        "model": None,
        "llm_error": None,
        "suggested_questions": [],
    }


def _clean_evidence_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _assistant_intro(question: str, intent: str | None = None) -> str:
    labels = {
        "summary": "핵심 내용과 중요도",
        "analysis": "상세 분석과 해석",
        "importance": "중요도와 우선순위",
        "metrics": "동향과 수치 근거",
        "compare": "비교와 차이점",
        "extract": "중요 문장 발췌",
        "시각화": "시각화 자료",
        "general": "문서 분석",
    }
    label = labels.get(intent or "general", "문서 분석")
    if question:
        return f"질문하신 내용은 {label}에 관한 것으로 보입니다. 제가 문서에서 근거를 뽑아 정리해볼게요."
    return "업로드한 문서를 기준으로 핵심 내용을 먼저 정리해볼게요."


def _topic_label(fallback_answer: dict) -> str:
    topics = fallback_answer.get("topics") or fallback_answer.get("document_topics") or []
    for topic in topics:
        label = str(topic.get("label") or "").strip()
        if label:
            korean_count = len(re.findall(r"[가-힣]", label))
            english_count = len(re.findall(r"[A-Za-z]", label))
            if korean_count or english_count < 8:
                return label[:24]

    keywords = fallback_answer.get("keywords") or fallback_answer.get("document_keywords") or []
    meaningful = [
        str(keyword).strip()
        for keyword in keywords
        if str(keyword).strip() and re.search(r"[가-힣]", str(keyword))
    ]
    if meaningful:
        return ", ".join(meaningful[:2])[:24]

    return "문서 주요 내용"


def _has_metric_evidence(fallback_answer: dict) -> bool:
    return bool((fallback_answer.get("metrics") or []) or (fallback_answer.get("document_metrics") or []))


def _local_suggested_questions(fallback_answer: dict) -> list[str]:
    """LLM 없이도 문서 로컬 추출 결과만으로 후속 칩을 만듭니다."""

    if not (fallback_answer.get("summary") or fallback_answer.get("relevant_chunks")):
        return []

    topic = _topic_label(fallback_answer)
    metric_word = "수치 후보" if _has_metric_evidence(fallback_answer) else "핵심 항목"
    visual_questions = [
        f"[추천 시각화: 90점] 문서의 {metric_word}를 비교 막대 그래프 그려줘",
        f"[추천 시각화: 85점] {topic} 관련 항목을 표로 정리해줘",
    ]
    related_questions = [
        f"[연관 질문] 이 문서의 핵심 근거는 뭐야?",
        f"[연관 질문] 이 문서에서 추가로 확인해야 할 {metric_word}는 뭐야?",
    ]
    return [*visual_questions, *related_questions]


def _merge_llm_answer_with_evidence(question: str, llm_answer: str, fallback_answer: dict) -> str:
    sections = [
        _assistant_intro(question, fallback_answer.get("intent")),
        llm_answer.strip(),
    ]

    metrics = fallback_answer.get("metrics") or []
    if metrics:
        sections.append("[수치 후보]\n" + "\n".join(f"- {metric}" for metric in metrics[:6]))

    topics = fallback_answer.get("topics") or []
    if topics:
        topic_lines = []
        for topic in topics[:5]:
            keywords = ", ".join(topic.get("keywords", [])[:5]) or topic.get("label", "주제")
            topic_lines.append(f"- {topic.get('label', '주제')}: {keywords}")
        sections.append("[문서 주제 후보]\n" + "\n".join(topic_lines))

    relevant_chunks = fallback_answer.get("relevant_chunks") or []
    if relevant_chunks:
        chunk_lines = []
        for chunk in relevant_chunks[:4]:
            filename = chunk.get("filename", "문서")
            source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', '?')}"
            score = chunk.get("score")
            evidence_text = _clean_evidence_text(chunk.get("text", ""))
            chunk_lines.append(f"- {filename} {source_label} (관련도 {score}): {evidence_text}")
        sections.append("[관련 문서 구간]\n" + "\n".join(chunk_lines))

    documents = fallback_answer.get("documents") or []
    doc_lines = []
    for doc in documents[:3]:
        filename = doc.get("filename", "문서")
        key_points = doc.get("key_points") or []
        keywords = doc.get("keywords") or []
        if key_points:
            doc_lines.append(f"- {filename}: {_clean_evidence_text(key_points[0])}")
        elif keywords:
            doc_lines.append(f"- {filename}: {', '.join(keywords[:6])}")
    if doc_lines:
        sections.append("[문서별 핵심 근거]\n" + "\n".join(doc_lines))

    return "\n\n".join(section for section in sections if section.strip())


def _with_korean_answer(payload: dict) -> dict:
    return translate_analysis_payload(payload)


def _llm_first_payload(
    *,
    fallback_answer: dict,
    llm_answer: dict,
    llm_key_received: bool,
    llm_key_source: str,
    suggested_questions: list[str],
    web_docs: list[dict] | None = None,
    llm_error: str | None = None,
) -> dict:
    """Return a key-backed LLM answer while keeping local extraction as metadata."""

    return _with_korean_answer({
        **fallback_answer,
        "answer": llm_answer.get("answer", ""),
        "keywords": fallback_answer.get("keywords", []) or llm_answer.get("keywords", []),
        "metrics": fallback_answer.get("metrics", []),
        "topics": fallback_answer.get("topics", []),
        "relevant_chunks": fallback_answer.get("relevant_chunks", []),
        "intent": llm_answer.get("intent", fallback_answer.get("intent", "분석")),
        "llm_used": True,
        "llm_key_received": llm_key_received,
        "llm_key_source": llm_key_source,
        "provider": llm_answer.get("provider"),
        "model": llm_answer.get("model"),
        "llm_error": llm_error,
        "suggested_questions": llm_answer.get("suggested_questions", []) or suggested_questions,
        "comparison_table": llm_answer.get("comparison_table", []),
        "time_series_comparison_table": llm_answer.get("time_series_comparison_table", []),
        "experiment_comparison_table": llm_answer.get("experiment_comparison_table", []),
        "experiment_chart": llm_answer.get("experiment_chart"),
        "compare": llm_answer.get("compare", {}),
        "web_sources": web_docs or [],
    })


def _resolve_llm_provider_and_keys(
    provider: str,
    openai_api_key: str | None,
    google_api_key: str | None,
) -> tuple[str, str, str, bool]:
    selected = (provider or "auto").strip().lower()
    if selected not in {"auto", "gemini", "google", "openai"}:
        selected = "auto"

    request_openai = (openai_api_key or "").strip()
    request_google = (google_api_key or "").strip()
    env_openai = settings.openai_api_key
    env_google = settings.gemini_api_key or settings.google_api_key

    if selected == "openai":
        if not request_openai and not env_openai and (request_google or env_google):
            key_source = "request" if request_google else "env"
            return "gemini", request_google or env_google, key_source, True
        key_source = "request" if request_openai else "env" if env_openai else "none"
        return "openai", request_openai or env_openai, key_source, key_source != "none"

    if selected in {"gemini", "google"}:
        if not request_google and not env_google and (request_openai or env_openai):
            key_source = "request" if request_openai else "env"
            return "openai", request_openai or env_openai, key_source, True
        key_source = "request" if request_google else "env" if env_google else "none"
        return "gemini", request_google or env_google, key_source, key_source != "none"

    if request_openai:
        return "openai", request_openai, "request", True
    if request_google:
        return "gemini", request_google, "request", True
    if env_openai:
        return "openai", env_openai, "env", True
    if env_google:
        return "gemini", env_google, "env", True
    return "openai", "", "none", False


def run_analysis_pipeline(
    *,
    question: str,
    extracted_docs: list[dict],
    uploaded_filenames: list[str] | None = None,
    llm_provider: str = "gemini",
    openai_api_key: str | None = None,
    google_api_key: str | None = None,
    analysis_text: str = "",
) -> dict:
    """분석 서비스의 단일 진입점입니다."""

    uploaded_filenames = uploaded_filenames or []
    fallback_answer = build_analysis_answer(question, extracted_docs)
    extraction_errors = [
        str(doc.get("extraction_error") or "").strip()
        for doc in extracted_docs
        if str(doc.get("extraction_error") or "").strip()
    ]
    local_suggested_questions = _local_suggested_questions(fallback_answer)
    has_grounded_docs = any(str(doc.get("text", "")).strip() for doc in extracted_docs)
    should_compare_documents = is_compare_request(question) or len(
        [doc for doc in extracted_docs if str(doc.get("text", "")).strip()]
    ) >= 2
    is_visual_request = _is_visual_request(question)
    web_docs = search_results_to_docs(web_search(question)) if has_grounded_docs and wants_web_search(question) else []
    selected_provider, resolved_key, llm_key_source, llm_key_received = _resolve_llm_provider_and_keys(
        llm_provider,
        openai_api_key,
        google_api_key,
    )

    if not has_grounded_docs:
        return _with_korean_answer({
            **fallback_answer,
            "answer": build_empty_context_answer(
                question,
                fallback_answer,
                bool(uploaded_filenames),
                uploaded_filenames,
                extraction_errors,
            ),
            "llm_used": False,
            "provider": None,
            "model": None,
            "llm_error": None,
            "llm_key_received": False,
            "llm_key_source": None,
            "suggested_questions": [],
        })

    local_visual_config = _local_visual_config(question, extracted_docs)
    if local_visual_config:
        return _local_visual_payload(
            local_visual_config,
            fallback_answer,
            selected_provider=selected_provider,
            llm_key_received=llm_key_received,
            llm_key_source=llm_key_source,
        )

    if should_compare_documents:
        compare_payload = build_document_compare_answer(question, extracted_docs)
        if compare_payload:
            return _with_korean_answer({
                **fallback_answer,
                **compare_payload,
                "llm_used": False,
                "provider": selected_provider,
                "model": None,
                "llm_error": None,
                "llm_key_received": llm_key_received,
                "llm_key_source": llm_key_source,
                "intent": "compare",
            })

    if not llm_key_received:
        return _with_korean_answer({
            **fallback_answer,
            "answer": build_concise_fallback_answer(question, fallback_answer),
            "llm_used": False,
            "provider": selected_provider,
            "model": None,
            "llm_error": None,
            "llm_key_received": False,
            "llm_key_source": "none",
            "suggested_questions": local_suggested_questions,
        })

    llm_answer = analyze_with_llm(
        question,
        extracted_docs,
        provider=selected_provider,
        openai_api_key=resolved_key if selected_provider == "openai" else None,
        google_api_key=resolved_key if selected_provider == "gemini" else None,
        analysis_text=analysis_text,
        relevant_chunks=fallback_answer.get("relevant_chunks", []),
        web_docs=web_docs,
    )

    if not llm_answer.get("llm_used"):
        return _with_korean_answer({
            **fallback_answer,
            "answer": build_concise_fallback_answer(question, fallback_answer),
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": llm_answer.get("llm_error"),
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": llm_answer.get("suggested_questions", []) or local_suggested_questions,
        })

    visual_config = _extract_json_object(llm_answer["answer"]) if is_visual_request else None
    if visual_config and visual_config.get("type") == "chart_error":
        return {
            **fallback_answer,
            "answer": json.dumps(visual_config, ensure_ascii=False),
            "keywords": fallback_answer.get("keywords", []),
            "metrics": fallback_answer.get("metrics", []),
            "topics": fallback_answer.get("topics", []),
            "relevant_chunks": fallback_answer.get("relevant_chunks", []),
            "intent": fallback_answer.get("intent", "visual"),
            "llm_used": True,
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "suggested_questions": llm_answer.get("suggested_questions", []),
        }
    if visual_config and _validate_visual_config(visual_config, extracted_docs):
        return {
            **fallback_answer,
            "answer": json.dumps(visual_config, ensure_ascii=False),
            "keywords": fallback_answer.get("keywords", []),
            "metrics": fallback_answer.get("metrics", []),
            "topics": fallback_answer.get("topics", []),
            "relevant_chunks": fallback_answer.get("relevant_chunks", []),
            "intent": fallback_answer.get("intent", "시각화"),
            "llm_used": True,
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "suggested_questions": llm_answer.get("suggested_questions", []),
        }

    if is_visual_request and visual_config:
        return _with_korean_answer({
            **fallback_answer,
            "answer": build_concise_fallback_answer(question, fallback_answer),
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": "PaperMate가 시각화 데이터에서 업로드 문서에 없는 수치를 감지해 로컬 근거 답변으로 전환했습니다.",
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": local_suggested_questions,
        })

    grounding = validate_grounding(
        llm_answer["answer"],
        [*extracted_docs, *web_docs],
        fallback_answer.get("relevant_chunks", []),
        fallback_answer.get("metrics", []),
    )
    if not grounding.get("passed"):
        reason = (
            "문서 근거 점검에서 업로드 문서와 직접 일치하지 않는 수치가 감지되었지만, "
            "API 키가 있어 LLM 답변을 우선 표시했습니다."
            if grounding.get("unsupported_numbers")
            else "문서 근거 점검에서 낮은 단어 일치도가 감지되었지만, API 키가 있어 LLM 답변을 우선 표시했습니다."
        )
        return _llm_first_payload(
            fallback_answer=fallback_answer,
            llm_answer=llm_answer,
            llm_key_received=llm_key_received,
            llm_key_source=llm_key_source,
            suggested_questions=local_suggested_questions,
            web_docs=web_docs,
            llm_error=reason,
        )

    if visual_config:
        return {
            **fallback_answer,
            "answer": json.dumps(visual_config, ensure_ascii=False),
            "keywords": fallback_answer.get("keywords", []),
            "metrics": fallback_answer.get("metrics", []),
            "topics": fallback_answer.get("topics", []),
            "relevant_chunks": fallback_answer.get("relevant_chunks", []),
            "intent": fallback_answer.get("intent", "시각화"),
            "llm_used": True,
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "suggested_questions": llm_answer.get("suggested_questions", []),
        }

    return _llm_first_payload(
        fallback_answer=fallback_answer,
        llm_answer=llm_answer,
        llm_key_received=llm_key_received,
        llm_key_source=llm_key_source,
        suggested_questions=local_suggested_questions,
        web_docs=web_docs,
    )
