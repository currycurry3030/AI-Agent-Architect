# -*- coding: utf-8 -*-
"""벡터 저장소 (ChromaDB).

저장 1건 = 청크 원문 + 벡터 + 부가 정보(문서명 · 청크 번호 · 페이지 · 전략).

부가 정보를 지금 넣어 두는 이유가 있다. 2교시에는 화면에 보이기만 하지만,
3교시의 Metadata Filter 가 이 필드를 조건으로 쓴다. 나중에 스키마를 고치지
않으려면 처음부터 담아야 한다.

임베딩은 우리가 직접 계산해 넣는다. Chroma 의 기본 임베딩 함수를 쓰지 않으므로
모델을 내려받지 않는다.
"""

import os
import shutil

import chromadb

from . import config


def _client():
    os.makedirs(config.STORE_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=config.STORE_DIR)


def _collection(client=None):
    client = client or _client()
    return client.get_or_create_collection(
        name=config.COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def reset():
    """저장소를 비운다. 다시 적재할 때마다 처음부터 쌓는다."""
    try:
        _client().delete_collection(config.COLLECTION)
    except Exception:                          # noqa: BLE001 — 없으면 그만
        pass


def wipe_files():
    """파일까지 지운다. 앱을 초기 상태로 되돌릴 때만 쓴다."""
    shutil.rmtree(config.STORE_DIR, ignore_errors=True)


def add(doc_name, chunks, vectors):
    col = _collection()
    col.add(
        ids=["%s#%d" % (doc_name, c["index"]) for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=vectors,
        metadatas=[{
            "document": doc_name,
            "chunk_index": c["index"],
            "page": c["page"],
            "strategy": c["strategy"],
            "n_chars": c["n_chars"],
        } for c in chunks],
    )


def status():
    """적재 현황. 문서별 청크 수와 적용된 전략."""
    try:
        col = _collection()
        n = col.count()
    except Exception:                          # noqa: BLE001
        return {"total": 0, "documents": []}
    if n == 0:
        return {"total": 0, "documents": []}

    got = col.get(include=["metadatas"])
    by_doc = {}
    for m in got.get("metadatas") or []:
        d = by_doc.setdefault(m.get("document", "?"),
                              {"document": m.get("document", "?"),
                               "chunks": 0, "strategy": m.get("strategy", "?")})
        d["chunks"] += 1
    return {
        "total": n,
        "documents": sorted(by_doc.values(), key=lambda x: x["document"]),
        "model": config.EMBED_MODEL,
        "dim": config.EMBED_DIM,
    }


def query(vector, k, documents=None):
    """documents 를 주면 그 문서들 안에서만 찾는다. 없으면 전체."""
    col = _collection()
    if col.count() == 0:
        return []
    kwargs = {"query_embeddings": [vector], "n_results": min(k, col.count()),
              "include": ["documents", "metadatas", "distances"]}
    if documents:
        kwargs["where"] = {"document": {"$in": documents}}
    res = col.query(**kwargs)
    out = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for rank, (text, meta, dist) in enumerate(zip(docs, metas, dists), 1):
        out.append({
            "rank": rank,
            "score": round(1.0 - float(dist), 4),   # cosine 거리 → 유사도
            "distance": round(float(dist), 4),
            "text": text,
            **{k2: meta.get(k2) for k2 in
               ("document", "chunk_index", "page", "strategy", "n_chars")},
        })
    return out


def peek_vector(doc_name, chunk_index, head=10):
    """청크 하나의 벡터 앞부분. 문장이 실제로 숫자가 된 모습을 보여 준다."""
    col = _collection()
    got = col.get(ids=["%s#%d" % (doc_name, chunk_index)], include=["embeddings"])
    vecs = got.get("embeddings")
    if vecs is None or len(vecs) == 0:
        return None
    v = list(vecs[0])
    return {"dim": len(v), "head": [round(float(x), 4) for x in v[:head]]}
