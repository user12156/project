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
from .llm.service import analyze_with_llm
from .translation import translate_analysis_payload


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


def _clean_evidence_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _assistant_intro(question: str, intent: str | None = None) -> str:
    labels = {
        "summary": "핵심 내용과 중요도",
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
        key_source = "request" if request_openai else "env" if env_openai else "none"
        return "openai", request_openai or env_openai, key_source, key_source != "none"

    if selected in {"gemini", "google"}:
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
    has_grounded_docs = any(str(doc.get("text", "")).strip() for doc in extracted_docs)
    is_visual_request = _is_visual_request(question)
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
            ),
            "llm_used": False,
            "provider": None,
            "model": None,
            "llm_error": None,
            "llm_key_received": False,
            "llm_key_source": None,
            "suggested_questions": [],
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
            "suggested_questions": [],
        })

    llm_answer = analyze_with_llm(
        question,
        extracted_docs,
        provider=selected_provider,
        openai_api_key=resolved_key if selected_provider == "openai" else None,
        google_api_key=resolved_key if selected_provider == "gemini" else None,
        analysis_text=analysis_text,
        relevant_chunks=fallback_answer.get("relevant_chunks", []),
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
            "suggested_questions": llm_answer.get("suggested_questions", []),
        })

    visual_config = _extract_json_object(llm_answer["answer"]) if is_visual_request else None
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

    grounding = validate_grounding(
        llm_answer["answer"],
        extracted_docs,
        fallback_answer.get("relevant_chunks", []),
        fallback_answer.get("metrics", []),
    )
    if not grounding.get("passed"):
        return _with_korean_answer({
            **fallback_answer,
            "answer": _merge_llm_answer_with_evidence(question, llm_answer["answer"], fallback_answer),
            "llm_used": True,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": "PaperMate가 문서 근거 점검에서 일부 낮은 일치도를 감지했습니다. 답변 아래 근거 구간을 함께 확인해주세요.",
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": llm_answer.get("suggested_questions", []),
        })

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

    return _with_korean_answer({
        **fallback_answer,
        "answer": _merge_llm_answer_with_evidence(question, llm_answer["answer"], fallback_answer),
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
        "suggested_questions": llm_answer.get("suggested_questions", []),
    })
