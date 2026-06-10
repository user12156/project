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
