# 초보자 안내: 문서 파일 업로드와 분석 요청을 처리하는 API 라우터입니다.

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.uploads import read_upload_content, validate_upload_count
from ..services.document_analysis import build_analysis_answer, extract_file_text
from ..services.llm_analysis import analyze_with_llm
from models.schemas import AnalysisResponse


# /api/analysis 아래의 분석 API를 모아두는 FastAPI Router입니다.
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# 프론트엔드 Analysis.js의 analysisAPI.chat(question, files)가 호출하는 엔드포인트입니다.
# 요청 형식은 multipart/form-data입니다.
# - question: 사용자가 채팅창에 입력한 질문
# - files: 업로드한 PDF/HWPX/HWP/DOCX/이미지/TXT 파일 목록
@router.post("/chat", response_model=AnalysisResponse)
async def analyze_chat(
    question: str = Form(""),
    llm_provider: str = Form("openai"),
    openai_api_key: str = Form(""),
    google_api_key: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    analysis_text: str = Form(""),
):
    analysis_text = analysis_text.strip()
    validate_upload_count(files, required=not bool(analysis_text))

    extracted_docs = []
    for upload in files:
        # UploadFile은 FastAPI가 제공하는 업로드 파일 객체입니다.
        # await upload.read()로 파일 내용을 bytes 형태로 읽습니다.
        content = await read_upload_content(upload)

        # 파일 확장자에 따라 PDF/HWPX/DOCX/이미지/TXT 추출기가 선택됩니다.
        # 결과 text는 이후 기본 분석과 LLM 분석의 공통 입력이 됩니다.
        try:
            text, file_format = extract_file_text(upload.filename or "unknown", content)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"{upload.filename or '파일'} 분석 중 오류가 발생했습니다: {exc}") from exc

        extracted_docs.append(
            {
                "filename": upload.filename or "unknown",
                "format": file_format,
                "text": text,
            }
        )

    if analysis_text and not extracted_docs:
        extracted_docs.append(
            {
                "filename": "이전 분석 내용",
                "format": "analysis_text",
                "text": analysis_text,
            }
        )

    # fallback_answer는 OpenAI 키가 없어도 항상 만들 수 있는 기본 분석입니다.
    # 키워드와 중요 문장 후보를 Python 로직으로 추출합니다.
    fallback_answer = build_analysis_answer(question, extracted_docs)
    selected_provider = llm_provider.strip() or "openai"
    if selected_provider.lower() == "google":
        request_key = google_api_key.strip()
        env_key = settings.google_api_key or settings.gemini_api_key
    else:
        request_key = openai_api_key.strip()
        env_key = settings.openai_api_key
    llm_key_source = "request" if request_key else "env" if env_key else "none"
    llm_key_received = llm_key_source != "none"

    # analyze_with_llm은 선택한 제공자(OpenAI/Gemini)의 키가 있을 때만 외부 API를 호출합니다.
    # 키가 없거나 호출 실패 시 실패 이유를 llm_error에 담고, fallback_answer만 프론트에 보냅니다.
    llm_answer = analyze_with_llm(
        question,
        extracted_docs,
        provider=selected_provider,
        openai_api_key=openai_api_key.strip() or None,
        google_api_key=google_api_key.strip() or None,
        analysis_text=analysis_text,
    )
    if not llm_answer.get("llm_used"):
        return {
            **fallback_answer,
            "llm_used": False,
            "provider": llm_answer.get("provider"),
            "model": llm_answer.get("model"),
            "llm_error": llm_answer.get("llm_error"),
            "llm_key_received": llm_key_received,
            "llm_key_source": llm_key_source,
            "suggested_questions": [],
        }

    # LLM 답변이 성공하면 fallback의 documents/keywords 같은 구조 정보와
    # LLM의 자연어 answer/model 정보를 합쳐서 반환합니다.
    return {
        **fallback_answer,
        **llm_answer,
        "llm_key_received": llm_key_received,
        "llm_key_source": llm_key_source,
    }
