# 서비스: 파일 형식별 문서 추출을 호출하고 공통 문서 구조로 통합합니다.
"""Thin document extraction orchestrator.

The heavy format-specific code lives in services/extractors. This module keeps
the public extraction API stable for routers and other services.
"""

from pathlib import Path

from app.services.analysis.answer_builder import preprocess_korean_text
from app.services.extractors.hwp_extractor import extract_hwp, parse_document
from app.services.extractors.image_extractor import (
    IMAGE_EXTENSIONS,
    extract_uploaded_image_assets,
    inspect_image,
)
from app.services.extractors.pdf_extractor import extract_pdf, extract_pdf_units
from app.services.extractors.text_extractor import TEXT_EXTENSIONS, extract_docx, extract_text
from app.services.visual_buttons.image.extraction import (
    extract_pdf_visual_assets,
    extract_zipped_visual_assets,
    visual_assets_to_source_units,
)


def _parsed_text_or_message(parsed: dict, empty_message: str) -> str:
    text = preprocess_korean_text(parsed.get("text", ""), fix_spacing=False)
    return text or empty_message


def _is_hwp_extraction_failure(text: str) -> bool:
    return any(
        message in str(text or "")
        for message in (
            "HWP 바이너리 문서는 olefile 패키지 또는 HWPX 변환이 필요합니다.",
            "HWP 파일 구조를 열 수 없습니다.",
            "HWP 본문 텍스트를 찾지 못했습니다.",
            "HWP 본문 추출 중 오류가 발생했습니다.",
        )
    )


def _finalize_extracted_text(text: str) -> str:
    return preprocess_korean_text(text, fix_spacing=False)


def _source_label(file_format: str, number: int | None = None) -> str:
    if file_format == "PDF" and number:
        return f"Page {number}"
    if file_format in {"HWP", "HWPX/OWPML", "DOCX"} and number:
        return f"Section {number}"
    return file_format or "document"


def _finalize_source_units(units: list[dict], file_format: str) -> list[dict]:
    finalized = []
    for index, unit in enumerate(units, start=1):
        text = _finalize_extracted_text(unit.get("text", ""))
        if not text.strip():
            continue
        page_number = unit.get("page_number")
        section_index = unit.get("section_index")
        number = page_number or section_index or index
        finalized.append(
            {
                **unit,
                "text": text,
                "source_label": unit.get("source_label") or _source_label(file_format, number),
            }
        )
    return finalized


def _document_from_units(
    filename: str,
    file_format: str,
    units: list[dict],
    visual_assets: list[dict] | None = None,
) -> dict:
    visual_assets = visual_assets or []
    if visual_assets:
        units = [*units, *visual_assets_to_source_units(visual_assets)]
    finalized_units = _finalize_source_units(units, file_format)
    text = "\n\n".join(
        f"[{unit['source_label']}]\n{unit['text']}" for unit in finalized_units
    )
    return {
        "filename": filename,
        "format": file_format,
        "text": text,
        "source_units": finalized_units,
        "visual_assets": visual_assets,
    }


def extract_file_document(filename: str, content: bytes) -> dict:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return _document_from_units(
            filename,
            "PDF",
            extract_pdf_units(content),
            visual_assets=extract_pdf_visual_assets(content, filename),
        )

    if extension == ".hwpx":
        parsed = parse_document(content, filename)
        text = _parsed_text_or_message(
            parsed,
            "HWPX/OWPML 내부에서 추출 가능한 본문 텍스트를 찾지 못했습니다.",
        )
        return _document_from_units(
            filename,
            "HWPX/OWPML",
            [{"section_index": 1, "text": text}],
            visual_assets=extract_zipped_visual_assets(content, filename),
        )

    if extension == ".docx":
        return _document_from_units(
            filename,
            "DOCX",
            [{"section_index": 1, "text": extract_docx(content)}],
            visual_assets=extract_zipped_visual_assets(content, filename),
        )

    if extension in TEXT_EXTENSIONS:
        return _document_from_units(filename, "TEXT", [{"section_index": 1, "text": extract_text(content)}])

    if extension in IMAGE_EXTENSIONS:
        return _document_from_units(
            filename,
            "IMAGE",
            [{"section_index": 1, "text": inspect_image(content)}],
            visual_assets=extract_uploaded_image_assets(filename, content),
        )

    if extension == ".hwp":
        text = extract_hwp(content)
        if text and not _is_hwp_extraction_failure(text):
            return _document_from_units(filename, "HWP", [{"section_index": 1, "text": text}])

        parsed = parse_document(content, filename)
        parsed_text = _parsed_text_or_message(parsed, "")
        if parsed_text:
            text = parsed_text
        return _document_from_units(filename, "HWP", [{"section_index": 1, "text": text}])

    return _document_from_units(filename, "UNKNOWN", [{"section_index": 1, "text": "지원하지 않는 파일 형식입니다."}])


def extract_file_text(filename: str, content: bytes) -> tuple[str, str]:
    document = extract_file_document(filename, content)
    return document.get("text", ""), document.get("format", "UNKNOWN")


def _legacy_extract_file_text(filename: str, content: bytes) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return _finalize_extracted_text(extract_pdf(content)), "PDF"
    if extension == ".hwpx":
        parsed = parse_document(content, filename)
        text = _parsed_text_or_message(
            parsed,
            "HWPX/OWPML 내부에서 추출 가능한 본문 텍스트를 찾지 못했습니다.",
        )
        return _finalize_extracted_text(text), "HWPX/OWPML"
    if extension == ".docx":
        return _finalize_extracted_text(extract_docx(content)), "DOCX"
    if extension in TEXT_EXTENSIONS:
        return _finalize_extracted_text(extract_text(content)), "TEXT"
    if extension in IMAGE_EXTENSIONS:
        return _finalize_extracted_text(inspect_image(content)), "IMAGE"
    if extension == ".hwp":
        text = extract_hwp(content)
        if text and not _is_hwp_extraction_failure(text):
            return _finalize_extracted_text(text), "HWP"

        parsed = parse_document(content, filename)
        parsed_text = _parsed_text_or_message(parsed, "")
        return _finalize_extracted_text(parsed_text or text), "HWP"
    return "지원하지 않는 파일 형식입니다.", "UNKNOWN"
