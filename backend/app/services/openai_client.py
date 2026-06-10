# 서비스: OpenAI SDK 클라이언트 설정과 사용자 친화적 오류 메시지 변환을 관리합니다.
"""OpenAI SDK client defaults and user-safe PaperMate error messages."""

OPENAI_RETRY_COUNT = 1
OPENAI_CHUNK_TIMEOUT_SECONDS = 90.0
OPENAI_REWRITE_TIMEOUT_SECONDS = 120.0
OPENAI_ANALYSIS_TIMEOUT_SECONDS = 180.0
OPENAI_TITLE_TIMEOUT_SECONDS = 30.0
OPENAI_STRUCTURED_TIMEOUT_SECONDS = 60.0


def make_openai_client(api_key: str, timeout: float):
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=timeout, max_retries=OPENAI_RETRY_COUNT)


def openai_error_message(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    error_type = exc.__class__.__name__.lower()
    raw_message = str(exc).strip()

    if "authentication" in error_type or status_code == 401:
        return "PaperMate 분석 키가 올바르지 않거나 권한이 없습니다."
    if "permission" in error_type or status_code == 403:
        return "PaperMate 분석 키에 이 모델 또는 기능을 사용할 권한이 없습니다."
    if "rate" in error_type or status_code == 429:
        return "PaperMate 분석 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
    if "timeout" in error_type:
        return "PaperMate 응답 시간이 초과되어 로컬 근거 답변으로 전환했습니다."
    if status_code and 500 <= int(status_code) < 600:
        return "PaperMate 분석 엔진이 일시적으로 응답하지 않아 로컬 근거 답변으로 전환했습니다."
    if status_code == 400:
        return "PaperMate 분석 요청 형식이 올바르지 않아 로컬 근거 답변으로 전환했습니다."
    return f"PaperMate 분석 호출 실패: {raw_message}" if raw_message else "PaperMate 분석 호출 실패"
