# 초보자 안내: 문서 미리보기 PDF를 만드는 API 라우터입니다.
# 프론트엔드가 업로드 파일을 보내면 백엔드가 PDF bytes로 변환해 브라우저 미리보기 창에 띄웁니다.

from fastapi import APIRouter, File, Response, UploadFile

from app.core.uploads import read_upload_content
from app.services.document_preview import create_document_preview_pdf


router = APIRouter(prefix="/api/document-previews", tags=["document-previews"])


@router.post("/pdf")
async def create_pdf_preview(file: UploadFile = File(...)):
    filename = file.filename or "document"
    content = await read_upload_content(file)
    pdf_bytes = create_document_preview_pdf(filename, content)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="preview.pdf"'},
    )
