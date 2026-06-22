"""OpenAI provider integration."""

import concurrent.futures
import logging

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


logger = logging.getLogger(__name__)


def analyze_with_openai(
    question: str,
    extracted_docs: list[dict],
    api_key: str,
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
    web_docs: list[dict] | None = None,
) -> dict:
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        return llm_error("openai 패키지가 설치되어 있지 않습니다.", "openai")

    model = settings.openai_model
    client = make_openai_client(api_key, OPENAI_ANALYSIS_TIMEOUT_SECONDS)
    system_prompt, user_prompt = build_prompts(question, extracted_docs, analysis_text, relevant_chunks, web_docs=web_docs)

    question_lower = (question or "").strip().lower()
    broad_summary_patterns = (
        "요약",
        "요약해줘",
        "정리",
        "정리해줘",
        "분석",
        "분석해줘",
        "핵심 요약",
        "전체 요약",
    )
    is_general_summary = (
        not question_lower
        or question_lower in broad_summary_patterns
        or any(question_lower.endswith(pattern) and len(question_lower) <= 18 for pattern in broad_summary_patterns)
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
            web_block = ""
            if web_docs:
                web_block = "[Web Search Context]\n" + "\n\n".join(
                    f"[웹 {index}]\n{doc.get('text', '')}"
                    for index, doc in enumerate(web_docs, start=1)
                ) + "\n\n"

            if visual_request:
                user_prompt = (
                    "[Uploaded Document Context - Extracted Facts]\n"
                    f"{extracted_context}\n\n"
                    f"{web_block}"
                    f"{history_block}"
                    f"The user requested a visualization: '{question}'. "
                    "Return only the strict JSON object required by the system instructions."
                )
            else:
                user_prompt = (
                    "[User Request]\n"
                    f"{question or '문서의 전반적인 내용을 꼼꼼하게 분석해줘.'}\n\n"
                    "[Uploaded Document Context - Extracted Facts]\n"
                    f"{extracted_context}\n\n"
                    f"{web_block}"
                    f"{history_block}"
                    "Answer the current user request directly. Do not repeat a previous answer unless the current request asks for the same thing. "
                    "Base factual claims only on the extracted document facts above and the explicit web context if provided. "
                    "Use previous conversation history only to understand continuity, never as a factual source or as a template to copy. "
                    "The source facts may include English, but the final user-facing answer must be natural Korean. "
                    "Preserve concrete facts, numbers, names, methods, and conclusions."
                )

    try:
        request_kwargs = {}
        if visual_request:
            request_kwargs["response_format"] = {"type": "json_object"}

        user_content = chat_user_content(user_prompt, extracted_docs)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            **request_kwargs,
        )

        content = response.choices[0].message.content
        if content is None:
            logger.warning(
                "OpenAI response content is None. finish_reason=%s",
                getattr(response.choices[0], "finish_reason", None),
            )
            return llm_error("PaperMate 분석 엔진이 빈 답변을 반환했습니다.", "openai", model)

        answer = content.strip()
    except Exception as exc:
        if getattr(exc, "status_code", None) == 400:
            try:
                logger.info("OpenAI multimodal request failed with 400; retrying text-only analysis.")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    **request_kwargs,
                )

                content = response.choices[0].message.content
                if content is None:
                    logger.warning(
                        "OpenAI retry response content is None. finish_reason=%s",
                        getattr(response.choices[0], "finish_reason", None),
                    )
                    return llm_error("PaperMate 분석 엔진이 빈 답변을 반환했습니다.", "openai", model)

                answer = content.strip()
            except Exception as retry_exc:
                return llm_error(openai_error_message(retry_exc), "openai", model)
        else:
            return llm_error(openai_error_message(exc), "openai", model)

    if not answer:
        return llm_error("PaperMate 분석 엔진이 빈 답변을 반환했습니다.", "openai", model)

    if visual_request:
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
