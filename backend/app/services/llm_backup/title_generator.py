"""Chat title generation across configured LLM providers."""

from app.core.config import settings
from app.services.llm.gemini_provider import call_gemini
from app.services.openai_client import OPENAI_TITLE_TIMEOUT_SECONDS, make_openai_client


def generate_chat_title(
    question: str,
    provider: str = "gemini",
    openai_api_key: str | None = None,
    google_api_key: str | None = None,
    analysis_text: str = "",
) -> str:
    """사용자의 첫 질문을 바탕으로 3~5단어의 짧은 제목을 생성합니다."""

    prompt = (
        "다음 질문(또는 분석 요청)을 바탕으로 대화방의 제목을 3~5단어 내외의 짧은 명사형으로 작성해.\n\n"
        f"질문: {question}\n\n"
        "오직 제목만 출력할 것."
    )

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
            return question[:20]
        try:
            return call_gemini(api_key, settings.gemini_model, "", prompt).strip().replace('"', "").replace("'", "")[:40]
        except Exception:
            return question[:20]

    api_key = openai_api_key or settings.openai_api_key
    if not api_key:
        return question[:20]

    try:
        client = make_openai_client(api_key, OPENAI_TITLE_TIMEOUT_SECONDS)
        model = settings.openai_model
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=20,
        )
        return response.choices[0].message.content.strip().replace('"', "").replace("'", "")
    except Exception:
        return question[:20]
