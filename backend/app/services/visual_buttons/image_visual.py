# 서비스: 업로드된 이미지 기반 시각화 후보를 추출하여 표시합니다.
# 초보자 안내: 문서 안의 이미지/차트/표 후보를 추출해 화면에 보여주는 파일입니다.

from .common import base_asset, clean_line


def create_image_visual(extracted_docs: list[dict], analysis_text: str) -> dict:
    asset = base_asset("image", "이미지 파일 추출", analysis_text)
    extracted_items = []

    for doc in extracted_docs or []:
        filename = doc.get("filename", "문서")
        for visual in doc.get("visual_assets", []) or []:
            item = {
                "id": visual.get("id") or f"{filename}-{len(extracted_items) + 1}",
                "filename": filename,
                "kind": visual.get("kind") or "image",
                "name": visual.get("name") or visual.get("source_label") or f"추출 항목 {len(extracted_items) + 1}",
                "source": visual.get("source_label") or filename,
                "width": visual.get("width"),
                "height": visual.get("height"),
                "mimeType": visual.get("mime_type"),
                "ocrText": visual.get("ocr_text") or "",
                "previewText": clean_line(visual.get("text", "")),
                "dataUrl": visual.get("data_url"),
            }
            extracted_items.append(item)

    rows = [
        {
            "source": item["source"],
            "kind": item["kind"],
            "name": item["name"],
            "summary": item["ocrText"] or item["previewText"] or "이미지/차트 후보",
        }
        for item in extracted_items
    ]

    asset.update(
        {
            "type": "image",
            "text": (
                f"문서에서 이미지 후보 {len(extracted_items)}개를 추출했습니다."
                if extracted_items
                else "추출 가능한 이미지 후보를 찾지 못했습니다. 문서 내부 이미지가 너무 작거나 빈 이미지로 판단되면 제외됩니다."
            ),
            "desc": "업로드 이미지와 문서 내부 이미지 후보를 멀티모달 분석 대상으로 정리합니다. 빈 공간과 장식 이미지는 제외합니다.",
            "items": extracted_items,
            "rows": rows,
            "data": rows,
            "columns": [
                {"key": "source", "label": "출처"},
                {"key": "kind", "label": "유형"},
                {"key": "name", "label": "이름"},
                {"key": "summary", "label": "추출 내용"},
            ],
            "details": [
                {
                    "lbl": item["source"],
                    "val": item["ocrText"] or item["previewText"] or item["name"],
                }
                for item in extracted_items[:8]
            ],
        }
    )
    return asset
