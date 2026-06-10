# 초보자 안내: 문서 파일 업로드와 분석 요청을 처리하는 API 라우터입니다.

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.uploads import read_upload_content, validate_upload_count
from ..services.analysis_pipeline import run_analysis_pipeline
from ..services.document_processing import extract_file_document
from models.schemas import AnalysisResponse


# /api/analysis 아래의 분석 API를 모아두는 FastAPI Router입니다.
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

DOCUMENT_SESSION_CACHE: dict[str, list[dict]] = {}


# 프론트엔드 Analysis.js의 analysisAPI.chat(question, files)가 호출하는 엔드포인트입니다.
# 요청 형식은 multipart/form-data입니다.
# - question: 사용자가 채팅창에 입력한 질문
# - files: 업로드한 PDF/HWPX/HWP/DOCX/이미지/TXT 파일 목록
@router.post("/chat", response_model=AnalysisResponse)
async def analyze_chat(
    question: str = Form(""),
    conversation_id: str = Form(""),
    llm_provider: str = Form("auto"),
    openai_api_key: str = Form(""),
    google_api_key: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    analysis_text: str = Form(""),
):
    analysis_text = analysis_text.strip()
    session_key = conversation_id.strip()
    if files:
        validate_upload_count(files)
        extracted_docs = []
    elif session_key and session_key in DOCUMENT_SESSION_CACHE:
        extracted_docs = DOCUMENT_SESSION_CACHE[session_key]
    elif analysis_text:
        extracted_docs = []
    else:
        extracted_docs = []

    for upload in files:
        # UploadFile은 FastAPI가 제공하는 업로드 파일 객체입니다.
        # await upload.read()로 파일 내용을 bytes 형태로 읽습니다.
        content = await read_upload_content(upload)

        # 파일 확장자에 따라 PDF/HWPX/DOCX/이미지/TXT 추출기가 선택됩니다.
        # 결과 text는 이후 기본 분석과 LLM 분석의 공통 입력이 됩니다.
        try:
            extracted_doc = extract_file_document(upload.filename or "unknown", content)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"{upload.filename or '파일'} 분석 중 오류가 발생했습니다: {exc}") from exc

        extracted_docs.append(extracted_doc)

    # fallback_answer는 OpenAI 키가 없어도 항상 만들 수 있는 기본 분석입니다.
    # 키워드와 중요 문장 후보를 Python 로직으로 추출합니다.
    if files and session_key and extracted_docs:
        DOCUMENT_SESSION_CACHE[session_key] = extracted_docs

    if analysis_text and not extracted_docs:
        extracted_docs.append(
            {
                "filename": "이전 분석 내용",
                "format": "analysis_text",
                "text": analysis_text,
            }
        )

    return run_analysis_pipeline(
        question=question,
        extracted_docs=extracted_docs,
        uploaded_filenames=[upload.filename or "파일" for upload in files],
        llm_provider=llm_provider,
        openai_api_key=openai_api_key.strip() or None,
        google_api_key=google_api_key.strip() or None,
        analysis_text=analysis_text,
    )

@router.post("/title")
async def generate_title(
    question: str = Form(""),
    llm_provider: str = Form("auto"),
    openai_api_key: str = Form(""),
    google_api_key: str = Form(""),
    analysis_text: str = Form("")
):
    selected_provider = (llm_provider or "auto").strip().lower()
    if selected_provider not in {"auto", "gemini", "google", "openai"}:
        selected_provider = "auto"
    
    from ..services.llm.title_generator import generate_chat_title
    
    title = generate_chat_title(
        question,
        provider=selected_provider,
        openai_api_key=openai_api_key.strip() or None,
        google_api_key=google_api_key.strip() or None,
        analysis_text=analysis_text.strip()
    )
    
    return {"title": title}
