# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A teaching app for a naive-RAG-to-advanced-RAG walkthrough (Korean-language course, "2·3교시 실습 앱"). It exposes each RAG stage — PDF parsing, chunking, embedding/indexing, retrieval, generation — as an observable step in a 4-panel UI. The retrieval panel now also includes the advanced techniques the README originally described as a later-session exercise (BM25, hybrid/RRF, metadata document filter, query rewrite, LLM reranking) — they were added directly to the app rather than left as a student exercise, so treat the README's "수강생이 만듭니다" framing for those as historical, not current.

Code and comments are in Korean, matching the course. Match that convention when editing `lab/*.py`.

## Running

```
copy .env.example .env      # then put OPENAI_API_KEY in it
pip install -r requirements.txt
python app.py                # or run.bat on Windows
```

Opens `http://127.0.0.1:8765/`. `app.py` checks for `chromadb`, `pypdf`, and `OPENAI_API_KEY` before starting and prints what's missing instead of crashing partway through — a student-facing safety net, keep it that way when touching `app.py`.

There is no test suite, linter, or build step in this repo — it's a single-session teaching app, not a package.

## Architecture

Stdlib `http.server` backend (no Flask/FastAPI) serving a static HTML/JS/CSS frontend. No frontend build step — `static/app.js` is loaded directly.

**Request flow:** `static/app.js` → `/api/*` routes in `lab/web.py` → stage module (`parsing` / `chunking` / `llm` + `store` / `answer`).

**Pipeline stages, each feeding the next (mirrors the 4 UI panels):**
1. `lab/parsing.py` — PDF → text via `pypdf`. Deliberately does **not** reconstruct tables; a page with very little extracted text (`THIN_PAGE_CHARS`) signals an image-based table, and that's the pedagogical point — don't "fix" this by adding table extraction.
2. `lab/chunking.py` — three strategies (`fixed`, `structure`, `paragraph`), no overlap by design (chunk boundaries must be visible for comparison). `structure` splits on detected headings (numbered sections, `제N조`, `Section/Chapter`) and merges short fragments back together to avoid table-of-contents pages exploding into hundreds of tiny chunks.
3. `lab/llm.py` — direct HTTP calls to the OpenAI API (`urllib`, no SDK), so students can see exactly what's sent. This is the **only** place chunk text leaves the machine. Embeddings and generation share this module; query and document text use the same embedding model/config (no separate query-embedding mode).
4. `lab/store.py` — ChromaDB (`PersistentClient`, cosine space), storing chunk text + vector + metadata (`document`, `chunk_index`, `page`, `strategy`, `n_chars`) together from the start, since a later session's Metadata Filter exercise relies on those fields already being present — don't defer adding metadata.
5. `lab/answer.py` — builds a grounded prompt from retrieved hits only (never the full document) and calls `lab/llm.py`'s `generate`.

**Retrieval methods, run side by side (`lab/web.py::_api_search`):**
- Semantic (`store.query`) and `lab/bm25.py` (hand-rolled Okapi BM25, no external dependency — reindexes the whole ChromaDB corpus on every call rather than maintaining a separate persistent index; fine at lab scale) each return the same hit shape (`rank`, `score`, `text`, `document`, `chunk_index`, `page`, `strategy`, `n_chars`), which is why the frontend can render either through the same `chunkNode()`.
- `lab/hybrid.py` fuses those two hit lists by **Reciprocal Rank Fusion**, not by summing scores — cosine similarity and BM25 scores live on different scales, so only the rank each method assigned is comparable. It only re-ranks the two existing top-K lists; it does not re-query the store with a wider candidate pool.
- All three run for every `/api/search` call, and each optionally gets its own independently-generated answer (see below) — this is intentional 3-way comparison, not redundant work to trim.

**Reranking (`lab/rerank.py`), query rewrite (`lab/rewrite.py`), document filter — all optional, toggled per request:**
- `rerank: true` short-circuits the 3-way comparison above: only hybrid runs, fetching `config.RERANK_CANDIDATES` (10) candidates instead of K, then `rerank.rerank()` sends all 10 to the LLM (`config.GEN_MODEL`) in one prompt asking it to return candidate numbers in relevance order, and the top `config.RERANK_TOP_N` (5) become the answer's context. If the model's reply doesn't parse into enough valid numbers, remaining slots are filled back in hybrid order — never fail the request over a parsing miss.
- `rewrite: true` runs before embedding/search: `rewrite.rewrite()` sends the raw query to the LLM and the *rewritten* query is what actually gets embedded and searched (semantic, BM25, and reranking all see only the rewritten form). Both the original and rewritten text are returned so the UI can show them side by side.
- `documents: [...]` (a list of document filenames from `/api/status`'s `store.documents`) restricts `store.query` and `bm25.search` via a Chroma `where={"document": {"$in": ...}}` filter; an empty/omitted list means the whole store. Applies identically whether or not reranking is on.

**Server state (`lab/web.py::STATE`):** parsed doc + chunks live in memory only and are lost on restart; only embedded/indexed data persists, in `chroma_db/`. `/api/status` reconstructs UI state from this on page refresh — keep it in sync with `STATE` when adding fields.

**Config (`lab/config.py`):** model names, ports, chunking bounds. Comment in the file says these aren't meant to change during class — treat this as a real constraint, not a suggestion, when asked to "just bump the model" etc. Note `GEN_MODEL` is fixed by the instructor per course run.

**Multipart uploads** are parsed by hand in `lab/web.py::_read_upload` (not `cgi`, which was removed in Python 3.13) — students' machines may run varying Python versions.

## API surface

`GET /api/status`, `/api/document?page=N`, `/api/chunks`
`POST /api/upload`, `/api/chunk`, `/api/embed`, `/api/search`, `/api/vector`, `/api/reset`

`/api/search` request body: `{query, k, answer, rerank, rewrite, documents}` (all but `query` optional). Response shape depends on `rerank`:
- off (default): `{"semantic": {...}, "bm25": {...}, "hybrid": {...}, ...}`, one `{"hits": [...]}` block per retrieval method, each optionally carrying its own `"answer"` when `answer: true` — every method's answer is generated from *that method's* chunks only, never a merged set.
- on: `{"rerank": {"candidates": [...10 hybrid hits...], "hits": [...top 5 reranked...], "latency": ..., "answer"?: {...}}, ...}` instead of the three method blocks.

When `rewrite: true`, the response also carries `{"rewrite": {"original", "rewritten", "latency"}}`. Retrieval and generation are intentionally separable in the UI so students see retrieved chunks before enabling answer generation.
