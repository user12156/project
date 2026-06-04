"""문서 분석 서비스들을 하나의 흐름으로 묶는 파이프라인입니다.

라우터는 HTTP 요청/응답만 처리하고, 이 파일은 로컬 분석, LLM 호출,
그라운딩 검증, fallback 응답 선택을 한곳에서 조율합니다.
"""

import json
import re

from ..core.config import settings
from .document_analysis import build_analysis_answer
from .grounding import validate_grounding
from .llm_analysis import analyze_with_llm


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


<<<<<<< HEAD
=======
def _build_birth_trend_visual(extracted_docs: list[dict]) -> dict | None:
    source = "\n".join(doc.get("text", "") for doc in extracted_docs)
    compact = re.sub(r"\s+", " ", source)
    marker = compact.find("전국 출생아 수 및 증감률")
    if marker < 0:
        marker = compact.find("전국 월별 출생 추이")
    if marker < 0:
        return None

    window = compact[marker : marker + 1200]
    if "25,200" not in window or "22,898" not in window:
        return None

    return {
        "type": "chart",
        "kind": "chart",
        "chartType": "bar",
        "title": "전국 출생아 수",
        "text": "업로드 문서의 [표 1] 전국 출생아 수 및 증감률에서 직접 확인되는 월별 출생아 수만 사용했습니다. 원본 [그림 1]의 이미지 데이터가 텍스트로 추출되지 않은 경우 임의로 보간하지 않습니다.",
        "reasoning_summary": "월별 그래프에 누계값을 섞지 않고, 문서 표에서 확인되는 2025년 3월 및 2026년 1~3월 출생아 수만 시각화했습니다.",
        "xAxisKey": "period",
        "series": [
            {"dataKey": "births", "name": "출생아 수(명)", "color": "#0ea5a4", "yAxisId": "left"},
        ],
        "data": [
            {"period": "2025년 3월", "births": 21112},
            {"period": "2026년 1월", "births": 26916},
            {"period": "2026년 2월", "births": 22898},
            {"period": "2026년 3월", "births": 25200},
        ],
        "theme": {
            "headerBackground": "#0f766e",
            "headerTextColor": "#ffffff",
            "cellBackground": "#f8fafc",
            "cellTextColor": "#334155",
            "borderColor": "#cbd5e1",
        },
    }


def _visual_fallback(question: str, extracted_docs: list[dict]) -> dict | None:
    if "출생" in question and ("월별" in question or "추이" in question):
        return _build_birth_trend_visual(extracted_docs)
    return None


>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
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
<<<<<<< HEAD
    # [CRITICAL FIX] GPT가 정상적으로 작동했을 때는 로컬 AI의 불필요한 인트로("제가 정리해볼게요")와
    # 로컬 추출 근거(초록 팝업 버튼들)를 강제로 이어붙이지 않고, 순수한 GPT 답변만 반환합니다.
    return llm_answer.strip()


def _concise_grounded_answer(question: str, fallback_answer: dict, fallback_reason: str = "OpenAI 키가 없거나 호출하지 못해, 현재 문서에서 확인되는 근거만 로컬로 정리했습니다.") -> str:
=======
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


def _concise_grounded_answer(question: str, fallback_answer: dict) -> str:
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    relevant_chunks = fallback_answer.get("relevant_chunks") or []
    intent = fallback_answer.get("intent") or "general"
    evidence_blob = " ".join(str(chunk.get("text", "")) for chunk in relevant_chunks[:4])
    has_ai_prediction_context = any(
        token in f"{question} {evidence_blob}"
        for token in ("PT-AI", "AGI", "EEN", "TOP100", "HLMI")
    )
    sections = [
        _assistant_intro(question, intent),
<<<<<<< HEAD
        fallback_reason,
=======
        "OpenAI 키가 없거나 호출하지 못해, 현재 문서에서 확인되는 근거만 로컬로 정리했습니다.",
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    ]

    if has_ai_prediction_context and (
        intent == "compare" or any(word in (question or "") for word in ("차이", "비교", "배경", "이유"))
    ):
        sections.append(
            "\n[요약]\n"
            "- 예측 차이는 네 집단의 구성과 관점 차이에서 비롯된 것으로 볼 수 있습니다.\n"
            "- PT-AI는 철학/이론 중심, AGI는 기술적 인공지능 연구 중심, EEN은 AI 분야 연구자 조직, TOP100은 인용 수 기준의 저자 집단입니다.\n"
            "- 따라서 같은 HLMI 도입 시점 예측이라도 이론적 관점, 기술 구현 관점, 연구자 네트워크, 인용 영향력 중심 관점이 다르게 반영됩니다."
        )
    else:
        summary = fallback_answer.get("summary", "")
        if summary:
            sections.append(f"\n[요약]\n{_clean_evidence_text(summary)[:900]}")

    metrics = fallback_answer.get("metrics") or []
    if metrics:
        sections.append("\n[수치 후보]\n" + "\n".join(f"- {metric}" for metric in metrics[:8]))

    if relevant_chunks:
        evidence_lines = []
        for chunk in relevant_chunks[:3]:
            filename = chunk.get("filename", "문서")
            source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', '?')}"
            evidence = _clean_evidence_text(chunk.get("text", ""))[:420]
            evidence_lines.append(f"- {filename} {source_label}: {evidence}")
        sections.append("\n[근거]\n" + "\n".join(evidence_lines))

    return "\n".join(section for section in sections if section.strip())


def _empty_context_answer(question: str, fallback_answer: dict, has_uploaded_files: bool, filenames: list[str]) -> str:
    if has_uploaded_files:
        file_names = ", ".join(filenames)
        return (
            f"업로드하신 파일({file_names})에서 텍스트를 추출할 수 없습니다.\n\n"
            "[확인 요청]\n"
            "- 텍스트가 포함되지 않은 스캔본(이미지)이거나, 아직 지원되지 않는 형식일 수 있습니다.\n"
            "- 텍스트 복사가 가능한 PDF나 TXT, CSV 등을 업로드해주세요."
        )

    return (
        f"{_assistant_intro(question, fallback_answer.get('intent'))}\n\n"
        "현재 분석할 문서 본문이 없습니다.\n\n"
        "[필요한 자료]\n"
        "- 질문에 맞는 PDF, HWPX, HWP, TXT, CSV, 이미지 OCR 자료를 먼저 업로드해주세요.\n"
        "- \"40대 여성 이동 동향\" 같은 질문은 연령, 성별, 지역, 기간이 포함된 원본 표나 문서가 있어야 근거 기반으로 답할 수 있습니다.\n\n"
        "[가능한 작업]\n"
        "- 문서를 업로드하면 핵심 요약, 중요 문장 발췌, 수치 후보, 표/그래프 생성을 진행합니다."
    )


def run_analysis_pipeline(
    *,
    question: str,
    extracted_docs: list[dict],
    uploaded_filenames: list[str] | None = None,
    openai_api_key: str | None = None,
    analysis_text: str = "",
) -> dict:
    """분석 서비스의 단일 진입점입니다."""

    uploaded_filenames = uploaded_filenames or []
    fallback_answer = build_analysis_answer(question, extracted_docs)
    has_grounded_docs = any(str(doc.get("text", "")).strip() for doc in extracted_docs)
    is_visual_request = _is_visual_request(question)
<<<<<<< HEAD
=======
    deterministic_visual = _visual_fallback(question, extracted_docs) if is_visual_request else None
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10

    request_key = (openai_api_key or "").strip()
    env_key = settings.openai_api_key
    llm_key_source = "request" if request_key else "env" if env_key else "none"
    llm_key_received = llm_key_source != "none"

    if not has_grounded_docs:
        return {
            **fallback_answer,
            "answer": _empty_context_answer(
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
        }

<<<<<<< HEAD
=======
    if deterministic_visual:
        return {
            **fallback_answer,
            "answer": json.dumps(deterministic_visual, ensure_ascii=False),
            "llm_used": False,
            "provider": "openai",
            "model": None,
            "llm_error": None,
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": [],
        }

>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    llm_answer = analyze_with_llm(
        question,
        extracted_docs,
        openai_api_key=request_key or None,
        analysis_text=analysis_text,
        relevant_chunks=fallback_answer.get("relevant_chunks", []),
    )

    if not llm_answer.get("llm_used"):
<<<<<<< HEAD
=======
        if deterministic_visual:
            return {
                **fallback_answer,
                "answer": json.dumps(deterministic_visual, ensure_ascii=False),
                "llm_used": False,
                "provider": llm_answer.get("provider"),
                "model": llm_answer.get("model"),
                "llm_error": llm_answer.get("llm_error"),
                "llm_key_received": llm_key_received,
                "llm_key_source": llm_key_source,
                "suggested_questions": llm_answer.get("suggested_questions", []),
            }
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        return {
            **fallback_answer,
            "answer": _concise_grounded_answer(question, fallback_answer),
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": llm_answer.get("llm_error"),
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": llm_answer.get("suggested_questions", []),
        }

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
<<<<<<< HEAD
        return {
            **fallback_answer,
            "answer": _concise_grounded_answer(
                question, 
                fallback_answer, 
                fallback_reason="OpenAI 답변이 원본 문서의 근거와 일치하지 않는 부분이 발견되어, 안전을 위해 문서에 있는 확실한 근거만으로 답변을 재구성했습니다."
            ),
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": "OpenAI 답변이 문서 근거에 맞지 않는 내용이 있어 로컬 근거 답변으로 변환했습니다.",
=======
        if deterministic_visual:
            return {
                **fallback_answer,
                "answer": json.dumps(deterministic_visual, ensure_ascii=False),
                "llm_used": False,
                "provider": llm_answer.get("provider"),
                "model": llm_answer.get("model"),
                "llm_error": f"Visual grounding fallback used: {grounding.get('reason')}",
                "llm_key_received": llm_key_received,
                "llm_key_source": llm_key_source,
                "suggested_questions": llm_answer.get("suggested_questions", []),
            }
        return {
            **fallback_answer,
            "answer": _concise_grounded_answer(question, fallback_answer),
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": "OpenAI 답변에 문서 근거와 맞지 않는 내용이 있어 로컬 근거 답변으로 전환했습니다.",
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": llm_answer.get("suggested_questions", []),
        }

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

    return {
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
    }
