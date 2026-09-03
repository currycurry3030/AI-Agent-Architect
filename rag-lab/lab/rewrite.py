# -*- coding: utf-8 -*-
"""질의 재작성 — 사용자가 입력한 질문을 검색에 맞는 형태로 다듬는다.

구어체거나 대명사가 섞인 질문은 임베딩·BM25 모두에서 손해를 본다. LLM 에게
검색 엔진에 넣기 좋은 형태로 한 번 고쳐 쓰게 한 뒤, 그 결과로 검색한다.
"""

from . import llm

PROMPT = """다음 질문을 문서 검색에 적합한 형태로 다시 쓰세요.
핵심 키워드는 유지하고, 불필요한 대화체 표현이나 대명사는 정리하세요.
다른 설명 없이 다시 쓴 질문 한 줄만 답하세요.

[원래 질문] {question}"""


def rewrite(question):
    prompt = PROMPT.format(question=question)
    text = llm.generate(prompt, max_tokens=120)
    return text.strip().strip('"').strip("'")
