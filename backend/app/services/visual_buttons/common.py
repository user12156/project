# 서비스: 시각화 생성 공통 유틸 함수로 텍스트 정리와 메타데이터 생성을 지원합니다.
# 초보자 안내: 시각화 생성 서비스들이 함께 쓰는 공통 텍스트 정리/추출 도우미 함수 모음입니다.

import re
from collections import Counter
from datetime import datetime, timezone


def clean_line(text: str) -> str:
    text = re.sub(r"^[-\d.·\s]+", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def meaningful_lines(text: str, limit: int = 8) -> list[str]:
    lines = [clean_line(line) for line in str(text or "").splitlines()]
    return [line for line in lines if len(line) > 8][:limit]


def frequent_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z가-힣0-9]{2,}", str(text or "").lower())
    stopwords = {"분석", "문서", "내용", "결과", "기준", "업로드", "합니다", "있는", "없는"}
    counter = Counter(word for word in words if word not in stopwords)
    return [word for word, _ in counter.most_common(limit)]


def base_asset(kind: str, title: str, source_text: str) -> dict:
    return {
        "id": f"visual-{kind}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "role": "asset",
        "kind": kind,
        "title": title,
        "desc": " ".join(meaningful_lines(source_text, 2)) or "업로드 문서를 기준으로 생성한 시각화입니다.",
        "date": datetime.now(timezone.utc).isoformat(),
        "saved": False,
    }
