"""Public LLM analysis entrypoint."""

from app.core.config import settings
from app.services.llm.gemini_provider import analyze_with_gemini
from app.services.llm.openai_provider import analyze_with_openai
from app.services.llm.response_utils import llm_error


def analyze_with_llm(
    question: str,
    extracted_docs: list[dict],
    provider: str = "gemini",
    openai_api_key: str | None = None,
    google_api_key: str | None = None,
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
) -> dict:
    selected_provider = (provider or "auto").strip().lower()
    if selected_provider == "auto":
        if openai_api_key or settings.openai_api_key:
            selected_provider = "openai"
        elif google_api_key or settings.gemini_api_key or settings.google_api_key:
            selected_provider = "gemini"
        else:
            selected_provider = "openai"

    if selected_provider in {"gemini", "google"}:
        api_key = google_api_key or settings.gemini_api_key or settings.google_api_key
        if not api_key:
            return llm_error("PaperMate 분석 키가 없어 기본 문서 추출로 응답했습니다.", "gemini", settings.gemini_model)
        return analyze_with_gemini(question, extracted_docs, api_key, analysis_text, relevant_chunks)

    api_key = openai_api_key or settings.openai_api_key
    if not api_key:
        return llm_error("PaperMate 분석 키가 없어 기본 문서 추출로 응답했습니다.", "openai", settings.openai_model)
    return analyze_with_openai(question, extracted_docs, api_key, analysis_text, relevant_chunks)
