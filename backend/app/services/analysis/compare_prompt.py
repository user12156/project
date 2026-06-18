"""Prompt templates for optional LLM-backed document comparison."""

COMPARE_EXTRACTION_PROMPT = """다음 문서에서 아래 항목만 추출하라.

1. 연구 주제
2. 연구 목적
3. 사용 데이터
4. 분석 방법
5. 주요 결과
6. 한계점

반드시 JSON 객체로만 답변하라.
{
  "topic": "",
  "purpose": "",
  "data_source": "",
  "methodology": "",
  "findings": "",
  "limitations": ""
}
"""


COMPARE_SYNTHESIS_PROMPT = """위 비교 결과를 바탕으로 아래 내용을 한국어로 정리하라.

1. 공통점 3개
2. 차이점 3개
3. 어떤 문서가 어떤 상황에 적합한지
"""
