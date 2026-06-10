"""OpenAI provider integration."""

import concurrent.futures

from app.core.config import settings
from app.services.llm.prompt_builder import build_prompts, chat_user_content, is_visual_request
from app.services.llm.response_utils import (
    chunk_text,
    extract_chunk_with_openai,
    llm_error,
    needs_korean_rewrite,
    parse_suggested_questions,
    postprocess_visual_answer,
    rewrite_answer_in_korean,
)
from app.services.openai_client import OPENAI_ANALYSIS_TIMEOUT_SECONDS, make_openai_client, openai_error_message


def analyze_with_openai(
    question: str,
    extracted_docs: list[dict],
    api_key: str,
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
) -> dict:
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        return llm_error("openai 패키지가 설치되어 있지 않습니다.", "openai")

    model = settings.openai_model
    client = make_openai_client(api_key, OPENAI_ANALYSIS_TIMEOUT_SECONDS)
    system_prompt, user_prompt = build_prompts(question, extracted_docs, analysis_text, relevant_chunks)

    question_lower = (question or "").strip().lower()
    is_general_summary = not question_lower or any(
        keyword in question_lower for keyword in ("요약", "분석", "정리", "핵심")
    )
    visual_request = is_visual_request(question)

    raw_document_text = "\n\n".join(str(doc.get("text", "")) for doc in extracted_docs)
    should_map_reduce = (
        len(raw_document_text) > 15000
        and "mini" in model.lower()
        and (is_general_summary or visual_request)
    )

    if should_map_reduce:
        chunks = chunk_text(raw_document_text)
        results = [""] * len(chunks)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(
                    extract_chunk_with_openai,
                    chunk,
                    api_key,
                    model,
                    question,
                    visual_request,
                ): index
                for index, chunk in enumerate(chunks)
            }

            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception:
                    results[index] = ""

        extracted_context = "\n\n---\n\n".join(result for result in results if result)

        if extracted_context:
            history_block = f"[Previous Conversation History]\n{analysis_text}\n\n" if analysis_text else ""

            if visual_request:
                user_prompt = (
                    "[Uploaded Document Context - Extracted Facts]\n"
                    f"{extracted_context}\n\n"
                    f"{history_block}"
                    f"The user requested a visualization: '{question}'. "
                    "Return only the strict JSON object required by the system instructions."
                )
            else:
                user_prompt = (
                    "[Uploaded Document Context - Extracted Facts]\n"
                    f"{extracted_context}\n\n"
                    f"{history_block}"
                    "Write a thorough Korean analysis based only on the extracted facts above. "
                    "The source facts may include English, but the final user-facing answer must be natural Korean. "
                    "Preserve concrete facts, numbers, names, methods, and conclusions."
                )

    try:
        request_kwargs = {}
        if visual_request:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_user_content(user_prompt, extracted_docs)},
            ],
            temperature=0.2,
            **request_kwargs,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as exc:
        return llm_error(openai_error_message(exc), "openai", model)

    if not answer:
        return llm_error("PaperMate 분석 엔진이 빈 답변을 반환했습니다.", "openai", model)

    if visual_request:
        answer = postprocess_visual_answer(answer)
        return {
            "answer": answer,
            "suggested_questions": [],
            "llm_used": True,
            "model": model,
            "provider": "openai",
        }

    if needs_korean_rewrite(answer):
        answer = rewrite_answer_in_korean(answer, api_key, model)

    main_answer, questions = parse_suggested_questions(answer)

    return {
        "answer": main_answer,
        "suggested_questions": questions,
        "llm_used": True,
        "model": model,
        "provider": "openai",
    }
