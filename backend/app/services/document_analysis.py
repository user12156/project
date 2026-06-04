# 초보자 안내: PDF, DOCX, HWPX, 이미지 등에서 텍스트를 뽑고 기본 분석 결과를 만드는 서비스입니다.

import io
import math
import re
import struct
import zipfile
import subprocess
import tempfile
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from ..core.config import settings
<<<<<<< HEAD
=======
from .topic_modeling import extract_topics
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10

# 이 파일은 AI가 직접 동작하는 곳이 아니라, AI에 넣을 텍스트를 준비하는 전처리 서비스입니다.
# 파일 형식별로 본문 텍스트를 추출하고, OpenAI 키가 없을 때 쓸 기본 분석 결과도 만듭니다.
# 사용 라이브러리:
# - PyMuPDF(fitz): PDF 텍스트 추출
# - zipfile + ElementTree: DOCX/HWPX 내부 XML 텍스트 추출
# - olefile + struct + zlib: 구형 HWP 바이너리 본문 추출 시도
# - Pillow(PIL): 이미지 크기/형식 확인
# - pytesseract: 이미지 속 글자 OCR. 단, PC에 Tesseract 실행 파일도 별도 설치되어야 합니다.

TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
CHUNK_SIZE = 900
CHUNK_OVERLAP = 160
EXTRACTION_NOISE_PATTERN = re.compile(r"[\u0100-\u024f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
IMAGE_META_PATTERNS = (
    re.compile(r"원본\s*그림의\s*이름\s*:\s*CLP[^\s]+", re.IGNORECASE),
    re.compile(r"원본\s*그림의\s*크기\s*:\s*가로\s*\d+\s*pixel\s*,?\s*세로\s*\d+\s*pixel", re.IGNORECASE),
<<<<<<< HEAD
=======
    re.compile(r"그림\s*입니다\.?", re.IGNORECASE),
    re.compile(r"이미지\s*입니다\.?", re.IGNORECASE),
    re.compile(r"binaryitemid\s*[:=]\s*[^\s]+", re.IGNORECASE),
    re.compile(r"href\s*[:=]\s*[^\s]+", re.IGNORECASE),
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
)
FORMULA_NOISE_PATTERN = re.compile(
    r"\{[^{}]{0,100}(?:TIMES|over)[^{}]{0,220}\}|(?:TIMES|over)\s*`?\s*1,?0{2,}",
    re.IGNORECASE,
)

# WikiDocs의 한국어 QA 예제는 사용자 사전을 추가한 형태소 분석으로
# 사람 이름/전문용어가 잘게 쪼개지는 문제를 줄이는 아이디어를 소개합니다.
# 우리 프로젝트에서는 설치가 까다로운 형태소 분석기를 필수로 두지 않고,
# 설치되어 있으면 사용하고 없으면 정규식 기반 토큰화로 안전하게 동작하게 합니다.
DOMAIN_TERMS = {
    "RAG",
    "LLM",
    "BERT",
    "GPT",
    "OWPML",
    "HWPX",
    "HWP",
    "FastAPI",
    "MongoDB",
    "정확도",
    "정밀도",
    "재현율",
    "데이터셋",
    "벤치마크",
    "마인드맵",
    "시각화",
}

INTENT_CUE_TERMS = {
    "summary": {
        "중요",
        "중요도",
        "핵심",
        "요약",
        "우선순위",
        "의미",
        "강조",
        "주제",
        "결론",
        "목적",
        "필요성",
    },
    "metrics": {
        "실험",
        "결과",
        "성능",
        "정확도",
        "정밀도",
        "재현율",
        "비율",
        "수치",
        "평가",
        "검증",
        "동향",
        "추이",
        "변화",
        "증가",
        "감소",
        "이동",
        "이동량",
    },
    "compare": {
        "비교",
        "차이",
        "공통점",
        "차별점",
        "반면",
        "그러나",
        "반대로",
        "유사",
    },
    "extract": {
        "문장",
        "발췌",
        "인용",
        "근거",
        "부분",
        "구절",
        "원문",
    },
}

QUERY_EXPANSIONS = {
    "중요도": {"중요", "핵심", "우선순위", "비중", "영향", "강조", "의미", "필요성"},
    "중요": {"중요도", "핵심", "우선순위", "의미", "필요성"},
    "요약": {"핵심", "개요", "정리", "결론", "목적"},
    "분석": {"핵심", "근거", "결과", "특징", "의미"},
    "결과": {"실험", "성능", "수치", "평가", "검증"},
    "성능": {"정확도", "정밀도", "재현율", "f1", "평가", "결과"},
    "동향": {"추이", "변화", "증가", "감소", "흐름", "수치"},
    "추이": {"동향", "변화", "증가", "감소", "흐름", "수치"},
    "이동": {"이동량", "전입", "전출", "지역", "동향", "추이"},
    "이동량": {"이동", "전입", "전출", "지역", "동향", "추이"},
    "비교": {"차이", "공통점", "차별점", "반면", "유사"},
    "차이": {"비교", "차별점", "반면", "다른"},
    "발췌": {"문장", "근거", "구절", "인용", "원문"},
}

KOREAN_SUFFIXES = (
    "에서는",
    "에게서",
    "으로서",
    "으로써",
    "입니다",
    "합니다",
    "였다",
    "했다",
    "에서",
    "으로",
    "에게",
    "보다",
    "처럼",
    "까지",
    "부터",
    "이며",
    "이고",
    "지만",
    "는데",
    "거나",
    "하고",
    "라는",
    "이란",
    "되었습니다",
    "했습니다",
    "됩니다",
    "합니다",
    "되었",
    "하였",
    "했다",
    "된다",
    "하다",
    "였다",
    "보였다",
    "나왔다",
    "있었다",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "의",
    "도",
    "와",
    "과",
    "로",
)


# 공백과 HTML 엔티티를 정리해 분석하기 쉬운 한 줄 텍스트로 만듭니다.
def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = EXTRACTION_NOISE_PATTERN.sub(" ", text)
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
    """반복 문자와 감탄 표현을 가벼운 정규식으로 정리합니다."""

    if not text:
        return ""

    return re.sub(r"(.)\1{2,}", r"\1\1", text)


def preprocess_korean_text(text: str) -> str:
    """문서 분석 전 한국어 텍스트를 정제/정규화하는 공통 입구입니다."""

    cleaned = _clean_text(text)
    normalized = _normalize_repeated_korean(cleaned)
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
    symbol_count = len(re.findall(r"[^가-힣A-Za-z0-9\s.,%()/-]", sentence))
    if symbol_count / max(len(sentence), 1) > 0.22:
        return True
    return False


def _is_negative_sentence(sentence: str) -> bool:
    return bool(re.search(r"(아니다|않다|없다|낮다|제외|부족|어렵다|불가능)", sentence))


def _question_wants_negative(question: str) -> bool:
    return bool(re.search(r"(아닌|제외|낮은|낮다|부족|한계|문제|어려운|불가능|단점)", question or ""))


def _strip_korean_suffix(word: str) -> str:
    """조사/어미가 붙은 한국어 단어를 키워드 비교용으로 가볍게 정규화합니다."""

    for suffix in KOREAN_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[: -len(suffix)]
    return word


def _regex_terms(text: str) -> list[str]:
    """외부 형태소 분석기가 없을 때 쓰는 기본 토큰화입니다."""

    terms = []
    for word in re.findall(r"[A-Za-z가-힣0-9]{2,}", text.lower()):
        normalized = _strip_korean_suffix(word)
        if normalized.isdigit() or re.fullmatch(r"\d+(?:월|년|분기|일)", normalized):
            continue
        if len(normalized) >= 2:
            terms.append(normalized)
    return terms


def _tokenize_terms(text: str) -> list[str]:
    """가벼운 정규식 기반 한국어/영어 토큰화입니다."""

    return _regex_terms(text)


def _expanded_query_terms(question: str) -> set[str]:
    terms = set(_tokenize_terms(question or ""))
    for term in list(terms):
        terms.update(QUERY_EXPANSIONS.get(term, set()))
    intent = _question_intent(question)
    terms.update(INTENT_CUE_TERMS.get(intent, set()))
    return {term for term in terms if len(term) >= 2}


def _sentence_query_overlap(sentence: str, query_terms: set[str]) -> tuple[int, float]:
    if not query_terms:
        return 0, 0.0
    compact_sentence = _compact_for_match(sentence)
    sentence_terms = set(_tokenize_terms(sentence))
    matched = {
        term
        for term in query_terms
        if term in sentence_terms or term in compact_sentence
    }
    return len(matched), len(matched) / max(len(query_terms), 1)


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


def _safe_cosine(left, right) -> float:
    try:
        numerator = sum(float(a) * float(b) for a, b in zip(left, right))
        left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
        right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)
    except Exception:
        return 0.0


def _mean_vector(vectors: list) -> list[float]:
    if not vectors:
        return []
    width = len(vectors[0])
    return [
        sum(float(vector[index]) for vector in vectors) / len(vectors)
        for index in range(width)
    ]


def _semantic_text_features(anchor: str, texts: list[str]) -> dict | None:
    """이미 학습된 임베딩 모델로 텍스트 중요도 특징을 계산합니다.

    sentence-transformers가 없거나 ENABLE_BERT_GROUNDING=false이면 None을 반환하고
    기존 규칙 기반 발췌만 사용합니다. 새로 학습하지 않고, 사전학습 모델의 의미 공간에서
    질문 관련성(relevance)과 문서 중심성(centrality)을 함께 봅니다.
    """

    cleaned_texts = [_clean_text(text) for text in texts if _clean_text(text)]
    if not cleaned_texts or not settings.enable_bert_grounding:
        return None

    try:
        from .grounding import _embedding_model
    except Exception:
        return None

    model = _embedding_model()
    if model is None:
        return None

    instruction = settings.bert_grounding_instruction
    default_anchor = "문서의 핵심 주장, 중요한 근거, 실험 결과, 수치, 결론"
    query_text = anchor or default_anchor
    query = f"Instruct: {instruction}\nQuery: {query_text}" if instruction else query_text

    try:
        embeddings = model.encode(
            [query, *cleaned_texts],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception:
        return None

    vectors = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
    query_vector = vectors[0]
    text_vectors = vectors[1:]
    centroid = _mean_vector(text_vectors)
    return {
        "texts": cleaned_texts,
        "vectors": text_vectors,
        "relevance": [round(_safe_cosine(query_vector, vector), 4) for vector in text_vectors],
        "centrality": [round(_safe_cosine(centroid, vector), 4) for vector in text_vectors],
    }


def _select_diverse_ranked(
    ranked: list[dict],
    limit: int,
    vectors: list | None = None,
    *,
    penalty: float = 5.0,
) -> list[dict]:
    """MMR 방식으로 점수는 높지만 서로 너무 비슷한 항목은 덜 뽑습니다."""

    if not ranked or limit <= 0:
        return []
    if not vectors:
        return ranked[:limit]

    selected: list[dict] = []
    remaining = list(ranked)
    while remaining and len(selected) < limit:
        best_item = None
        best_adjusted = -10**9
        for item in remaining:
            adjusted = float(item.get("score", 0.0))
            if selected:
                item_index = item.get("vector_index")
                if isinstance(item_index, int) and 0 <= item_index < len(vectors):
                    redundancy = max(
                        (
                            _safe_cosine(vectors[item_index], vectors[selected_item["vector_index"]])
                            for selected_item in selected
                            if isinstance(selected_item.get("vector_index"), int)
                            and 0 <= selected_item["vector_index"] < len(vectors)
                        ),
                        default=0.0,
                    )
                    adjusted -= max(0.0, redundancy) * penalty
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_item = item
        if best_item is None:
            break
        selected.append(best_item)
        remaining.remove(best_item)
    return selected


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
    semantic_features = _semantic_text_features(question, sentences)
    semantic_relevance = semantic_features.get("relevance", []) if semantic_features else []
    semantic_centrality = semantic_features.get("centrality", []) if semantic_features else []
    semantic_vectors = semantic_features.get("vectors", []) if semantic_features else []
    scored = []
    for index, sentence in enumerate(sentences):
        matched_count, coverage = _sentence_query_overlap(sentence, query_terms)
        relevance_score = semantic_relevance[index] if index < len(semantic_relevance) else 0.0
        centrality_score = semantic_centrality[index] if index < len(semantic_centrality) else 0.0
        score = (
            _keyword_score(sentence, query_terms, term_weights)
            + max(0, 1.6 - index * 0.04)  # 초반 문장에 약간 가중치
        )
        if semantic_features:
            score += relevance_score * 14
            score += centrality_score * 10
        scored.append({
            "index": index,
            "vector_index": index,
            "sentence": sentence,
            "matched_count": matched_count,
            "coverage": coverage,
            "score": round(score, 4),
            "semantic_relevance": relevance_score,
            "semantic_centrality": centrality_score,
        })

    ranked = sorted(
        scored,
        key=lambda item: (
            item["score"],
            item["semantic_relevance"],
            item["semantic_centrality"],
            item["coverage"],
            -item["index"],
        ),
        reverse=True,
    )
    if question and not _question_wants_negative(question):
        non_negative = [item for item in ranked if not _is_negative_sentence(item["sentence"])]
        if non_negative:
            ranked = non_negative
    selected = _select_diverse_ranked(ranked, limit, semantic_vectors, penalty=4.5)
    selected = sorted(selected, key=lambda item: item["index"])
    return [item["sentence"] for item in selected]


# 자주 등장하는 단어를 뽑아 키워드 목록을 만듭니다.
# 조사/일반 단어는 stopwords로 제외합니다.
def _frequent_terms(text: str, limit: int = 10) -> list[str]:
    words = _tokenize_terms(text)
    stopwords = {
        "the",
        "and",
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


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """긴 문서를 RAG처럼 겹치는 청크로 나눕니다.

    LangChain의 RecursiveCharacterTextSplitter 개념을 가볍게 구현한 버전입니다.
    문장 경계를 우선 사용하고, 너무 긴 문장은 길이 기준으로 한 번 더 자릅니다.
    """

    cleaned = _clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    current = ""
    for sentence in _sentences(cleaned) or [cleaned]:
        if len(sentence) > chunk_size:
            step = max(chunk_size - overlap, 1)
            chunks.extend(sentence[index:index + chunk_size] for index in range(0, len(sentence), step))
            current = ""
            continue

        next_text = f"{current} {sentence}".strip()
        if len(next_text) <= chunk_size:
            current = next_text
            continue

        if current:
            chunks.append(current)
            current = f"{current[-overlap:]} {sentence}".strip() if overlap else sentence
        else:
            current = sentence

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk.strip()]


def _idf_weights(chunks: list[str]) -> dict[str, float]:
    token_sets = [set(_tokenize_terms(chunk)) for chunk in chunks]
    total = len(token_sets)
    document_frequency = Counter(token for tokens in token_sets for token in tokens)
    return {
        token: math.log((total + 1) / (count + 1)) + 1
        for token, count in document_frequency.items()
    }


def _compact_for_match(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def _query_terms_for_rank(question: str) -> list[str]:
    return list(_expanded_query_terms(question))


def rank_relevant_chunks(question: str, extracted_docs: list[dict], limit: int = 6) -> list[dict]:
    """질문과 가까운 문서 조각을 TF-IDF식 점수로 고릅니다.

    벡터DB 없이도 긴 문서에서 질문과 관련 있는 부분을 먼저 보여주기 위한 로컬 검색입니다.
    """

    candidates: list[dict] = []
    for doc in extracted_docs:
        source_units = doc.get("source_units") or [
            {
                "source_label": doc.get("source_label") or doc.get("format", "document"),
                "page_number": doc.get("page_number"),
                "section_index": doc.get("section_index"),
                "text": doc.get("text", ""),
            }
        ]
        chunk_index = 1
        for unit in source_units:
            for chunk in _chunk_text(unit.get("text", "")):
                candidates.append(
                    {
                        "filename": doc.get("filename", "unknown"),
                        "format": doc.get("format", "unknown"),
                        "chunk_index": chunk_index,
                        "source_label": unit.get("source_label") or doc.get("format", "document"),
                        "page_number": unit.get("page_number"),
                        "section_index": unit.get("section_index"),
                        "text": chunk,
                    }
                )
                chunk_index += 1

    if not candidates:
        return []

    query_terms = _expanded_query_terms(question) if question else set(
        _tokenize_terms(" ".join(_frequent_terms(" ".join(item["text"] for item in candidates), 8)))
    )
    compact_question = _compact_for_match(question)
    rank_terms = _query_terms_for_rank(question)
    important_phrases = (
        "시도별혼인건수",
        "시도별이혼건수",
        "시도별사망자수",
        "시도별출생아수",
        "시도별조혼인율",
        "시도별조이혼율",
        "시도별합계출산율",
        "혼인종류별혼인건수",
        "혼인건수",
        "이혼건수",
        "사망자수",
        "출생아수",
        "자연증가",
        "합계출산율",
    )
    idf = _idf_weights([item["text"] for item in candidates])
    semantic_features = _semantic_text_features(question, [item["text"] for item in candidates])
    semantic_relevance = semantic_features.get("relevance", []) if semantic_features else []
    semantic_centrality = semantic_features.get("centrality", []) if semantic_features else []
    semantic_vectors = semantic_features.get("vectors", []) if semantic_features else []

    ranked = []
    for vector_index, item in enumerate(candidates):
        term_counts = Counter(_tokenize_terms(item["text"]))
        if not term_counts:
            continue

        score = 0.0
        for term in query_terms:
            if not term:
                continue
            tf = term_counts.get(term, 0)
            if tf:
                score += (1 + math.log(tf)) * idf.get(term, 1)

        # 질문어가 적거나 일치가 거의 없을 때도 연구 핵심 문장 청크가 올라오게 보정합니다.
        score += sum(min(idf.get(term, 1), 3) for term in _frequent_terms(item["text"], 4)) * 0.15
        score += len(_metric_candidates(item["text"], 2)) * 1.4
        compact_text = _compact_for_match(item["text"])
        for phrase in important_phrases:
            if phrase in compact_question and phrase in compact_text:
                score += 25
        score += sum(1.2 for term in rank_terms if term in compact_text)
        matched_count, coverage = _sentence_query_overlap(item["text"], query_terms)
        score += matched_count * 1.8 + coverage * 5.0
        relevance_score = semantic_relevance[vector_index] if vector_index < len(semantic_relevance) else 0.0
        centrality_score = semantic_centrality[vector_index] if vector_index < len(semantic_centrality) else 0.0
        if semantic_features:
            score += relevance_score * 10
            score += centrality_score * 6
        if "원본그림" in compact_text or "수식입니다" in item["text"]:
            score -= 8

        ranked.append({
            **item,
            "score": round(score, 4),
            "vector_index": vector_index,
            "semantic_relevance": relevance_score,
            "semantic_centrality": centrality_score,
        })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return _select_diverse_ranked(ranked, limit, semantic_vectors, penalty=4.0)


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


# --- HWPX / HWP 파싱 보조 함수들 (PoC) -----------------------------
# 이 영역은 HWPX와 HWP 문서에서 텍스트/이미지를 추출하는 전용 파서 로직입니다.
# HWPX는 Zip+XML 기반 포맷이고, HWP는 구형 한글 바이너리 포맷이므로 각각 다른 접근을 사용합니다.
<<<<<<< HEAD
=======
def _local_name(tag: str) -> str:
    return str(tag or "").split("}", 1)[-1].split(":", 1)[-1].lower()


def _is_hwpx_body_xml(name: str) -> bool:
    lower = name.lower().replace("\\", "/")
    if not lower.endswith(".xml"):
        return False
    if lower.startswith(("settings/", "meta-inf/", "preview/", "docinfo")):
        return False
    return (
        "/section" in lower
        or lower.startswith("contents/section")
        or lower.startswith("contents/body")
        or lower.startswith("bodytext/")
    )


def _clean_hwpx_block(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\b(?:charpridref|parapridref|styleidref|borderfillidref)\b\s*\d*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:instid|zorder|numberingtype|textwrap|lock)\b\s*[:=]?\s*[A-Za-z0-9_-]+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:\[그림\]\s*){2,}", "[그림] ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_hwpx_noise_block(text: str) -> bool:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if not compact:
        return True

    lower = compact.lower()
    noise_patterns = [
        "원본 그림의 이름",
        "그림 크기",
        "내려 주기",
        "위로",
        "아래로",
        "오른쪽",
        "왼쪽",
        "image",
        "ole",
        "adobe photoshop",
    ]
    if any(pattern in lower for pattern in noise_patterns):
        return True
    if compact == "[그림]":
        return True
    if re.fullmatch(r"[\[\]그림\s]+", compact):
        return True
    return False


def _split_hwpx_sentences(block: str) -> list[str]:
    text = _clean_hwpx_block(block)
    if not text:
        return []

    text = re.sub(r"\s+(?=(?:○|※|\[[^\]]+\]|출처|자료|주기|주석)\b)", "\n", text)
    text = re.sub(r"(?<=[.!?])\s+(?=[가-힣A-Z0-9\"'(\[])", "\n", text)
    text = re.sub(r"(?<=(?:다|요|함|음|됨|임)\.)\s+(?=[가-힣A-Z0-9\"'(\[])", "\n", text)

    parts = [part.strip() for part in text.splitlines() if part.strip()]
    if len(parts) <= 1 and len(text) > 320:
        parts = re.split(r"(?<=\))\s+(?=[가-힣A-Z0-9])|(?<=\.)\s+(?=[가-힣A-Z0-9])", text)

    return [part.strip() for part in parts if part.strip()]


def _node_text(node) -> str:
    return _clean_hwpx_block(" ".join(part for part in node.itertext() if part and part.strip()))


def _paragraph_text(node) -> str:
    parts: list[str] = []
    for child in node.iter():
        name = _local_name(child.tag)
        if name in {"t", "text"} and child.text:
            parts.append(child.text)
        elif name in {"linebreak", "br"}:
            parts.append("\n")
        elif name in {"tab"}:
            parts.append("\t")
        elif name in {"pic", "image", "drawing", "ole"}:
            parts.append(" [그림] ")
    text = "".join(parts).strip()
    return _clean_hwpx_block(text or _node_text(node))


def _table_rows(node) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in node.iter():
        if _local_name(row.tag) not in {"tr", "row"}:
            continue
        cells: list[str] = []
        for cell in row:
            if _local_name(cell.tag) not in {"tc", "cell"}:
                continue
            cell_text = _node_text(cell)
            if cell_text:
                cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def _format_table(rows: list[list[str]], table_index: int) -> str:
    if not rows:
        return ""
    lines = [f"[표 {table_index}]"]
    for row in rows[:80]:
        lines.append(" | ".join(cell for cell in row if cell))
    return "\n".join(lines)


def _is_inside(node, ancestor_names: set[str], parent_map: dict) -> bool:
    parent = parent_map.get(node)
    while parent is not None:
        if _local_name(parent.tag) in ancestor_names:
            return True
        parent = parent_map.get(parent)
    return False


def _parse_hwpx_body_xml(raw: bytes) -> list[str]:
    try:
        root = ElementTree.fromstring(raw)
    except Exception:
        return []

    parent_map = {child: parent for parent in root.iter() for child in parent}
    blocks: list[str] = []
    table_index = 1

    for node in root.iter():
        name = _local_name(node.tag)
        if name in {"tbl", "table"}:
            table_text = _format_table(_table_rows(node), table_index)
            if table_text:
                blocks.append(table_text)
                table_index += 1
            continue

        if name in {"pic", "image", "drawing", "ole"} and not _is_inside(node, {"p", "para", "tbl", "table"}, parent_map):
            blocks.append("[그림]")
            continue

        if name not in {"p", "para"}:
            continue
        if _is_inside(node, {"tbl", "table"}, parent_map):
            continue
        paragraph = _paragraph_text(node)
        if paragraph and paragraph != "[그림]":
            blocks.append(paragraph)
        elif paragraph == "[그림]":
            blocks.append("[그림]")

    cleaned_blocks: list[str] = []
    seen = set()
    for block in blocks:
        for part in _split_hwpx_sentences(block):
            if _is_hwpx_noise_block(part):
                continue
            compact = re.sub(r"\s+", "", part)
            if not part or compact in seen:
                continue
            if len(compact) <= 1:
                continue
            seen.add(compact)
            cleaned_blocks.append(part)
    return cleaned_blocks


>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
def _parse_hwpx_bytes(data: bytes) -> tuple[str, list[dict]]:
    """HWPX(Zip+XML) 포맷을 안전하게 파싱합니다.

    반환값: (text, images)
    - text: 문서에서 추출한 텍스트(간단 정리)
    - images: [{'name': str, 'bytes': bytes}] 형태의 추출된 이미지들
    """
<<<<<<< HEAD
    texts = []
=======
    blocks = []
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    images = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                lname = name.lower()
<<<<<<< HEAD
                # XML 파일에서 텍스트 수집
                if lname.endswith('.xml'):
                    try:
                        raw = z.read(name)
                        try:
                            root = ElementTree.fromstring(raw)
                        except Exception:
                            # 일부 XML은 네임스페이스/깨진 문자 때문에 파싱이 실패할 수 있습니다.
                            # 태그 원문을 그대로 넣으면 분석 품질이 떨어지므로 이 파일은 건너뜁니다.
                            continue
                        # 모든 텍스트 노드 합치기
                        texts.append(' '.join(t for t in root.itertext() if t and t.strip()))
=======
                # 본문 XML만 문단/표/그림 단위로 수집합니다.
                if _is_hwpx_body_xml(name):
                    try:
                        blocks.extend(_parse_hwpx_body_xml(z.read(name)))
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
                    except KeyError:
                        continue

                # 이미지 파일 추출
                if any(lname.endswith(ext) for ext in IMAGE_EXTENSIONS) or lname.endswith('.svg'):
                    try:
                        images.append({'name': name, 'bytes': z.read(name)})
                    except KeyError:
                        continue

    except zipfile.BadZipFile:
        return "", []

<<<<<<< HEAD
    combined = '\n'.join(_clean_text(t) for t in texts if t)
=======
    if not blocks:
        # 일부 HWPX 변형은 본문 경로가 다를 수 있어, 마지막 fallback으로 XML 텍스트를 읽되
        # settings/docInfo/metadata 계열은 제외합니다.
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for name in z.namelist():
                    lname = name.lower().replace("\\", "/")
                    if not lname.endswith(".xml") or lname.startswith(("settings/", "meta-inf/", "docinfo")):
                        continue
                    try:
                        root = ElementTree.fromstring(z.read(name))
                    except Exception:
                        continue
                    text = _node_text(root)
                    if text:
                        blocks.append(text)
        except zipfile.BadZipFile:
            return "", images

    combined = '\n\n'.join(block for block in blocks if block)
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    return combined, images


def _parse_hwpx_with_java(jar_path: str, data: bytes) -> tuple[str, list[dict]]:
    """hwpxlib(Java) JAR을 호출해 문서 텍스트를 얻는 PoC.

    사용법: 환경변수 `HWPX_JAR`에 hwpxlib을 패키징한 JAR 경로를 설정하면
    `parse_document`가 이 함수를 우선 시도합니다.

    이 PoC는 JAR이 입력 파일 경로를 인자로 받아 정제된 본문 텍스트를
    표준출력(stdout)에 쓰는 간단한 CLI를 제공한다고 가정합니다.
    """
    if not jar_path or not Path(jar_path).is_file():
        return "", []

    # 임시 파일에 쓰고 JAR에 경로 전달
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.hwpx') as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        proc = subprocess.run([
            'java', '-jar', jar_path, tmp_path
        ], capture_output=True, text=True, timeout=30)

        stdout = proc.stdout or ''
        stderr = proc.stderr or ''
        if proc.returncode != 0:
            # 실패 시 stderr를 로깅할 수 있도록 빈 결과 반환
            return "", []

        return _clean_text(stdout), []
    except Exception:
        return "", []
    finally:
        try:
            if 'tmp_path' in locals() and Path(tmp_path).exists():
                Path(tmp_path).unlink()
        except Exception:
            pass


def _parse_hwp_bytes(data: bytes) -> tuple[str, list[dict]]:
    """HWP(바이너리) 파서는 외부 파서가 설치되어 있으면 시도합니다.

    HWP는 구형 한글문서 바이너리 포맷이므로 일반 XML/Zip 파서로는 열리지 않습니다.
    따라서 python-hwplib처럼 HWP 전용 라이브러리를 사용해 문서를 해석해야 합니다.

    - 우선 `hwplib` (python-hwplib) 모듈을 import 시도합니다.
    - 모듈이 없거나 실패하면 빈 텍스트와 빈 이미지 목록을 반환합니다.
    """
    try:
        # python-hwplib 래퍼가 설치되어 있으면 사용 시도
        import hwplib

        try:
            # python-hwplib의 API는 버전에 따라 다르므로 안전한 접근
            # HWPDocument 등 친숙한 클래스가 존재하면 사용하고, 없으면 예외 처리
            if hasattr(hwplib, 'HWPDocument'):
                doc = hwplib.HWPDocument(io.BytesIO(data))
                # 문서에서 텍스트를 수집하는 일반적 방법
                text_parts = []
                for para in getattr(doc, 'paragraphs', []) or []:
                    try:
                        text_parts.append(' '.join(p.text for p in para if getattr(p, 'text', None)))
                    except Exception:
                        continue
                return _clean_text('\n'.join(text_parts)), []

            # 다른 API 형태 시도
            if hasattr(hwplib, 'HwpDocument'):
                doc = hwplib.HwpDocument(io.BytesIO(data))
                txt = str(doc)
                return _clean_text(txt), []

        except Exception:
            return "", []

    except ModuleNotFoundError:
        # 사용자가 아직 설치하지 않았음
        return "", []

    return "", []


def parse_document(file_bytes: bytes, filename: str = "document") -> dict:
    """파일 바이트와 이름으로 문서의 텍스트와 내장 이미지를 추출해 구조화된 dict 반환.

    반환 예:
    {
      'filename': '...',
      'format': 'hwpx'|'hwp'|'unknown',
      'text': '...',
      'images': [ {'name':..., 'bytes':...}, ... ]
    }
    """
    ext = Path(filename).suffix.lower()
    if ext == '.hwpx':
        # 우선적으로 Java hwpxlib JAR을 사용하도록 시도합니다.
        jar_path = settings.hwpx_jar
        if jar_path:
            try:
                text, images = _parse_hwpx_with_java(jar_path, file_bytes)
                if text or images:
                    return {'filename': filename, 'format': 'hwpx', 'text': text, 'images': images}
            except Exception:
                # Java 파서 실패 시 안전하게 폴백
                pass

        # 폴백: zip/xml 기반 파서
        text, images = _parse_hwpx_bytes(file_bytes)
        return {'filename': filename, 'format': 'hwpx', 'text': text, 'images': images}

    if ext == '.hwp':
        # HWP 바이너리 문서 처리는 _parse_hwp_bytes()에서 시도합니다.
        # 이 함수는 python-hwplib 같은 외부 파서가 설치되어 있으면 HWP 내부 텍스트를 추출합니다.
        text, images = _parse_hwp_bytes(file_bytes)
        return {'filename': filename, 'format': 'hwp', 'text': text, 'images': images}

    # 기본 폴백: zip 내부 XML 시도 (DOCX 등)
    try:
        text, images = _parse_hwpx_bytes(file_bytes)
        if text or images:
            return {'filename': filename, 'format': 'zip-xml', 'text': text, 'images': images}
    except Exception:
        pass

    return {'filename': filename, 'format': 'unknown', 'text': '', 'images': []}


def _parsed_text_or_message(parsed: dict, empty_message: str) -> str:
    text = _clean_text(parsed.get("text", ""))
    return text or empty_message


def _finalize_extracted_text(text: str) -> str:
    """파일별 추출기가 반환한 텍스트를 분석용으로 최종 전처리합니다."""

    return preprocess_korean_text(text)


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


def _document_from_units(filename: str, file_format: str, units: list[dict]) -> dict:
    finalized_units = _finalize_source_units(units, file_format)
    text = "\n\n".join(
        f"[{unit['source_label']}]\n{unit['text']}" for unit in finalized_units
    )
    return {
        "filename": filename,
        "format": file_format,
        "text": text,
        "source_units": finalized_units,
    }


def _question_intent(question: str) -> str:
    lowered = (question or "").lower()
    if any(word in lowered for word in ["중요", "핵심", "요약", "분석", "설명", "summary", "main"]):
        return "summary"
    if any(word in lowered for word in ["실험", "결과", "정확도", "성능", "동향", "추이", "이동", "이동량", "증가", "감소", "변화", "score", "accuracy", "f1"]):
        return "metrics"
    if any(word in lowered for word in ["비교", "차이", "다른", "compare", "difference"]):
        return "compare"
    if any(word in lowered for word in ["문장", "발췌", "인용", "quote", "extract"]):
        return "extract"
    return "general"


def _intent_label(intent: str) -> str:
    return {
        "summary": "핵심 내용과 중요도",
        "metrics": "동향과 수치 근거",
        "compare": "비교와 차이점",
        "extract": "중요 문장 발췌",
        "general": "문서 분석",
    }.get(intent, "문서 분석")


def _intent_intro(question: str, intent: str) -> str:
    label = _intent_label(intent)
    if question:
        return f"질문하신 내용은 {label}에 관한 것으로 보입니다. 문서에서 근거가 되는 부분을 먼저 뽑아볼게요."
    return "업로드한 문서를 기준으로 핵심 내용을 먼저 정리해볼게요."


def _doc_brief(doc: dict) -> dict:
    text = doc.get("text", "")
    return {
        "filename": doc.get("filename", "unknown"),
        "format": doc.get("format", "unknown"),
        "key_points": _top_sentences(text, 4) or [text[:260] if text else "추출된 텍스트가 없습니다."],
        "keywords": _frequent_terms(text, 6),
        "metrics": _metric_candidates(text, 5),
    }


# PDF 분석은 PyMuPDF의 fitz.open(stream=..., filetype="pdf")를 사용합니다.
# 각 페이지의 텍스트를 page.get_text("text")로 꺼내 이어 붙입니다.
def extract_pdf(content: bytes) -> str:
    return "\n".join(unit["text"] for unit in extract_pdf_units(content))


def extract_pdf_units(content: bytes) -> list[dict]:
    try:
        import fitz
    except ModuleNotFoundError:
        return [
            {
                "page_number": 1,
                "source_label": "Page 1",
                "text": "PDF 분석을 위해 PyMuPDF 패키지가 필요합니다. requirements.txt 설치 후 다시 시도해주세요.",
            }
        ]

    with fitz.open(stream=content, filetype="pdf") as document:
        units: list[dict] = []
        for page_index, page in enumerate(document, start=1):
            page_text = page.get_text("text")
            if isinstance(page_text, str):
                text = page_text
            elif page_text is not None:
                text = str(page_text)
            else:
                text = ""
            if text.strip():
                units.append({"page_number": page_index, "source_label": f"Page {page_index}", "text": text})
        return units


# TXT/CSV/MD 파일은 인코딩을 순서대로 시도합니다.
# 한국어 Windows 파일은 cp949/euc-kr일 수 있어 함께 처리합니다.
def extract_text(content: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


# DOCX와 HWPX는 실제로 ZIP 안에 XML 문서들이 들어 있는 구조입니다.
# zipfile로 압축을 열고 ElementTree로 XML 노드의 text를 긁어옵니다.
def _iter_zip_xml_text(content: bytes, wanted_suffixes: Iterable[str]) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            lower_name = name.lower()
            if not lower_name.endswith(".xml"):
                continue
            if wanted_suffixes and not any(lower_name.endswith(suffix) for suffix in wanted_suffixes):
                continue
            try:
                root = ElementTree.fromstring(archive.read(name))
            except ElementTree.ParseError:
                continue
            for node in root.iter():
                if node.text and node.text.strip():
                    texts.append(node.text.strip())
    return _clean_text(" ".join(texts))


# DOCX의 본문은 보통 word/document.xml에 들어 있습니다.
def extract_docx(content: bytes) -> str:
    return _iter_zip_xml_text(content, ("word/document.xml",))


# .hwp 구형 바이너리 문서는 HWPX보다 훨씬 까다롭습니다.
# olefile로 OLE 컨테이너를 열고, BodyText/Section* 스트림의 HWPTAG_PARA_TEXT(67)를 읽습니다.
# 모든 HWP가 안정적으로 추출되지는 않으므로 실패하면 HWPX 변환 안내를 반환합니다.
def extract_hwp(content: bytes) -> str:
    try:
        import olefile
    except ModuleNotFoundError:
        return "HWP 바이너리 문서는 olefile 패키지 또는 HWPX 변환이 필요합니다."

    try:
        ole = olefile.OleFileIO(io.BytesIO(content))
    except Exception:
        return "HWP 파일 구조를 열 수 없습니다. HWPX로 변환 후 다시 업로드해주세요."

    try:
        header = ole.openstream("FileHeader").read()
        is_compressed = bool(header[36] & 1) if len(header) > 36 else False
        section_names = sorted(
            "/".join(path)
            for path in ole.listdir()
            if len(path) == 2 and path[0] == "BodyText" and path[1].startswith("Section")
        )

        chunks: list[str] = []
        for section_name in section_names:
            raw = ole.openstream(section_name).read()
            if is_compressed:
                import zlib

                raw = zlib.decompress(raw, -15)

            offset = 0
            while offset + 4 <= len(raw):
                header_value = struct.unpack_from("<I", raw, offset)[0]
                offset += 4
                tag_id = header_value & 0x3FF
                size = (header_value >> 20) & 0xFFF
                if size == 0xFFF:
                    if offset + 4 > len(raw):
                        break
                    size = struct.unpack_from("<I", raw, offset)[0]
                    offset += 4

                payload = raw[offset:offset + size]
                offset += size

                # HWPTAG_PARA_TEXT = 67이며, 본문 payload는 UTF-16LE 문자열입니다.
                if tag_id == 67 and payload:
                    chunks.append(payload.decode("utf-16le", errors="ignore"))

        text = _clean_text(" ".join(chunks))
        return text or "HWP 본문 텍스트를 찾지 못했습니다. HWPX로 변환하면 더 안정적으로 분석할 수 있습니다."
    except Exception:
        return "HWP 본문 추출 중 오류가 발생했습니다. HWPX로 변환 후 다시 업로드해주세요."
    finally:
        ole.close()


# 이미지는 현재 "이미지 자체를 이해하는 비전 모델"을 쓰는 것이 아닙니다.
# Pillow로 이미지 메타정보를 읽고, pytesseract로 이미지 안의 글자 OCR을 시도합니다.
# OCR까지 하려면 Python 패키지뿐 아니라 Tesseract 프로그램이 OS에 설치되어 있어야 합니다.
def inspect_image(content: bytes) -> str:
    try:
        from PIL import Image
    except ModuleNotFoundError:
        return "이미지 분석을 위해 Pillow 패키지가 필요합니다. requirements.txt 설치 후 다시 시도해주세요."

    image = Image.open(io.BytesIO(content))
    description = f"이미지 파일입니다. 크기: {image.width}x{image.height}px, 형식: {image.format}."

    try:
        import pytesseract
    except ModuleNotFoundError:
        return f"{description} 이미지 속 텍스트까지 발췌하려면 OCR 엔진(pytesseract/Tesseract)이 필요합니다."

    try:
        ocr_text = _clean_text(pytesseract.image_to_string(image, lang="kor+eng"))
    except Exception:
        return f"{description} OCR 실행 파일(Tesseract)이 설치되어 있지 않아 이미지 속 문자는 아직 읽을 수 없습니다."

    if not ocr_text:
        return f"{description} OCR로 읽힌 텍스트가 없습니다."
    return f"{description} OCR 추출 텍스트: {ocr_text}"


# 확장자를 보고 어떤 추출기를 사용할지 결정하는 입구 함수입니다.
def extract_file_document(filename: str, content: bytes) -> dict:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return _document_from_units(filename, "PDF", extract_pdf_units(content))
    if extension == ".hwpx":
        parsed = parse_document(content, filename)
<<<<<<< HEAD
=======
        raw_text = parsed.get("text", "")
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        text = _parsed_text_or_message(
            parsed,
            "HWPX/OWPML 내부에서 추출 가능한 본문 텍스트를 찾지 못했습니다.",
        )
<<<<<<< HEAD
        return _document_from_units(filename, "HWPX/OWPML", [{"section_index": 1, "text": text}])
=======
        document = _document_from_units(filename, "HWPX/OWPML", [{"section_index": 1, "text": text}])
        document["preview_text"] = raw_text or text
        return document
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    if extension == ".docx":
        return _document_from_units(filename, "DOCX", [{"section_index": 1, "text": extract_docx(content)}])
    if extension in TEXT_EXTENSIONS:
        return _document_from_units(filename, "TEXT", [{"section_index": 1, "text": extract_text(content)}])
    if extension in IMAGE_EXTENSIONS:
        return _document_from_units(filename, "IMAGE", [{"section_index": 1, "text": inspect_image(content)}])
    if extension == ".hwp":
        parsed = parse_document(content, filename)
<<<<<<< HEAD
        text = _parsed_text_or_message(parsed, "")
        if not text:
            text = extract_hwp(content)
        return _document_from_units(filename, "HWP", [{"section_index": 1, "text": text}])
=======
        raw_text = parsed.get("text", "")
        text = _parsed_text_or_message(parsed, "")
        if not text:
            text = extract_hwp(content)
        document = _document_from_units(filename, "HWP", [{"section_index": 1, "text": text}])
        document["preview_text"] = raw_text or text
        return document
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
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
        parsed = parse_document(content, filename)
        text = _parsed_text_or_message(parsed, "")
        if text:
            return _finalize_extracted_text(text), "HWP"
        return _finalize_extracted_text(extract_hwp(content)), "HWP"
    return "지원하지 않는 파일 형식입니다.", "UNKNOWN"


# OpenAI API가 없거나 실패했을 때도 답변을 만들기 위한 기본 분석 함수입니다.
# 진짜 LLM이 아니라, 위에서 추출한 텍스트에서 중요 문장/키워드를 규칙 기반으로 뽑습니다.
def build_analysis_answer(question: str, extracted_docs: list[dict]) -> dict:
<<<<<<< HEAD
    # [CRITICAL FIX] 불필요한 로컬 1차 분석을 완전히 꺼달라는 사용자 요청에 따라,
    # 키워드 추출, 문장 요약, 수치 검색 등의 무거운 로컬 연산을 모두 해제하고 빈 껍데기만 즉시 반환합니다.
    # 이제 로컬 서버는 오직 파일 해독 역할만 하며, 모든 문해력과 분석은 GPT 전담으로 돌아갑니다.
    return {
        "answer": "로컬 분석이 해제되었습니다.",
        "summary": "",
        "intent": "general",
        "keywords": [],
        "metrics": [],
        "topics": [],
        "documents": [],
        "relevant_chunks": [],
=======
    combined_text = "\n".join(doc["text"] for doc in extracted_docs if doc["text"])
    intent = _question_intent(question)
    relevant_chunks = rank_relevant_chunks(question, extracted_docs, 6)
    relevant_text = "\n".join(chunk["text"] for chunk in relevant_chunks) or combined_text
    highlights = _top_sentences(relevant_text, 10, question)
    summary_points = _extractive_summary(relevant_text, question, 4)
    terms = _frequent_terms(combined_text)
    metrics = _metric_candidates(combined_text)
    topics = extract_topics(combined_text)

    if not combined_text.strip():
        summary = (
            "업로드 파일은 받았지만 추출 가능한 본문 텍스트가 거의 없습니다. "
            "이미지라면 OCR 설치가 필요할 수 있고, 구형 HWP는 HWPX 변환이 더 안정적입니다."
        )
    else:
        summary = " ".join(summary_points) or combined_text[:600]

    comparison = [_doc_brief(doc) for doc in extracted_docs]
    keyword_sets = {item["filename"]: set(item["keywords"]) for item in comparison}

    answer_lines = [
        _intent_intro(question, intent),
        "",
        "LLM 없이 로컬 기본 분석으로 처리했습니다.",
        f"분석 기준: {_intent_label(intent)}",
        "",
        "[핵심 내용 요약]",
    ]

    if summary_points:
        answer_lines.extend(f"{index}. {point}" for index, point in enumerate(summary_points, start=1))
    else:
        answer_lines.append(summary)

    answer_lines.extend([
        "",
        "[중요 문장 발췌]",
    ])

    if highlights:
        answer_lines.extend(f"- {sentence}" for sentence in highlights[:8])
    else:
        answer_lines.append("- 발췌할 문장을 찾지 못했습니다.")

    answer_lines.extend([
        "",
        "[중요 키워드]",
        ", ".join(terms) if terms else "키워드를 추출할 텍스트가 부족합니다.",
        "",
        "[실험 결과/수치 후보]",
    ])

    if metrics:
        answer_lines.extend(f"- {metric}" for metric in metrics)
    else:
        answer_lines.append("- 정확도, F1, AUC, % 등으로 표시된 실험 수치 후보를 찾지 못했습니다.")

    if topics:
        answer_lines.extend(["", "[문서 주제 후보]"])
        for topic in topics[:5]:
            keywords = ", ".join(topic.get("keywords", [])[:5]) or topic.get("label", "주제")
            example = topic.get("examples", [""])[0] if topic.get("examples") else ""
            answer_lines.append(f"- {topic.get('label', '주제')}: {keywords}")
            if example:
                answer_lines.append(f"  · 근거 문장: {example[:180]}")

    if relevant_chunks:
        answer_lines.extend([
            "",
            "[질문 관련 문서 구간]",
        ])
        for chunk in relevant_chunks[:4]:
            focused = _top_sentences(chunk["text"], 1, question)
            preview = (focused[0] if focused else _clean_text(chunk["text"]))[:260]
            source_label = chunk.get("source_label") or f"Chunk {chunk['chunk_index']}"
            answer_lines.append(
                f"- {chunk['filename']} {source_label} "
                f"(관련도 {chunk['score']}): {preview}"
            )

    answer_lines.extend([
        "",
        "[문서별 핵심 발췌]",
    ])

    for item in comparison:
        answer_lines.append(f"- {item['filename']} ({item['format']})")
        answer_lines.extend(f"  · {point}" for point in item["key_points"][:4])
        if item["metrics"]:
            answer_lines.append(f"  · 수치 후보: {' / '.join(item['metrics'])}")
        if item["keywords"]:
            answer_lines.append(f"  · 키워드: {', '.join(item['keywords'][:6])}")

    if len(comparison) >= 2:
        answer_lines.extend(["", "[문서 간 차이점 후보]"])
        for item in comparison:
            other_terms = set().union(
                *(terms for filename, terms in keyword_sets.items() if filename != item["filename"])
            )
            unique_terms = [term for term in item["keywords"] if term not in other_terms]
            answer_lines.append(
                f"- {item['filename']}: {', '.join(unique_terms[:5]) if unique_terms else '다른 문서와 겹치는 키워드가 많습니다.'}"
            )

    if question:
        matched = _top_sentences(combined_text, 4, question)
        answer_lines.extend(["", "[질문 반영 답변]"])
        if matched:
            answer_lines.append(f"'{question}' 관점에서 가장 가까운 근거 문장은 아래와 같습니다.")
            answer_lines.extend(f"- {sentence}" for sentence in matched)
        else:
            answer_lines.append(f"'{question}'와 직접 연결되는 문장을 찾지 못해 전체 요약을 우선 제공했습니다.")

    return {
        "answer": "\n".join(answer_lines),
        "summary": summary,
        "intent": intent,
        "keywords": terms,
        "metrics": metrics,
        "topics": topics,
        "documents": comparison,
        "relevant_chunks": relevant_chunks,
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    }


