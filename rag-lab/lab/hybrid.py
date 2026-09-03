# -*- coding: utf-8 -*-
"""하이브리드 검색 — 의미 검색과 BM25 를 순위로 합친다.

점수를 그대로 더하지 않는다. 코사인 유사도는 0~1 사이에 갇혀 있고,
BM25 점수는 용어 빈도·문서 길이에 따라 위로 열려 있어 계산법 자체가
다르다. 그래서 각 방식이 매긴 **순위**만 보고 Reciprocal Rank Fusion
(RRF) 으로 합친다.

    RRF(chunk) = Σ 1 / (RRF_K + rank_i)

한쪽에만 나온 조각은 그 한쪽의 순위만 더한다. RRF_K 는 1등과 10등의
차이가 지나치게 벌어지지 않도록 완충하는 상수로, 원 논문
(Cormack, Clarke & Buettcher, 2009) 의 기본값 60 을 그대로 쓴다.
"""

RRF_K = 60


def _key(hit):
    return (hit.get("document"), hit.get("chunk_index"))


def fuse(semantic_hits, bm25_hits, k):
    """의미 검색·BM25 각각의 히트 목록(이미 순위가 매겨져 있음) → 합친 히트 목록.

    두 목록에 이미 담긴 조각만 다룬다. 화면의 세 컬럼이 정확히 같은
    후보를 놓고 순위만 다르게 보는 것이어야 비교가 성립하기 때문에,
    별도로 더 넓은 후보 풀을 다시 검색하지 않는다.
    """
    pool = {}
    for hits in (semantic_hits, bm25_hits):
        for h in hits:
            key = _key(h)
            entry = pool.setdefault(key, {"hit": h, "rrf": 0.0})
            entry["rrf"] += 1.0 / (RRF_K + h["rank"])
            entry["hit"] = h   # 같은 청크이므로 텍스트·메타데이터는 어느 쪽이든 같다

    ordered = sorted(pool.values(), key=lambda e: e["rrf"], reverse=True)[:k]
    out = []
    for rank, entry in enumerate(ordered, 1):
        h = entry["hit"]
        out.append({
            "rank": rank,
            "score": round(entry["rrf"], 4),
            "text": h.get("text"),
            "document": h.get("document"),
            "chunk_index": h.get("chunk_index"),
            "page": h.get("page"),
            "strategy": h.get("strategy"),
            "n_chars": h.get("n_chars"),
        })
    return out
