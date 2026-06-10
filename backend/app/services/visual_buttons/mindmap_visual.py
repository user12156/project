# 서비스: 분석 결과를 마인드맵 형태로 구조화합니다.
# 초보자 안내: 분석 내용을 중심 주제와 가지 구조의 마인드맵 데이터로 바꾸는 파일입니다.

from .common import base_asset, meaningful_lines


def create_mindmap_visual(extracted_docs: list[dict], analysis_text: str) -> dict:
    asset = base_asset("mindmap", "핵심 내용 마인드맵", analysis_text)
    branches = meaningful_lines(analysis_text, 5)
    if not branches:
        branches = ["핵심 내용", "실험 결과", "차이점", "추가 확인"]

    asset.update(
        {
            "text": "문서의 핵심 내용과 연결 주제를 마인드맵으로 정리했습니다.",
            "branches": branches[:5],
            "details": [{"lbl": f"가지 {index + 1}", "val": branch} for index, branch in enumerate(branches[:5])],
        }
    )
    return asset
