# 서비스: 문서 요약, 키워드/수치 후보, 응답 구성 보조 함수를 제공합니다.
# 초보자 안내: 추출된 문서 텍스트에서 질문 관련 근거, 키워드, 수치 후보를 고르는 분석 유틸입니다.

import re
from collections import Counter
from html import unescape

from app.services.embeddings.reranker import semantic_sentence_scores
from app.services.analysis.query_analyzer import (
    _compact_for_match,
    _expanded_query_terms,
    _question_wants_negative,
    _sentence_query_overlap,
    _tokenize_terms,
)

# 이 파일은 AI가 직접 동작하는 곳이 아니라, 추출된 텍스트를 답변 재료로 정리합니다.
# 선택 사용 라이브러리:
# - soynlp: 반복 문자 정규화. 설치되어 있으면 "ㅋㅋㅋㅋ", "ㅠㅠㅠㅠ" 같은 반복을 줄입니다.
# - customized_konlpy: 사용자 사전을 넣어 한국어 전문용어가 잘게 쪼개지는 문제를 줄입니다.
# - pykospacing: 띄어쓰기 보정. 설치되어 있고 텍스트가 너무 길지 않을 때만 사용합니다.

MAX_SPACING_CHARS = 3000
EXTRACTION_NOISE_PATTERN = re.compile(r"[\u0100-\u024f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
BROKEN_GLYPH_PATTERN = re.compile(r"[\u00a1-\u02af\u2500-\u25ff\u2b00-\u2bff\ufffd]+")
IMAGE_META_PATTERNS = (
    re.compile(r"원본\s*그림의\s*이름\s*:\s*CLP[^\s]+", re.IGNORECASE),
    re.compile(r"원본\s*그림의\s*크기\s*:\s*가로\s*\d+\s*pixel\s*,?\s*세로\s*\d+\s*pixel", re.IGNORECASE),
)
FORMULA_NOISE_PATTERN = re.compile(
    r"\{[^{}]{0,100}(?:TIMES|over)[^{}]{0,220}\}|(?:TIMES|over)\s*`?\s*1,?0{2,}",
    re.IGNORECASE,
)

# 공백과 HTML 엔티티를 정리해 분석하기 쉬운 한 줄 텍스트로 만듭니다.
def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = EXTRACTION_NOISE_PATTERN.sub(" ", text)
    text = BROKEN_GLYPH_PATTERN.sub(" ", text)
    for pattern in IMAGE_META_PATTERNS:
        text = pattern.sub(" ", text)
    text = re.sub(r"\{[^\n]{0,260}(?:TIMES|over)[^\n]{0,260}\}", " ", text, flags=re.IGNORECASE)
    text = FORMULA_NOISE_PATTERN.sub(" ", text)
    text = re.sub(r"(?:\{[^{}]{0,80}\}\s*){2,}", " ", text)
    text = re.sub(r"\b(?:TIMES|over)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"수식입니다", " ", text)
    # 제어문자 제거
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)

    # HWP/HWPX 추출 시 남는 주석/각주 표기 '^3', '^3)', '(^5)' 등 제거
    # 의도치 않은 캐럿 표식만 제거하도록 숫자만 붙은 캐럿 패턴을 타깃으로 함
    text = re.sub(r"\^\s*\(?\d+\)?", " ", text)
    text = re.sub(r"\(\^\s*\d+\)", " ", text)

    # 불필요한 단일 기호(중간점 등) 연속을 정리
    text = re.sub(r"[·•◦]+", " ", text)

    # HTML/공백 정리
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # 남은 빈 괄호 제거
    text = re.sub(r"\(\s*\)", "", text)
    return text


def _normalize_repeated_korean(text: str) -> str:
    """반복 문자와 감탄 표현을 정리합니다.

    soynlp가 있으면 emoticon_normalize/repeat_normalize를 사용하고,
    없으면 같은 문자가 3번 이상 반복되는 경우를 2번으로 줄입니다.
    """

    if not text:
        return ""

    try:
        from soynlp.normalizer import emoticon_normalize, repeat_normalize

        normalized = emoticon_normalize(text, num_repeats=2)
        return repeat_normalize(normalized, num_repeats=2)
    except ModuleNotFoundError:
        return re.sub(r"(.)\1{2,}", r"\1\1", text)
    except Exception:
        return re.sub(r"(.)\1{2,}", r"\1\1", text)


def _maybe_fix_spacing(text: str) -> str:
    """선택형 띄어쓰기 보정입니다.

    PyKoSpacing은 설치가 무겁고 환경 영향을 많이 받으므로 필수로 쓰지 않습니다.
    설치되어 있고 텍스트가 짧을 때만 사용해 서버 응답 지연을 피합니다.
    """

    if not text or len(text) > MAX_SPACING_CHARS:
        return text

    try:
        from pykospacing import Spacing
    except ModuleNotFoundError:
        return text

    try:
        return Spacing()(text)
    except Exception:
        return text


def preprocess_korean_text(text: str, fix_spacing: bool = False) -> str:
    """문서 분석 전 한국어 텍스트를 정제/정규화하는 공통 입구입니다."""

    cleaned = _clean_text(text)
    normalized = _normalize_repeated_korean(cleaned)
    if fix_spacing:
        normalized = _maybe_fix_spacing(normalized)
    return _clean_text(normalized)


# 문장을 대략적으로 나눕니다.
# 완전한 자연어 처리 라이브러리는 아니고, 한국어/영어 문장 구분자를 기준으로 단순 분리합니다.
def _sentences(text: str) -> list[str]:
    normalized = str(text or "")
    normalized = re.sub(r"([.!?。！？])", r"\1\n", normalized)
    normalized = re.sub(r"((?:한다|했다|된다|였다|이다|있다|없다|같다|높다|낮다|크다|작다|된다|한다|보인다|나타났다|제시한다|설명한다|분석한다|정리한다|의미한다|필요하다|중요하다|가능하다|어렵다|쉽다|다|요|음|함|임|됨))\s+", r"\1\n", normalized)
    normalized = re.sub(r"([;；])\s+", r"\1\n", normalized)
    pieces = re.split(r"\n+|(?<=[.!?。！？])\s+", normalized)
    sentences = []
    seen = set()
    for piece in pieces:
        cleaned = _clean_text(piece)
        if len(cleaned) < 14 or cleaned in seen:
            continue
        if _is_low_value_sentence(cleaned):
            continue
        seen.add(cleaned)
        sentences.append(cleaned)
    return sentences


def _is_low_value_sentence(sentence: str) -> bool:
    compact = _compact_for_match(sentence)
    if not compact:
        return True
    if len(sentence) > 900:
        return True
    if "원본그림" in compact or "수식입니다" in sentence:
        return True
    if len(re.findall(r"[가-힣A-Za-z]", sentence)) < 8:
        return True
    if len(re.findall(r"[가-힣]", sentence)) < 6 and len(re.findall(r"[A-Za-z]", sentence)) < 12:
        return True
    broken_count = len(BROKEN_GLYPH_PATTERN.findall(sentence))
    if broken_count / max(len(sentence), 1) > 0.08:
        return True
    symbol_count = len(re.findall(r"[^가-힣A-Za-z0-9\s.,%()/-]", sentence))
    if symbol_count / max(len(sentence), 1) > 0.22:
        return True
    return False


def _is_negative_sentence(sentence: str) -> bool:
    return bool(re.search(r"(아니다|않다|없다|낮다|제외|부족|어렵다|불가능)", sentence))


def _sentence_quality_score(sentence: str) -> float:
    length = len(sentence)
    if 45 <= length <= 260:
        score = 2.0
    elif 24 <= length < 45:
        score = 0.8
    elif 260 < length <= 430:
        score = 0.4
    else:
        score = -2.0

    if re.search(r"(따라서|즉|결론|핵심|중요|필요|의미|결과|보여|나타|제안|비교|차이)", sentence):
        score += 1.2
    if re.search(r"(아니다|않다|없다|낮다|제외)", sentence):
        score -= 1.4
    if re.search(r"\d+(?:\.\d+)?\s?%|\d+\.\d+", sentence):
        score += 0.9
    if len(re.findall(r"[,，]", sentence)) > 8:
        score -= 1.2
    return score


# 기본 분석에서 중요한 문장 후보를 고르기 위한 점수 함수입니다.
# 정확도, 실험, 데이터셋, 비교 같은 연구 문서 키워드가 있으면 점수를 더 줍니다.
def _keyword_score(sentence: str, query_terms: set[str] | None = None, term_weights: Counter | None = None) -> float:
    keywords = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "experiment",
        "dataset",
        "benchmark",
        "result",
        "method",
        "limitation",
        "정확도",
        "성능",
        "실험",
        "결과",
        "데이터셋",
        "방법",
        "비교",
        "한계",
        "중요",
        "제안",
    ]
    lowered = sentence.lower()
    score = sum(2.2 for keyword in keywords if keyword in lowered) + _sentence_quality_score(sentence)
    score += len(re.findall(r"\d+(?:\.\d+)?\s?%|\d+\.\d+", sentence)) * 2.5
    if query_terms:
        matched_count, coverage = _sentence_query_overlap(sentence, query_terms)
        score += matched_count * 3.2 + coverage * 6.0
    if term_weights:
        sentence_terms = set(_tokenize_terms(lowered))
        score += sum(min(term_weights.get(term, 0), 4) * 0.38 for term in sentence_terms)
    return score


# 문장 후보를 점수순으로 정렬해 상위 문장만 뽑습니다.
def _top_sentences(text: str, limit: int = 5, question: str = "") -> list[str]:
    sentences = _sentences(text)
    if not sentences:
        return []

    query_terms = _expanded_query_terms(question) if question else set()
    term_weights = Counter(_tokenize_terms(text))
    semantic_scores = semantic_sentence_scores(question, sentences)
    scored = []
    for index, sentence in enumerate(sentences):
        matched_count, coverage = _sentence_query_overlap(sentence, query_terms)
        semantic_score = semantic_scores[index] if semantic_scores else None
        score = (
            _keyword_score(sentence, query_terms, term_weights)
            + max(0, 1.6 - index * 0.04)  # 초반 문장에 약간 가중치
        )
        if semantic_score is not None:
            score += semantic_score * 18
        scored.append((index, sentence, matched_count, coverage, score, semantic_score or 0.0))

    ranked = sorted(
        scored,
        key=lambda item: (
            item[4],
            item[5],
            item[3],
            -item[0],
        ),
        reverse=True,
    )
    if question and not _question_wants_negative(question):
        non_negative = [item for item in ranked if not _is_negative_sentence(item[1])]
        if non_negative:
            ranked = non_negative
    selected = sorted(ranked[:limit], key=lambda item: item[0])
    return [sentence for _, sentence, *_ in selected]


# 자주 등장하는 단어를 뽑아 키워드 목록을 만듭니다.
# 조사/일반 단어는 stopwords로 제외합니다.
def _frequent_terms(text: str, limit: int = 10) -> list[str]:
    words = _tokenize_terms(text)
    stopwords = {
        "the",
        "and",
        "in",
        "of",
        "to",
        "on",
        "as",
        "by",
        "is",
        "it",
        "or",
        "an",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "were",
        "논문",
        "연구",
        "대한",
        "있는",
        "한다",
        "에서",
        "으로",
        "그리고",
        "하지만",
        "또한",
        "통해",
        "위해",
        "경우",
        "사용",
        "대한",
        "관련",
        "되었습니다",
        "했습니다",
        "됩니다",
        "합니다",
        "되었",
        "하였",
        "향상되었",
        "나타났",
        "보였다",
        "나왔다",
        "있었다",
        "없는",
        "있다",
    }
    counter = Counter(word for word in words if word not in stopwords and len(word) >= 2)
    return [word for word, _ in counter.most_common(limit)]


# 정확도/성능 수치처럼 논문 비교에 자주 필요한 값을 규칙 기반으로 뽑습니다.
# LLM이 없어도 "어떤 수치가 문서에 있었는지"를 답변에 포함하기 위한 보조 함수입니다.
def _metric_candidates(text: str, limit: int = 8) -> list[str]:
    metric_pattern = re.compile(
        r"(?i)\b(accuracy|precision|recall|f1(?:-score)?|auc|map|bleu|rouge|정확도|정밀도|재현율|성능|오차율|속도)\b"
        r"[^\n]{0,90}?(?:\d+(?:\.\d+)?\s?%|\d+\.\d+)"
    )
    percent_pattern = re.compile(r"[^\n]{0,70}\d+(?:\.\d+)?\s?%[^\n]{0,70}")
    statistic_unit_pattern = re.compile(
        r"[^.\n]{0,70}"
        r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?"
        r"(?:명|건|회|개|원|만원|억원|조원|%|퍼센트|년|월|일|시간|km|㎞)"
        r"[^.\n]{0,70}"
    )

    candidates = [_clean_text(match.group(0)) for match in metric_pattern.finditer(text)]
    if len(candidates) < limit:
        candidates.extend(_clean_text(match.group(0)) for match in percent_pattern.finditer(text))
    if len(candidates) < limit:
        candidates.extend(_clean_text(match.group(0)) for match in statistic_unit_pattern.finditer(text))

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
        if len(unique_candidates) >= limit:
            break
    return unique_candidates


def _extractive_summary(text: str, question: str = "", limit: int = 4) -> list[str]:
    summary = _top_sentences(text, limit, question)
    if summary:
        return summary
    cleaned = _clean_text(text)
    return [cleaned[:360]] if cleaned else []


def _doc_brief(doc: dict) -> dict:
    text = doc.get("text", "")
    return {
        "filename": doc.get("filename", "unknown"),
        "format": doc.get("format", "unknown"),
        "key_points": _top_sentences(text, 4) or [text[:260] if text else "추출된 텍스트가 없습니다."],
        "keywords": _frequent_terms(text, 6),
        "metrics": _metric_candidates(text, 5),
    }




