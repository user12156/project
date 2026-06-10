# 서비스: 문서 주제 후보를 추출하며 로컬 토큰 기반과 필요 시 BERTopic 임베딩을 혼합합니다.
import re
from importlib import import_module
from collections import Counter

from app.core.config import settings
from app.services.embeddings.embedding_model import embedding_model


# 문서 분석 결과의 [문서 주제 후보]를 만드는 서비스입니다.
# 기본값은 가벼운 로컬 토큰/문장 기반 추출이고, BERTopic이 설치된 배포 환경에서는
# settings.topic_model_backend="bertopic"일 때만 사전학습 임베딩 기반 토픽을 시도합니다.

TOPIC_STOPWORDS = {
    "문서",
    "내용",
    "분석",
    "연구",
    "논문",
    "결과",
    "관련",
    "사용",
    "통해",
    "대한",
    "위해",
    "경우",
    "있는",
    "없는",
    "한다",
    "된다",
    "이다",
    "했다",
    "수행",
    "수행한다",
    "포함",
    "포함한다",
    "찾는다",
    "계산",
    "반복되",
    "표현한다",
    "그리고",
    "그러나",
    "따라서",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _split_units(text: str, limit: int = 160) -> list[str]:
    raw_units = re.split(r"(?<=[.!?。！？])\s+|(?<=다)\s+|\n+", str(text or ""))
    units = []
    for unit in raw_units:
        cleaned = _clean(unit)
        if 20 <= len(cleaned) <= 700:
            units.append(cleaned)
        if len(units) >= limit:
            break
    return units


def _strip_suffix(word: str) -> str:
    for suffix in ("에서는", "으로", "에서", "에게", "보다", "까지", "부터", "이며", "이고", "지만", "라는", "되는", "한다", "된다", "했다", "은", "는", "이", "가", "을", "를", "에", "의", "도", "와", "과", "로"):
        if word.endswith(suffix) and len(word) > len(suffix):
            return word[: -len(suffix)]
    return word


def _tokenize(text: str) -> list[str]:
    tokens = []
    for word in re.findall(r"[A-Za-z가-힣0-9]{2,}", text.lower()):
        token = _strip_suffix(word)
        if len(token) >= 2 and not token.isdigit():
            tokens.append(token)
    return tokens


def _local_topics(units: list[str], limit: int) -> list[dict]:
    unit_tokens = [
        [token for token in _tokenize(unit) if token not in TOPIC_STOPWORDS and len(token) >= 2]
        for unit in units
    ]
    token_counts = Counter(token for tokens in unit_tokens for token in tokens)
    topics = []
    used_keywords = set()
    for keyword, count in token_counts.most_common(limit * 3):
        if keyword in used_keywords:
            continue

        matching_units = []
        co_terms = Counter()
        for unit, tokens in zip(units, unit_tokens):
            if keyword not in tokens and keyword not in unit.lower():
                continue
            matching_units.append(unit)
            co_terms.update(token for token in tokens if token != keyword)

        related_keywords = [keyword]
        for term, _ in co_terms.most_common(5):
            if term not in used_keywords and term not in related_keywords:
                related_keywords.append(term)

        used_keywords.update(related_keywords)
        label = " / ".join(related_keywords[:3])
        topics.append(
            {
                "id": len(topics) + 1,
                "label": label,
                "keywords": related_keywords,
                "count": count,
                "examples": matching_units[:3],
                "method": "local-token",
            }
        )
        if len(topics) >= limit:
            break
    return topics


def _bertopic_topics(units: list[str], limit: int) -> list[dict] | None:
    if settings.topic_model_backend != "bertopic":
        return None
    if len(units) < 5:
        return None

    try:
        BERTopic = import_module("bertopic").BERTopic
    except Exception:
        return None

    try:
        model = embedding_model()
        if model is None:
            return None
        topic_model = BERTopic(
            embedding_model=model,
            language="multilingual",
            nr_topics="auto",
            verbose=False,
        )
        topics, _ = topic_model.fit_transform(units)
        info = topic_model.get_topic_info()
    except Exception:
        return None

    results = []
    for _, row in info.iterrows():
        topic_id = int(row.get("Topic", -1))
        if topic_id == -1:
            continue
        words = [word for word, _ in topic_model.get_topic(topic_id)[:6]]
        examples = [unit for unit, assigned in zip(units, topics) if assigned == topic_id][:3]
        results.append(
            {
                "id": topic_id,
                "label": ", ".join(words[:3]) if words else f"topic-{topic_id}",
                "keywords": words,
                "count": int(row.get("Count", 0)),
                "examples": examples,
                "method": "bertopic",
            }
        )
        if len(results) >= limit:
            break
    return results


def extract_topics(text: str, limit: int | None = None) -> list[dict]:
    if not settings.enable_topic_modeling:
        return []

    topic_limit = limit or settings.topic_model_limit
    units = _split_units(text)
    if not units:
        return []

    bertopic_topics = _bertopic_topics(units, topic_limit)
    if bertopic_topics:
        return bertopic_topics

    return _local_topics(units, topic_limit)
