# 서비스: 문서 분석을 표 형태로 정리하는 시각화 생성 로직입니다.
# 초보자 안내: 분석 내용을 행과 열이 있는 표 데이터로 바꾸는 파일입니다.

import json
import re
from pathlib import Path

from app.core.config import settings
from app.services.openai_client import OPENAI_STRUCTURED_TIMEOUT_SECONDS, make_openai_client

from .common import base_asset, clean_line, meaningful_lines


def _clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n-·")


def _logical_lines(text: str) -> list[str]:
    raw_lines = str(text or "").splitlines()
    if len(raw_lines) <= 2:
        heading_pattern = (
            r"초록|초론|요약|abstract|서론|introduction|본론|연구방법|연구 방법|"
            r"방법|method|methods|결과|results|논의|discussion|결론|conclusion"
        )
        text = re.sub(
            rf"\s+({heading_pattern})\s+",
            r"\n\1\n",
            str(text or ""),
            flags=re.IGNORECASE,
        )
        raw_lines = text.splitlines()
    return [_clean_title(line) for line in raw_lines]


def _filename_title(filename: str) -> str:
    stem = Path(str(filename or "")).stem
    return _clean_title(stem) or "문서 분석 표"


def _looks_like_person_or_meta(line: str) -> bool:
    value = _clean_title(line)
    lower = value.lower()
    if "@" in value or re.search(r"\b(?:대학교|학과|전공|학회|저널|vol\.|no\.|issn|keyword|접수번호)\b", lower):
        return True
    if re.search(r"(김|이|박|최|정|강|조|윤|장|임|한|오|서|신|권|황|안|송|류|홍|전)[가-힣]{1,3}\s*[,·]\s*", value):
        return True
    if re.fullmatch(r"[A-Za-z가-힣\s,·ㆍ]{2,40}", value) and len(value.split()) <= 6 and re.search(r"[,·ㆍ]", value):
        return True
    return False


def _title_candidate_score(line: str, index: int) -> int:
    title = _clean_title(line)
    if not title or _is_noise_line(title) or _looks_like_person_or_meta(title):
        return -999
    if re.search(r"\.(?:pdf|hwp|hwpx|docx|txt)$", title, flags=re.IGNORECASE):
        return -999
    if title.startswith(("-", "–", "—")):
        return -60
    if len(title) < 5 or len(title) > 95:
        return -80
    if re.match(r"^(?:\d+(?:\.\d+)*|[IVXLCDM]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)[.\s]+", title, flags=re.IGNORECASE):
        return -40

    score = 100
    score -= index * 5
    if 12 <= len(title) <= 55:
        score += 20
    if re.search(r"연구|분석|동향|방안|방법|설계|실험|조사|비교|고찰|개선|평가|전략", title):
        score += 22
    if re.search(r"[가-힣]", title):
        score += 12
    if re.search(r"[.!?。]$", title):
        score -= 35
    if re.search(r"^research\s+for|^a\s+study\s+on|^focused\s+on", title, flags=re.IGNORECASE):
        score -= 15
    if re.search(r"요약|abstract|초록|서론|introduction|결론|conclusion|keyword|중요|핵심", title, flags=re.IGNORECASE):
        score -= 45
    return score


def _document_title(extracted_docs: list[dict], fallback: str = "문서 분석 표") -> str:
    filename_fallback = fallback
    for doc in extracted_docs or []:
        filename_fallback = _filename_title(doc.get("filename") or filename_fallback)
        lines = _logical_lines(doc.get("text") or "")
        candidates = []
        for index, line in enumerate(lines[:30]):
            score = _title_candidate_score(line, index)
            if score > 0:
                candidates.append((score, index, line))
        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[1]))
            return candidates[0][2]
    return filename_fallback


def _object_particle(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return "을"
    last = stripped[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return "을" if (code - 0xAC00) % 28 else "를"
    return "을"


def _is_noise_line(line: str) -> bool:
    value = clean_line(line)
    if not value:
        return True
    if re.fullmatch(r"\[(?:page|section)\s*\d+\]", value, flags=re.IGNORECASE):
        return True
    return any(
        pattern in value
        for pattern in [
            "질문하신 내용은",
            "문서에서 근거가 되는 부분",
            "LLM 없이 로컬 기본 분석",
            "분석 기준:",
            "[핵심 내용 요약]",
            "[중요 문장 발췌]",
            "[중요 키워드]",
            "[실험 결과/수치 후보]",
            "[문서별 핵심 근거]",
            "분석 엔진:",
            "API 키:",
            "선택 Provider:",
            "LLM 호출 실패:",
            "발췌할 문장을 찾지 못했습니다",
        ]
    )


def _extract_summary_section(analysis_text: str, limit: int) -> list[str]:
    text = str(analysis_text or "")
    match = re.search(r"\[핵심 내용 요약\](.*?)(?:\n\s*\[[^\]]+\]|\Z)", text, flags=re.S)
    if not match:
        return []

    lines = []
    for raw_line in match.group(1).splitlines():
        line = clean_line(raw_line)
        line = re.sub(r"^\d+\s*[.)]\s*", "", line).strip()
        if line and not _is_noise_line(line):
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _heading_info(line: str) -> tuple[str, str] | None:
    value = _clean_title(line)
    if not value or _is_noise_line(value):
        return None

    decimal_match = re.match(r"^(\d+\.\d+(?:\.\d+)*)\s+(.{2,80})$", value)
    if decimal_match:
        return "sub", f"{decimal_match.group(1)} {decimal_match.group(2).strip()}"

    major_match = re.match(r"^(\d+)\.\s+(.{2,80})$", value)
    if major_match:
        return "major", f"{major_match.group(1)}. {major_match.group(2).strip()}"

    roman_match = re.match(r"^([IVXLCDM]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)[.\s]+\s*(.{2,80})$", value, flags=re.IGNORECASE)
    if roman_match:
        return "major", f"{roman_match.group(1)}. {roman_match.group(2).strip()}"

    normalized = re.sub(r"^\[[^\]]+\]\s*", "", value).strip()
    canonical_headings = {
        "요약",
        "abstract",
        "초록",
        "초론",
        "서론",
        "introduction",
        "본론",
        "연구방법",
        "연구 방법",
        "방법",
        "method",
        "methods",
        "결과",
        "results",
        "논의",
        "discussion",
        "결론",
        "conclusion",
        "참고문헌",
        "references",
    }
    if normalized.lower() in canonical_headings:
        label_map = {
            "abstract": "영문 요약",
            "초론": "초록",
            "introduction": "서론",
            "method": "연구방법",
            "methods": "연구방법",
            "results": "결과",
            "discussion": "논의",
            "conclusion": "결론",
            "references": "참고문헌",
        }
        return "major", label_map.get(normalized.lower(), normalized)

    if len(value) <= 32 and not re.search(r"[.!?。]$", value) and re.search(r"결론|서론|연구|분석|방법|결과|논의|해결|문제", value):
        return "major", value
    return None


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []
    normalized = re.sub(r"([.!?。])\s+", r"\1\n", normalized)
    normalized = re.sub(r"((?:다|요|함|음|됨|임)\.)\s+", r"\1\n", normalized)
    parts = normalized.splitlines()
    return [clean_line(part) for part in parts if len(clean_line(part)) > 8]


def _summarize_section(text: str, max_chars: int = 190) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return clean_line(text)[:max_chars]

    def sentence_score(sentence: str) -> int:
        score = 0
        score += min(12, len(re.findall(r"\d+(?:\.\d+)?", sentence)) * 3)
        score += 7 if re.search(r"핵심|중요|결과|문제|해결|분석|비교|목적|결론|제안", sentence) else 0
        score += min(8, len(sentence) // 35)
        return score

    selected = sorted(sentences, key=sentence_score, reverse=True)[:2]
    ordered = [sentence for sentence in sentences if sentence in selected]
    summary = " ".join(ordered)
    if len(summary) > max_chars:
        return summary[: max_chars - 1].rstrip() + "…"
    return summary


def _document_body_start(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        heading = _heading_info(line)
        if heading:
            return index
    for index, line in enumerate(lines):
        if len(line) > 40 and re.search(r"[.!?。]|다\.|이다\.|한다\.", line):
            return max(0, index - 1)
    return 1 if len(lines) > 1 else 0


def _infer_section_title(text: str, index: int) -> str:
    joined = str(text or "")
    lower = joined.lower()
    if re.search(r"요약|abstract|초록", lower):
        return "요약"
    if re.search(r"목적|배경|문제의식|기존|현재|도입|시작|발전", joined):
        return "서론"
    if re.search(r"유형|분류|특징|분석|비교|방법|설계|요소|구조", joined):
        return "본론"
    if re.search(r"문제점|한계|해결|개선|방안|제안", joined):
        return "쟁점 및 해결방안"
    if re.search(r"결론|정리|시사점|향후|필요하다|제시하였다", joined):
        return "결론"
    return f"핵심 내용 {index + 1}"


def _chunk_without_headings(lines: list[str], limit: int = 6) -> list[dict]:
    content_lines = [line for line in lines[_document_body_start(lines):] if not _is_noise_line(line)]
    paragraphs = [line for line in content_lines if len(line) > 18 and not _heading_info(line)]
    if not paragraphs:
        return []

    target_count = min(limit, max(3, len(paragraphs) // 2 or 1))
    chunk_size = max(1, (len(paragraphs) + target_count - 1) // target_count)
    sections = []
    used_titles: set[str] = set()
    for index in range(0, len(paragraphs), chunk_size):
        chunk = paragraphs[index:index + chunk_size]
        if not chunk:
            continue
        text = " ".join(chunk)
        title = _infer_section_title(text, len(sections))
        if title in used_titles:
            title = f"{title} {len(used_titles) + 1}"
        used_titles.add(title)
        summary = _summarize_section(text)
        if summary:
            sections.append({"title": title, "content": summary})
        if len(sections) >= limit:
            break
    return sections


def _extract_structured_sections(extracted_docs: list[dict], limit: int = 8) -> list[dict]:
    sections: list[dict] = []

    for doc in extracted_docs or []:
        lines = _logical_lines(doc.get("text") or "")
        lines = [line for line in lines if line and not _is_noise_line(line)]
        if not lines:
            continue

        current_major = ""
        current_sub = ""
        buffer: list[str] = []

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            if not current_major and not current_sub:
                buffer = []
                return
            heading = current_major
            if current_sub:
                heading = f"{current_major} > {current_sub}" if current_major else current_sub
            summary = _summarize_section(" ".join(buffer))
            if summary:
                sections.append({"title": heading or "문서 내용", "content": summary})
            buffer = []

        body_start = _document_body_start(lines)
        for line in lines[body_start:]:
            heading = _heading_info(line)
            if heading:
                flush()
                level, title = heading
                if level == "major":
                    current_major = title
                    current_sub = ""
                else:
                    current_sub = title
                continue
            buffer.append(line)

        flush()
        if len(sections) <= 1:
            sections = _chunk_without_headings(lines, limit)
        if len(sections) >= limit:
            break

    return sections[:limit]


def _source_lines(extracted_docs: list[dict], analysis_text: str, limit: int = 6) -> list[str]:
    lines = _extract_summary_section(analysis_text, limit)
    if lines:
        return lines[:limit]

    lines = [line for line in meaningful_lines(analysis_text, limit * 2) if not _is_noise_line(line)]
    if lines:
        return lines[:limit]

    doc_lines: list[str] = []
    for doc in extracted_docs or []:
        doc_lines.extend(meaningful_lines(doc.get("text", ""), limit))
        if len(doc_lines) >= limit:
            break
    return doc_lines[:limit]


def _section_title(line: str, index: int) -> str:
    compact = clean_line(line)
    bracket_match = re.match(r"^\[([^\]]{2,24})\]", compact)
    if bracket_match:
        return bracket_match.group(1)

    heading_match = re.match(r"^(.{2,24}?)(?:[:：]| - | – )", compact)
    if heading_match:
        return heading_match.group(1).strip()

    words = re.findall(r"[A-Za-z가-힣0-9]{2,}", compact)
    return " ".join(words[:3]) if words else f"목차 {index + 1}"


def _importance_score(line: str, index: int) -> int:
    number_bonus = min(10, len(re.findall(r"\d+(?:\.\d+)?", line)) * 3)
    keyword_bonus = 8 if re.search(r"핵심|중요|결과|비교|수치|근거|요약|결론", line) else 0
    length_bonus = min(10, max(0, len(line) - 40) // 18)
    return max(55, min(98, 92 - index * 4 + number_bonus + keyword_bonus + length_bonus))


def _accuracy_percent(line: str, extracted_docs: list[dict], index: int) -> int:
    has_docs = bool(extracted_docs)
    has_numbers = bool(re.search(r"\d+(?:\.\d+)?", line))
    base = 82 if has_docs else 70
    return max(62, min(99, base + (7 if has_numbers else 0) - index * 2))


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _coerce_percent(value, default: int) -> int:
    try:
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            value = match.group(0) if match else default
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _normalize_gpt_rows(payload: dict) -> list[dict]:
    rows = payload.get("data") or payload.get("rows") or []
    if not isinstance(rows, list):
        return []

    normalized = []
    for index, row in enumerate(rows[:8]):
        if not isinstance(row, dict):
            continue
        title = clean_line(row.get("toc") or row.get("title") or row.get("제목") or row.get("목차") or "")
        content = clean_line(
            row.get("content")
            or row.get("summary")
            or row.get("중요내용")
            or row.get("목차내용")
            or row.get("내용")
            or ""
        )
        if not title or not content:
            continue
        normalized.append(
            {
                "toc": title[:60],
                "content": content[:260],
                "importance": _coerce_percent(row.get("importance") or row.get("중요도") or row.get("score"), 92 - index * 4),
                "accuracy": _coerce_percent(row.get("accuracy") or row.get("정확도"), 88 - index * 2),
            }
        )
    return normalized


def _gpt_table_from_analysis(
    extracted_docs: list[dict],
    analysis_text: str,
    *,
    openai_api_key: str | None = None,
) -> dict | None:
    api_key = openai_api_key or settings.openai_api_key
    if not api_key or not analysis_text.strip():
        return None

    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        return None

    table_title = _document_title(extracted_docs)
    document_context = "\n\n".join(
        f"[{doc.get('filename') or '문서'}]\n{str(doc.get('text') or '')[:9000]}"
        for doc in extracted_docs or []
        if str(doc.get("text") or "").strip()
    )
    source_block = document_context or analysis_text
    source_label = "문서 원문" if document_context else "분석 결과"

    prompt = f"""
아래 {source_label}을 기준으로 문서 흐름 표를 만드세요.

요구사항:
- 문서 전체를 한눈에 볼 수 있도록 4~8행으로 압축
- 제목 열에는 문서 흐름에 맞는 항목명(예: 초록/요약, 서론, 본론, 결과, 결론 등)을 사용
- 중요내용 열에는 해당 항목에서 실제로 중요한 근거, 주장, 수치, 결론을 짧고 구체적으로 요약
- 중요도는 0~100 점수, 정확도는 분석 결과에 근거한 신뢰도 0~100
- 아래 내용에 없는 내용은 만들지 말 것
- 반드시 JSON 객체만 출력

JSON 형식:
{{
  "title": "{table_title}",
  "text": "{table_title}{_object_particle(table_title)} 표로 정리하였습니다.",
  "data": [
    {{"toc": "요약", "content": "핵심 요약", "importance": 98, "accuracy": 90}}
  ]
}}

[{source_label}]
{source_block[:12000]}
"""
    try:
        client = make_openai_client(api_key, OPENAI_STRUCTURED_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "너는 분석 결과를 정확한 한국어 표 데이터로 바꾸는 도우미다. JSON 외 텍스트를 출력하지 않는다.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
    except Exception:
        return None

    payload = _extract_json_object(content)
    if not payload:
        return None

    data = _normalize_gpt_rows(payload)
    if not data:
        return None
    return {
        "title": _clean_title(payload.get("title")) or table_title,
        "text": clean_line(payload.get("text")) or f"{table_title}{_object_particle(table_title)} 표로 정리하였습니다.",
        "data": data,
        "llm_used": True,
        "provider": "openai",
        "model": settings.openai_model,
    }


def create_table_visual(
    extracted_docs: list[dict],
    analysis_text: str,
    *,
    openai_api_key: str | None = None,
) -> dict:
    table_title = _document_title(extracted_docs)
    gpt_table = _gpt_table_from_analysis(extracted_docs, analysis_text, openai_api_key=openai_api_key)
    if gpt_table:
        table_title = gpt_table["title"]
    asset = base_asset("table", table_title, analysis_text)

    data = gpt_table["data"] if gpt_table else []
    if not data:
        structured_sections = _extract_structured_sections(extracted_docs, 8)
        if structured_sections:
            for index, section in enumerate(structured_sections):
                content = section["content"]
                data.append(
                    {
                        "toc": section["title"],
                        "content": content,
                        "importance": _importance_score(content, index),
                        "accuracy": _accuracy_percent(content, extracted_docs, index),
                    }
                )
        else:
            analysis_lines = _source_lines(extracted_docs, analysis_text, 8) if analysis_text.strip() else []
            if analysis_lines:
                for index, line in enumerate(analysis_lines[:8]):
                    data.append(
                        {
                            "toc": _section_title(line, index),
                            "content": clean_line(line),
                            "importance": _importance_score(line, index),
                            "accuracy": _accuracy_percent(line, extracted_docs, index),
                        }
                    )
            else:
                lines = _source_lines(extracted_docs, analysis_text, 6)
                if not lines:
                    lines = ["업로드 문서 또는 분석 답변이 없어 기본 목차 후보를 생성했습니다."]
                for index, line in enumerate(lines[:6]):
                    data.append(
                        {
                            "toc": _section_title(line, index),
                            "content": clean_line(line),
                            "importance": _importance_score(line, index),
                            "accuracy": _accuracy_percent(line, extracted_docs, index),
                        }
                    )

    columns = [
        {"key": "toc", "label": "제목"},
        {"key": "content", "label": "중요내용"},
        {"key": "importance", "label": "중요도(점수)"},
        {"key": "accuracy", "label": "정확도(%)"},
    ]

    asset.update(
        {
            "type": "table",
            "desc": f"{table_title}의 핵심 내용 요약을 표로 정리했습니다.",
            "text": gpt_table["text"] if gpt_table else f"{table_title}{_object_particle(table_title)} 표로 정리하였습니다.",
            "columns": columns,
            "data": data,
            "rows": data,
            "llm_used": bool(gpt_table),
            "provider": gpt_table.get("provider") if gpt_table else None,
            "model": gpt_table.get("model") if gpt_table else None,
            "layout": {
                "aspectRatio": "10 / 6",
                "variant": "wide",
            },
            "theme": {
                "headerBackground": "#0f766e",
                "headerTextColor": "#ffffff",
                "cellBackground": "#ffffff",
                "cellTextColor": "#334155",
                "borderColor": "#cbd5e1",
            },
            "details": [{"lbl": row["toc"], "val": row["content"]} for row in data],
        }
    )
    return asset
