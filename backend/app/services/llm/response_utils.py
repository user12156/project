"""Common LLM response parsing, fallback, and postprocessing helpers."""

import json
import re

from app.services.openai_client import OPENAI_CHUNK_TIMEOUT_SECONDS, OPENAI_REWRITE_TIMEOUT_SECONDS, make_openai_client
from app.services.visual_buttons.graph_visual import process_chart_response


def llm_error(message: str, provider: str, model: str | None = None) -> dict:
    return {
        "answer": "",
        "llm_used": False,
        "provider": provider,
        "model": model,
        "llm_error": message,
    }


def parse_suggested_questions(answer: str) -> tuple[str, list[str]]:
    parts = answer.split("===SUGGESTED_QUESTIONS===")
    main_answer = parts[0].strip()
    questions = []
    if len(parts) > 1:
        raw_qs = parts[1].strip().split("\n")
        for q in raw_qs:
            cleaned = q.strip().lstrip("-").lstrip("*").lstrip("0123456789. ").strip()
            if cleaned:
                questions.append(cleaned)
    return main_answer, questions


def korean_char_ratio(text: str) -> float:
    letters = re.findall(r"[A-Za-z가-힣]", text or "")
    if not letters:
        return 1.0
    korean_letters = [char for char in letters if "가" <= char <= "힣"]
    return len(korean_letters) / len(letters)


def needs_korean_rewrite(answer: str) -> bool:
    if not answer:
        return False
    if korean_char_ratio(answer) >= 0.25:
        return False
    english_words = re.findall(r"\b[A-Za-z]{4,}\b", answer)
    korean_words = re.findall(r"[가-힣]{2,}", answer)
    return len(english_words) >= max(8, len(korean_words) * 2)


def rewrite_answer_in_korean(answer: str, api_key: str, model: str) -> str:
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        return answer

    prompt = (
        "아래 답변은 문서 분석 결과입니다. 문서 원문이 영어여도 최종 사용자가 보는 답변은 반드시 자연스러운 한국어여야 합니다.\n"
        "고유명사, 논문 제목, 약어, 수치, 인용 표기, JSON 키, '===SUGGESTED_QUESTIONS===' 구분자는 보존하세요.\n"
        "본문의 분석, 요약, 추천 질문, 표/차트 라벨 설명은 한국어로 번역하고 어색한 직역은 다듬어 주세요.\n\n"
        f"[답변]\n{answer}"
    )

    try:
        client = make_openai_client(api_key, OPENAI_REWRITE_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        rewritten = (response.choices[0].message.content or "").strip()
        return rewritten or answer
    except Exception as exc:
        print(f"Korean rewrite failed: {exc}")
        return answer


def chunk_text(text: str, chunk_size: int = 30000) -> list[str]:
    normalized = " ".join(str(text or "").split())
    return [normalized[index : index + chunk_size] for index in range(0, len(normalized), chunk_size)]


def extract_chunk_with_openai(
    chunk: str,
    api_key: str,
    model: str,
    question: str = "",
    is_visual: bool = False,
) -> str:
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        return ""

    if is_visual:
        prompt = (
            "You are a strict data extraction assistant.\n"
            f"The user wants to generate a visualization based on this request: '{question}'.\n"
            "Extract only relevant numerical data, table rows, labels, dates, categories, and exact facts from the text chunk below.\n"
            "If there is no relevant data in this chunk, output nothing.\n\n"
            f"[Text Chunk]\n{chunk}"
        )
    else:
        prompt = (
            "You are a fast document extraction assistant.\n"
            "Extract the most important facts, numbers, named entities, claims, methods, and conclusions from the text chunk below.\n"
            "Keep the original meaning, but write concise bullet points in Korean. Preserve proper nouns, technical terms, numbers, and citations when needed.\n\n"
            f"[Text Chunk]\n{chunk}"
        )

    try:
        client = make_openai_client(api_key, OPENAI_CHUNK_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=900,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"Chunk extraction failed: {exc}")
        return ""


def postprocess_visual_answer(answer: str) -> str:
    try:
        return process_chart_response(answer)
    except Exception as exc:
        return json.dumps(
            {
                "type": "chart_error",
                "reasoning_summary": "그래프 응답을 후처리하는 중 오류가 발생했습니다.",
                "errors": [str(exc)],
                "rawAnswer": answer,
            },
            ensure_ascii=False,
        )
