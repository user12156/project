# 초보자 안내: 분석 결과를 표, 그래프, 마인드맵, 이미지 설명 형태로 바꾸는 API 라우터입니다.

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.uploads import read_upload_content, validate_upload_count
from app.services.document_processing import extract_file_document
from app.services.fallback_analysis import build_analysis_answer
from app.services.visual_buttons.registry import VISUAL_CREATORS
from models.schemas import VisualResponse


router = APIRouter(prefix="/api/visuals", tags=["visuals"])


@router.post("/{visual_type}", response_model=VisualResponse)
async def create_visual(
    visual_type: str,
    analysis_text: str = Form(""),
    openai_api_key: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    """분석 페이지의 표/그래프/이미지/마인드맵 버튼이 호출하는 생성 API입니다."""
    creator = VISUAL_CREATORS.get(visual_type)
    if not creator:
        raise HTTPException(status_code=404, detail="지원하지 않는 시각화 유형입니다.")

    validate_upload_count(files)
    extracted_docs = []
    for upload in files:
        content = await read_upload_content(upload)
        try:
            extracted_doc = extract_file_document(upload.filename or "unknown", content)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"{upload.filename or '파일'} 분석 중 오류가 발생했습니다: {exc}") from exc

        extracted_docs.append(extracted_doc)

    source_text = analysis_text.strip()
    if not source_text and extracted_docs:
        source_text = build_analysis_answer("시각화 자료로 정리해줘", extracted_docs)["answer"]
    if not source_text:
        source_text = "업로드 문서 또는 분석 답변이 없어 기본 시각화 예시를 생성합니다."

    if visual_type == "table":
        return {
            "visual": creator(
                extracted_docs,
                source_text,
                openai_api_key=openai_api_key.strip() or None,
            )
        }

    return {"visual": creator(extracted_docs, source_text)}
