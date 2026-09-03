# -*- coding: utf-8 -*-
"""BM25 검색 — 의미 검색과 나란히 비교하기 위한 키워드 기반 방식.

임베딩 없이, 질문과 조각에 같은 단어가 얼마나 겹치는지로 순위를 매긴다.
저장소에 이미 있는 조각(ChromaDB)을 그대로 코퍼스로 쓰고, 검색마다
그 자리에서 인덱스를 다시 만든다. 조각이 수백~수천 개 수준인 실습
규모에서는 이 편이 인덱스를 따로 관리하는 것보다 단순하다.

Okapi BM25 공식을 그대로 쓴다 (k1=1.5, b=0.75, rank_bm25 라이브러리와 동일 기본값).
"""

import math
import re

from . import store

K1 = 1.5
B = 0.75

_TOKEN = re.compile(r"[0-9a-zA-Z가-힣]+")


def tokenize(text):
    """아주 단순한 토큰화 — 한글·영문·숫자 덩어리를 하나의 단어로 본다.

    형태소 분석을 하지 않으므로 조사가 붙은 한국어 단어는 정확히 겹치지
    않으면 매칭되지 않는다. BM25 가 무엇을 잘하고 무엇을 못하는지 그대로
    드러내는 편이 낫다.
    """
    return _TOKEN.findall(text.lower())


def _corpus(documents=None):
    """저장소에 있는 청크. documents 를 주면 그 문서들만. → (documents, metadatas)"""
    col = store._collection()
    if col.count() == 0:
        return [], []
    kwargs = {"include": ["documents", "metadatas"]}
    if documents:
        kwargs["where"] = {"document": {"$in": documents}}
    got = col.get(**kwargs)
    return got.get("documents") or [], got.get("metadatas") or []


def search(query, k, documents=None):
    """→ store.query() 와 같은 모양의 히트 목록 (화면에서 그대로 재사용)."""
    docs, metas = _corpus(documents)
    n = len(docs)
    if n == 0:
        return []

    tokenized = [tokenize(d) for d in docs]
    doc_len = [len(t) for t in tokenized]
    avgdl = (sum(doc_len) / n) or 1.0

    df = {}
    for toks in tokenized:
        for term in set(toks):
            df[term] = df.get(term, 0) + 1

    def idf(term):
        nq = df.get(term, 0)
        return math.log((n - nq + 0.5) / (nq + 0.5) + 1)

    q_terms = tokenize(query)
    scores = [0.0] * n
    for i, toks in enumerate(tokenized):
        if not doc_len[i]:
            continue
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for term in q_terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            denom = freq + K1 * (1 - B + B * doc_len[i] / avgdl)
            s += idf(term) * (freq * (K1 + 1)) / denom
        scores[i] = s

    order = sorted(range(n), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order:
        if len(out) >= k:
            break
        if scores[i] <= 0:
            continue
        m = metas[i]
        out.append({
            "rank": len(out) + 1,
            "score": round(scores[i], 4),
            "text": docs[i],
            "document": m.get("document"),
            "chunk_index": m.get("chunk_index"),
            "page": m.get("page"),
            "strategy": m.get("strategy"),
            "n_chars": m.get("n_chars"),
        })
    return out
