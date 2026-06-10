# 서비스: PyMuPDF 기반 PDF 텍스트 추출을 처리합니다.
"""PDF text extraction with PyMuPDF."""


def extract_pdf_units(content: bytes) -> list[dict]:
    try:
        import fitz
    except ModuleNotFoundError:
        return [
            {
                "page_number": 1,
                "source_label": "Page 1",
                "text": "PDF 분석을 위해 PyMuPDF 패키지가 필요합니다. requirements.txt 설치 후 다시 시도해주세요.",
            }
        ]

    with fitz.open(stream=content, filetype="pdf") as document:
        units: list[dict] = []
        for page_index, page in enumerate(document, start=1):
            page_text = page.get_text("text")
            if isinstance(page_text, str):
                text = page_text
            elif page_text is not None:
                text = str(page_text)
            else:
                text = ""
            if text.strip():
                units.append({"page_number": page_index, "source_label": f"Page {page_index}", "text": text})
        return units


def extract_pdf(content: bytes) -> str:
    return "\n".join(unit["text"] for unit in extract_pdf_units(content))

