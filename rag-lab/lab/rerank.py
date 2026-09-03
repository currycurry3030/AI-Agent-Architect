# -*- coding: utf-8 -*-
"""LLM 재정렬 — 1차 후보를 질문과 함께 다시 순서 매긴다.

하이브리드가 순위로 후보를 추려도, 그 순위는 결국 벡터 거리·용어 빈도라는
대리 신호일 뿐이다. 재정렬은 후보 본문을 실제로 LLM 에게 읽혀 질문과
얼마나 관련 있는지 직접 판단시킨다.
"""

import re

from . import llm

PROMPT = """당신은 검색 결과를 다시 정렬하는 평가자입니다.
아래 후보 조각들이 질문에 답하는 데 얼마나 관련 있는지 판단해,
관련 있는 순서대로 후보 번호만 나열하세요. 관련 없는 후보는 제외해도 됩니다.
다른 설명 없이 번호만 쉼표로 구분해 답하세요. 예: 3, 1, 5

[질문] {question}

{candidates}"""


def _build_candidates(hits):
    return "\n\n".join(
        "[후보 %d] (%s · %s쪽)\n%s"
        % (i + 1, h.get("document", "?"), h.get("page", "?"), h.get("text", ""))
        for i, h in enumerate(hits))


def rerank(question, hits, top_n):
    """→ 관련도 순으로 재정렬한 히트 목록 (상위 top_n, 원래 순위도 함께 담는다)."""
    if not hits:
        return []
    prompt = PROMPT.format(question=question, candidates=_build_candidates(hits))
    text = llm.generate(prompt, max_tokens=120)
    order = [int(n) - 1 for n in re.findall(r"\d+", text)]

    picked = []
    for idx in order:
        if 0 <= idx < len(hits) and idx not in picked:
            picked.append(idx)
        if len(picked) >= top_n:
            break
    # 모델 응답을 못 읽었거나 개수가 모자라면 하이브리드 순서로 채운다
    for idx in range(len(hits)):
        if len(picked) >= top_n:
            break
        if idx not in picked:
            picked.append(idx)

    out = []
    for rank, idx in enumerate(picked, 1):
        h = hits[idx]
        out.append({**h, "rank": rank, "prior_rank": h.get("rank")})
    return out
