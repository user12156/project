"""Extract chart JSON from LLM responses."""

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("빈 응답입니다.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("JSON 객체를 찾을 수 없습니다.")

    return json.loads(cleaned[start : end + 1])
