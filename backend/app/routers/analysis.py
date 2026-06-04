# 초보자 안내: 문서 파일 업로드와 분석 요청을 처리하는 API 라우터입니다.

<<<<<<< HEAD
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..core.uploads import read_upload_content, validate_upload_count
from ..services.analysis_pipeline import run_analysis_pipeline
=======
import hashlib
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from ..core.uploads import read_upload_content, validate_upload_count
from ..services.analysis_pipeline import run_analysis_pipeline
from ..services.document_conversion import render_text_preview_pdf
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
from ..services.document_analysis import extract_file_document
from models.schemas import AnalysisResponse


# /api/analysis 아래의 분석 API를 모아두는 FastAPI Router입니다.
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

DOCUMENT_SESSION_CACHE: dict[str, list[dict]] = {}
<<<<<<< HEAD
=======
DOCUMENT_CACHE_LIMIT = 32
DOCUMENT_EXTRACT_CACHE: OrderedDict[str, dict] = OrderedDict()
DOCUMENT_PREVIEW_CACHE: OrderedDict[str, bytes] = OrderedDict()


def _document_cache_key(filename: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"{Path(filename).name.lower()}:{len(content)}:{digest}"


def _remember(cache: OrderedDict, key: str, value):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > DOCUMENT_CACHE_LIMIT:
        cache.popitem(last=False)
    return value


def _get_extracted_document(filename: str, content: bytes) -> dict:
    key = _document_cache_key(filename, content)
    if key in DOCUMENT_EXTRACT_CACHE:
        DOCUMENT_EXTRACT_CACHE.move_to_end(key)
        return DOCUMENT_EXTRACT_CACHE[key]
    return _remember(DOCUMENT_EXTRACT_CACHE, key, extract_file_document(filename, content))


def _get_preview_pdf(filename: str, content: bytes) -> bytes:
    key = _document_cache_key(filename, content)
    if key in DOCUMENT_PREVIEW_CACHE:
        DOCUMENT_PREVIEW_CACHE.move_to_end(key)
        return DOCUMENT_PREVIEW_CACHE[key]

    extracted_doc = _get_extracted_document(filename, content)
    pdf_bytes = render_text_preview_pdf(
        filename,
        extracted_doc.get("preview_text") or extracted_doc.get("text", ""),
        source_format=extracted_doc.get("format", "document"),
    )
    return _remember(DOCUMENT_PREVIEW_CACHE, key, pdf_bytes)


@router.post("/preview")
async def preview_document(file: UploadFile = File(...)):
    content = await read_upload_content(file)
    filename = file.filename or "document"
    try:
        pdf_bytes = _get_preview_pdf(filename, content)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"이 문서를 PDF 미리보기로 생성하지 못했습니다: {exc}",
        ) from exc

    if not pdf_bytes:
        raise HTTPException(
            status_code=422,
            detail="이 문서를 PDF 미리보기로 생성하지 못했습니다.",
        )

    output_name = Path(filename).stem + ".pdf"
    ascii_fallback_name = "preview.pdf"
    encoded_name = quote(output_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback_name}\"; filename*=UTF-8''{encoded_name}"},
    )
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10


# 프론트엔드 Analysis.js의 analysisAPI.chat(question, files)가 호출하는 엔드포인트입니다.
# 요청 형식은 multipart/form-data입니다.
# - question: 사용자가 채팅창에 입력한 질문
# - files: 업로드한 PDF/HWPX/HWP/DOCX/이미지/TXT 파일 목록
@router.post("/chat", response_model=AnalysisResponse)
async def analyze_chat(
    question: str = Form(""),
    conversation_id: str = Form(""),
    openai_api_key: str = Form(""),
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
<<<<<<< HEAD
            extracted_doc = extract_file_document(upload.filename or "unknown", content)
=======
            extracted_doc = _get_extracted_document(upload.filename or "unknown", content)
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
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
        uploaded_filenames=[upload.filename or "unknown" for upload in files],
        openai_api_key=openai_api_key.strip() or None,
        analysis_text=analysis_text,
    )

@router.post("/title")
async def generate_title(
    question: str = Form(""),
    openai_api_key: str = Form(""),
    analysis_text: str = Form("")
):
    from ..services.llm_analysis import generate_chat_title
    
    title = generate_chat_title(
        question,
        openai_api_key=openai_api_key.strip() or None,
        analysis_text=analysis_text.strip()
    )
    
    return {"title": title}
