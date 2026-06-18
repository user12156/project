# 서비스: 로컬 문서 분석 점수 가중치를 한곳에서 관리합니다.
"""Central scoring weights for local document analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryRelevanceWeights:
    overlap: float = 1.8
    coverage: float = 5.0
    compact_term: float = 1.2
    semantic: float = 18.0


@dataclass(frozen=True)
class ChunkRankWeights:
    frequent_term: float = 0.15
    frequent_term_cap: float = 3.0
    metric: float = 15.0
    noise_penalty: float = -8.0
    focused_score_ratio: float = 0.35


@dataclass(frozen=True)
class SentenceRankWeights:
    quality_good: float = 2.0
    quality_short: float = 0.8
    quality_long: float = 0.4
    quality_outlier: float = -2.0
    cue_keyword: float = 1.2
    negative_cue_penalty: float = -1.4
    numeric_signal: float = 0.9
    comma_overload_penalty: float = -1.2
    domain_keyword: float = 2.2
    metric_signal: float = 2.5
    term_frequency: float = 0.38
    term_frequency_cap: float = 4.0
    leading_sentence_bonus: float = 1.6
    leading_sentence_decay: float = 0.04


QUERY_RELEVANCE_WEIGHTS = QueryRelevanceWeights()
CHUNK_RANK_WEIGHTS = ChunkRankWeights()
SENTENCE_RANK_WEIGHTS = SentenceRankWeights()
