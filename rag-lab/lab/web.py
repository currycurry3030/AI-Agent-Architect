# -*- coding: utf-8 -*-
"""로컬 웹서버와 API.

화면은 네 구획이고, 각 구획이 앞 구획의 산출물을 받는다.
  ① 문서   → ② 청킹 → ③ 임베딩·적재 → ④ 검색 테스트
"""

import json
import os
import re
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import answer as answer_mod
from . import rerank as rerank_mod
from . import rewrite as rewrite_mod
from . import bm25, chunking, config, hybrid, llm, parsing, store

# 파싱 결과와 청킹 결과를 메모리에 들고 있는다. 서버를 끄면 사라진다.
# 적재된 것만 chroma_db 에 남는다.
STATE = {"doc": None, "name": None, "chunks": [], "strategy": None, "size": None}


def _read_upload(headers, rfile):
    """multipart/form-data 에서 파일 하나를 꺼낸다. → (파일명, 바이트)

    표준 라이브러리의 cgi 모듈은 Python 3.13 에서 없어졌다. 수강생 PC 의
    파이썬 버전이 갈릴 수 있어 직접 읽는다.
    """
    ctype = headers.get("Content-Type") or ""
    m = re.search(r'boundary="?([^";]+)"?', ctype)
    if not m:
        return None, None
    boundary = ("--" + m.group(1)).encode()
    raw = rfile.read(int(headers.get("Content-Length") or 0))

    for part in raw.split(boundary):
        if b"\r\n\r\n" not in part:
            continue
        head, _, data = part.partition(b"\r\n\r\n")
        head_s = head.decode("utf-8", "replace")
        if "filename=" not in head_s:
            continue
        fn = re.search(r'filename="([^"]*)"', head_s)
        if not fn or not fn.group(1):
            continue
        return fn.group(1), data.rstrip(b"\r\n-")
    return None, None


def _json(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "rag-lab"

    def log_message(self, fmt, *args):
        print("  %s" % (fmt % args))

    # ── 정적 파일 ───────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"
        if path == "/api/status":
            return self._api_status()
        if path == "/api/document":
            return self._api_document()
        if path == "/api/chunks":
            return self._api_chunks()

        fs = os.path.join(config.STATIC_DIR, path.lstrip("/"))
        if not os.path.isfile(fs):
            return _json(self, {"error": "not found"}, 404)
        ctype = ("text/html" if fs.endswith(".html") else
                 "text/css" if fs.endswith(".css") else
                 "application/javascript" if fs.endswith(".js") else
                 "application/octet-stream")
        with open(fs, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "%s; charset=utf-8" % ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/upload":
                return self._api_upload()
            if path == "/api/chunk":
                return self._api_chunk()
            if path == "/api/embed":
                return self._api_embed()
            if path == "/api/search":
                return self._api_search()
            if path == "/api/vector":
                return self._api_vector()
            if path == "/api/reset":
                store.reset()
                return _json(self, {"ok": True, "status": store.status()})
            return _json(self, {"error": "not found"}, 404)
        except Exception as e:                 # noqa: BLE001
            traceback.print_exc()
            return _json(self, {"error": str(e)}, 500)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ── ① 문서 ─────────────────────────────────────────────────────
    def _api_upload(self):
        filename, data = _read_upload(self.headers, self.rfile)
        if not filename or not data:
            return _json(self, {"error": "파일이 없습니다"}, 400)

        os.makedirs(config.DATA_DIR, exist_ok=True)
        name = os.path.basename(filename)
        dest = os.path.join(config.DATA_DIR, name)
        with open(dest, "wb") as f:
            f.write(data)

        print("파싱 시작 — %s" % name)
        doc = parsing.parse_pdf(dest)
        STATE.update({"doc": doc, "name": name, "chunks": [],
                      "strategy": None, "size": None})
        print("파싱 완료 — %d쪽 / %d자 / 글자가 거의 없는 페이지 %d쪽"
              % (doc["n_pages"], doc["n_chars"], len(doc["thin_pages"])))
        return _json(self, self._doc_payload())

    def _doc_payload(self):
        doc = STATE["doc"]
        if not doc:
            return {"loaded": False}
        return {
            "loaded": True,
            "name": STATE["name"],
            "n_pages": doc["n_pages"],
            "n_chars": doc["n_chars"],
            "thin_pages": doc["thin_pages"],
            "empty_pages": doc["empty_pages"],
            "pages": [{"page": p["page"], "n_chars": p["n_chars"],
                       "thin": parsing.is_thin(p)} for p in doc["pages"]],
        }

    def _api_document(self):
        q = self.path.split("?", 1)
        page = 1
        if len(q) > 1:
            for kv in q[1].split("&"):
                if kv.startswith("page="):
                    page = int(kv[5:] or 1)
        doc = STATE["doc"]
        if not doc:
            return _json(self, {"loaded": False})
        page = max(1, min(page, doc["n_pages"]))
        p = doc["pages"][page - 1]
        return _json(self, {"loaded": True, "page": page,
                            "n_pages": doc["n_pages"],
                            "n_chars": p["n_chars"],
                            "thin": parsing.is_thin(p),
                            "text": p["text"]})

    # ── ② 청킹 ─────────────────────────────────────────────────────
    def _api_chunk(self):
        if not STATE["doc"]:
            return _json(self, {"error": "먼저 PDF 를 올려 주세요"}, 400)
        body = self._body()
        strategy = body.get("strategy", "fixed")
        size = body.get("size", config.CHUNK_SIZE_DEFAULT)
        chunks = chunking.chunk(STATE["doc"], strategy, size)
        STATE.update({"chunks": chunks, "strategy": strategy, "size": size})
        print("청킹 — %s / %d자 기준 / 청크 %d개"
              % (config.STRATEGIES[strategy], size, len(chunks)))
        return _json(self, {"strategy": strategy,
                            "strategy_label": config.STRATEGIES[strategy],
                            "size": size,
                            "summary": chunking.summarize(chunks),
                            "chunks": chunks})

    def _api_chunks(self):
        return _json(self, {"chunks": STATE["chunks"],
                            "strategy": STATE["strategy"],
                            "summary": chunking.summarize(STATE["chunks"])})

    # ── ③ 임베딩 · 적재 ────────────────────────────────────────────
    def _api_embed(self):
        if not STATE["chunks"]:
            return _json(self, {"error": "먼저 청킹을 실행하세요"}, 400)
        chunks = STATE["chunks"]
        print("임베딩 시작 — %d개" % len(chunks))

        def progress(done, total):
            print("  임베딩 %d/%d" % (done, total))

        vectors = llm.embed_many([c["text"] for c in chunks], progress)
        store.add(STATE["name"], chunks, vectors)
        print("적재 완료 — %s / %d건" % (STATE["name"], len(chunks)))
        return _json(self, {"ok": True, "added": len(chunks),
                            "status": store.status()})

    def _api_status(self):
        # 새로고침해도 지금까지 온 단계가 화면에 그대로 복원되어야 한다
        return _json(self, {"store": store.status(),
                            "document": self._doc_payload(),
                            "chunking": {"strategy": STATE["strategy"],
                                         "label": config.STRATEGIES.get(STATE["strategy"]),
                                         "size": STATE["size"],
                                         "summary": chunking.summarize(STATE["chunks"])},
                            "strategies": config.STRATEGIES,
                            "defaults": {"size": config.CHUNK_SIZE_DEFAULT,
                                         "k": config.TOP_K_DEFAULT}})

    def _api_vector(self):
        body = self._body()
        got = store.peek_vector(body.get("document"), int(body.get("chunk_index", 0)))
        return _json(self, got or {"error": "적재되지 않은 청크입니다"})

    # ── ④ 검색 ─────────────────────────────────────────────────────
    def _api_search(self):
        """의미 검색 · BM25 검색 · 하이브리드(RRF) — 필요하면 그 앞뒤로 질의
        재작성과 LLM 재정렬을 붙인다.

        재정렬을 켜면 하이브리드 후보만 뽑는다(의미·BM25 개별 결과는 화면에
        보여줄 이유가 없다). 문서 필터는 세 방식·재정렬 후보 단계 모두에
        똑같이 적용된다.
        """
        body = self._body()
        q0 = (body.get("query") or "").strip()
        k = max(1, min(int(body.get("k", config.TOP_K_DEFAULT)), config.TOP_K_MAX))
        if not q0:
            return _json(self, {"error": "질문을 입력하세요"}, 400)

        documents = [d for d in (body.get("documents") or []) if d] or None
        want_rerank = bool(body.get("rerank"))
        want_answer = bool(body.get("answer"))

        out = {"query": q0, "k": k}

        q = q0
        if body.get("rewrite"):
            t0 = time.time()
            q = rewrite_mod.rewrite(q0)
            out["rewrite"] = {"original": q0, "rewritten": q,
                              "latency": round(time.time() - t0, 2)}
            print("질의 재작성 — %r → %r" % (q0, q))

        vec = llm.embed_one(q)

        if want_rerank:
            cand_k = config.RERANK_CANDIDATES
            semantic_hits = store.query(vec, cand_k, documents)
            bm25_hits = bm25.search(q, cand_k, documents)
            candidates = hybrid.fuse(semantic_hits, bm25_hits, cand_k)

            t0 = time.time()
            reranked = rerank_mod.rerank(q, candidates, config.RERANK_TOP_N)
            latency = round(time.time() - t0, 2)
            print("검색(재정렬) — %r → 후보 %d개 / 재정렬 %d개 / %.2f초"
                  % (q[:40], len(candidates), len(reranked), latency))

            out["rerank"] = {"candidates": candidates, "hits": reranked, "latency": latency}
            if want_answer:
                t1 = time.time()
                got = answer_mod.answer(q, reranked)
                out["rerank"]["answer"] = {**got, "latency": round(time.time() - t1, 2),
                                           "model": config.GEN_MODEL}
        else:
            semantic_hits = store.query(vec, k, documents)
            bm25_hits = bm25.search(q, k, documents)
            hybrid_hits = hybrid.fuse(semantic_hits, bm25_hits, k)
            columns = [("semantic", semantic_hits), ("bm25", bm25_hits), ("hybrid", hybrid_hits)]

            print("검색 — %r → 의미 1위 %s / BM25 1위 %s / 하이브리드 1위 %s"
                  % (q[:40],
                     semantic_hits[0]["chunk_index"] if semantic_hits else "없음",
                     bm25_hits[0]["chunk_index"] if bm25_hits else "없음",
                     hybrid_hits[0]["chunk_index"] if hybrid_hits else "없음"))

            for name, hits in columns:
                out[name] = {"hits": hits}

            # 답변 생성은 선택이다. 먼저 어떤 조각이 뽑히는지 보고, 그다음에 켠다.
            if want_answer:
                latencies = {}
                for name, hits in columns:
                    t0 = time.time()
                    got = answer_mod.answer(q, hits)
                    latency = round(time.time() - t0, 2)
                    latencies[name] = latency
                    out[name]["answer"] = {**got, "latency": latency, "model": config.GEN_MODEL}
                print("   답변 생성 — 의미 %.2f초 / BM25 %.2f초 / 하이브리드 %.2f초"
                      % (latencies["semantic"], latencies["bm25"], latencies["hybrid"]))

        out["query_vector_head"] = [round(float(x), 4) for x in vec[:10]]
        out["dim"] = len(vec)
        return _json(self, out)


def serve():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    srv = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print("rag-lab  http://%s:%d/" % (config.HOST, config.PORT))
    print("종료하려면 이 창에서 Ctrl+C 를 누르세요.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
