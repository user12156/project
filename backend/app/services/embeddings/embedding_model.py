# 서비스: 임베딩 모델 로드와 코사인 유사도 계산 공통 함수를 제공합니다.
"""Shared sentence-transformer model loading and vector math."""

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def embedding_model():
    if not settings.enable_bert_grounding:
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        return SentenceTransformer(settings.bert_grounding_model)
    except Exception:
        return None


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def encode_texts(texts: list[str]):
    model = embedding_model()
    if model is None or not texts:
        return None

    try:
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception:
        return None

    return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

