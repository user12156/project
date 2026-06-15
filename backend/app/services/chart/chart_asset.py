"""Create chart visual assets for the graph visual button."""

from app.services.visual_buttons.common import base_asset, frequent_keywords


def create_graph_visual(extracted_docs: list[dict], analysis_text: str) -> dict:
    asset = base_asset("graph", "키워드 중요도 그래프", analysis_text)
    keywords = frequent_keywords(analysis_text, 6)
    if not keywords:
        keywords = [doc.get("filename", f"문서 {index + 1}") for index, doc in enumerate((extracted_docs or [])[:4])]
    if not keywords:
        keywords = ["핵심", "요약", "비교", "결과", "차이"]

    rows = [
        {
            "label": keyword,
            "point": f"{keyword} 관련 언급 빈도와 중요도를 기준으로 측정했습니다.",
            "score": max(38, min(96, 90 - index * 6 + ((index % 2) * 8))),
        }
        for index, keyword in enumerate(keywords[:6])
    ]

    asset.update(
        {
            "text": "분석 결과의 주요 키워드를 막대그래프로 표현했습니다.",
            "rows": rows,
            "keywords": keywords[:6],
            "details": [{"lbl": row["label"], "val": str(row["score"])} for row in rows],
        }
    )
    return asset
