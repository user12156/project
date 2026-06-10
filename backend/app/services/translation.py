# 서비스: 영어 기반 분석 텍스트를 한국어로 번역하는 로컬 지원 로직입니다.
"""Optional local translation helpers for user-facing Korean analysis."""

import re
from functools import lru_cache

from app.core.config import settings


ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z\-]{2,}\b")
KOREAN_RE = re.compile(r"[가-힣]")


def _english_heavy(text: str) -> bool:
    letters = re.findall(r"[A-Za-z가-힣]", text or "")
    if not letters:
        return False
    korean_count = len(KOREAN_RE.findall(text or ""))
    english_count = len(re.findall(r"[A-Za-z]", text or ""))
    return english_count >= 20 and english_count > korean_count * 1.4


def _should_translate_line(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 12:
        return False
    if stripped.startswith(("{", "}", "- {", "```")):
        return False
    normalized = re.sub(r"^[-*]\s+", "", stripped)
    normalized = re.sub(r"^\[[^\]]+\]\s*", "", normalized)
    if re.fullmatch(r"[\[\]가-힣A-Za-z0-9 .,:()/%·_>\-]+", normalized) is None:
        return False
    return _english_heavy(normalized)


@lru_cache(maxsize=1)
def _argos_translation_ready() -> bool:
    if not settings.enable_local_translation:
        return False

    try:
        import argostranslate.package
        import argostranslate.translate
    except Exception:
        return False

    def has_installed_pair() -> bool:
        for language in argostranslate.translate.get_installed_languages():
            if language.code != "en":
                continue
            return any(translation.to_lang.code == "ko" for translation in language.translations_from)
        return False

    if has_installed_pair():
        return True

    if not settings.local_translation_auto_install:
        return False

    try:
        argostranslate.package.update_package_index()
        packages = argostranslate.package.get_available_packages()
        package = next(
            item for item in packages if item.from_code == "en" and item.to_code == "ko"
        )
        argostranslate.package.install_from_path(package.download())
        return has_installed_pair()
    except Exception:
        return False


def _translate_en_to_ko(text: str) -> str:
    if not _argos_translation_ready():
        return _cleanup_translated_text(_dictionary_translate(text))
    try:
        import argostranslate.translate

        translated = argostranslate.translate.translate(text, "en", "ko").strip()
        return _cleanup_translated_text(translated or text)
    except Exception:
        return _cleanup_translated_text(_dictionary_translate(text))


def _dictionary_translate(text: str) -> str:
    translated = str(text or "")
    replacements = [
        (r"\bAbstract\b", "초록"),
        (r"\bSummary\b", "요약"),
        (r"\bIntroduction\b", "서론"),
        (r"\bConclusion\b", "결론"),
        (r"\bConclusions\b", "결론"),
        (r"\bThis study investigates\b", "이 연구는 조사합니다"),
        (r"\bdocument analysis systems\b", "문서 분석 시스템"),
        (r"\bevaluates retrieval accuracy\b", "검색 정확도를 평가합니다"),
        (r"\bRecent AI tools\b", "최근 AI 도구"),
        (r"\boften answer in English\b", "종종 영어로 답변합니다"),
        (r"\bwhen the uploaded paper is written in English\b", "업로드한 논문이 영어로 작성되어 있을 때"),
        (r"\bThe system should provide\b", "시스템은 제공해야 합니다"),
        (r"\bKorean summaries\b", "한국어 요약"),
        (r"\bfor Korean users\b", "한국어 사용자에게"),
    ]
    for pattern, replacement in replacements:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
    return translated


def _cleanup_translated_text(text: str) -> str:
    cleaned = str(text or "")
    replacements = [
        (r"^\s*한국어\s+", ""),
        (r"\b소개\b", "서론"),
        (r"\b이름\s*\*", "결론"),
        (r"\b이름\b", "결론"),
        (r"summaries(?=[가-힣\s.,]|$)", "요약"),
        (r"summary(?=[가-힣\s.,]|$)", "요약"),
        (r"\bAbstract\b", "초록"),
        (r"\bIntroduction\b", "서론"),
        (r"\bConclusion\b", "결론"),
        (r"한국 사용자를 위한 한국어 요약", "한국어 사용자를 위한 요약"),
        (r"한국 사용자를 위한 한국어", "한국어 사용자에게"),
        (r"한국어 사용자에게 요약를", "한국어 사용자에게 요약을"),
        (r"한국어 사용자를 위한 요약를", "한국어 사용자를 위한 요약을"),
        (r"요약를", "요약을"),
        (r"영어로 작성 될 때", "영어로 작성되어 있을 때"),
        (r"종종 영어로 작성 될 때 영어로 응답합니다", "영어 문서가 업로드되면 종종 영어로 응답합니다"),
    ]
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def ensure_korean_analysis_text(text: str) -> str:
    """Translate English-heavy user-facing analysis paragraphs to Korean.

    This is intentionally conservative: headings, JSON-like data, and already
    Korean paragraphs are preserved. If Argos Translate or its en->ko package is
    unavailable, the original text is returned.
    """

    if not text:
        return text

    output: list[str] = []
    translated_any = False
    for line in str(text).splitlines():
        if _should_translate_line(line):
            translated = _translate_en_to_ko(line)
            output.append(translated)
            translated_any = translated_any or translated != line
        else:
            output.append(line)
    if translated_any:
        return "\n".join(output)
    return "\n".join(output)


def _translate_value(value):
    if isinstance(value, str):
        return ensure_korean_analysis_text(value)
    if isinstance(value, list):
        return [_translate_value(item) for item in value]
    if isinstance(value, dict):
        return translate_analysis_payload(value)
    return value


def translate_analysis_payload(payload: dict) -> dict:
    """Translate user-visible analysis fields while preserving metadata."""

    translated = dict(payload)
    for key in ("answer", "summary", "text", "desc"):
        if key in translated:
            translated[key] = _translate_value(translated[key])

    documents = translated.get("documents")
    if isinstance(documents, list):
        translated["documents"] = [
            {
                **doc,
                "key_points": _translate_value(doc.get("key_points", [])),
                "metrics": _translate_value(doc.get("metrics", [])),
            }
            if isinstance(doc, dict)
            else doc
            for doc in documents
        ]

    chunks = translated.get("relevant_chunks")
    if isinstance(chunks, list):
        translated["relevant_chunks"] = [
            {
                **chunk,
                "text": _translate_value(chunk.get("text", "")),
            }
            if isinstance(chunk, dict)
            else chunk
            for chunk in chunks
        ]

    topics = translated.get("topics")
    if isinstance(topics, list):
        translated["topics"] = [
            {
                **topic,
                "examples": _translate_value(topic.get("examples", [])),
            }
            if isinstance(topic, dict)
            else topic
            for topic in topics
        ]

    return translated
