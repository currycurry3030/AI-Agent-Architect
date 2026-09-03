# -*- coding: utf-8 -*-
"""rag-lab 설정값.

여기 있는 값은 수업 중에 바꾸지 않는다. 바꾸는 것은 화면에서 고르는
청킹 전략과 K 뿐이다.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 경로 ────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(ROOT, "data")          # 업로드한 PDF
STORE_DIR = os.path.join(ROOT, "chroma_db")    # 벡터 저장소
STATIC_DIR = os.path.join(ROOT, "static")

# ── 서버 ────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8765

# ── 모델 ────────────────────────────────────────────────────────────
# 질문과 문서를 같은 모델로 임베딩한다. 차원은 dimensions 로 줄일 수 있다(기본 1536).
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
EMBED_BATCH = 100

# 답을 만드는 모델. 검색이 꺼내 온 조각을 근거로 문장을 쓴다.
# 교육업체가 허용한 모델 안에서 강사가 확정 (2026-08-31).
GEN_MODEL = "gpt-5.6-luna"
GEN_MAX_TOKENS = 1024

COLLECTION = "rag_lab"

# ── 청킹 ────────────────────────────────────────────────────────────
# 오버랩은 쓰지 않는다. 조각의 경계가 어디서 생기는지 그대로 보여야 한다.
CHUNK_SIZE_DEFAULT = 500
CHUNK_SIZE_MIN = 100
CHUNK_SIZE_MAX = 2000

STRATEGIES = {
    "fixed": "고정 길이",
    "structure": "구조 경계",
    "paragraph": "문단",
}

# ── 검색 ────────────────────────────────────────────────────────────
TOP_K_DEFAULT = 5
TOP_K_MAX = 20

# ── 재정렬 ──────────────────────────────────────────────────────────
# 1차로 하이브리드 후보를 이만큼 꺼내 LLM 에게 다시 순서를 매기게 하고,
# 그중 상위 이만큼만 답변 생성의 근거로 쓴다.
RERANK_CANDIDATES = 10
RERANK_TOP_N = 5


def api_key():
    """.env 또는 환경변수에서 OpenAI API 키를 읽는다."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    path = os.path.join(ROOT, ".env")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == "OPENAI_API_KEY":
                    return v.strip().strip("'\"")
    return ""
