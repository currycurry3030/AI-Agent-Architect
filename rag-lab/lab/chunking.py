# -*- coding: utf-8 -*-
"""문서를 조각으로 자르는 세 가지 방식.

**오버랩은 쓰지 않는다.** 조각의 경계가 어디에 생겼는지가 그대로 보여야
청킹 전략을 비교할 수 있다.

  fixed      길이만 보고 자른다. 문서 사정을 모른다.
  structure  절 번호나 제목 줄을 경계로 삼는다. 구획이 뚜렷한 문서에서 산다.
  paragraph  빈 줄로 나뉜 문단을 최소 단위로 삼는다. 문단 중간을 자르지 않는다.
"""

import re

from . import config, parsing

# "2.2.1", "제10조", "Section 4", "4.1 Title" 같은 구획 시작 줄
_HEADING = re.compile(
    r"^\s*("
    r"\d+(\.\d+)+\.?\s+\S"                 # 2.2.1 제목
    r"|제\s*\d+\s*조"                       # 제10조
    r"|(Section|Chapter|Appendix)\s+\S"     # Section 4
    r"|\d+\.\s+[A-Z가-힣]"                  # 4. Title
    r")",
    re.IGNORECASE,
)


def _mk(text, start, pages, index, strategy):
    text = text.strip()
    return {
        "index": index,
        "text": text,
        "n_chars": len(text),
        "page": parsing.page_of(pages, start),
        "strategy": strategy,
    }


def _split_long(text, start, size):
    """상한을 넘는 덩어리를 길이로 다시 나눈다. (조각, 시작위치) 목록.

    마지막 꼬리가 너무 짧으면 앞 조각에 붙인다. `tations.` 처럼 단어 중간이
    잘린 8자짜리는 관찰거리가 아니라 그냥 쓰레기 조각이다.
    """
    out = []
    for i in range(0, len(text), size):
        out.append((text[i:i + size], start + i))
    if len(out) > 1 and len(out[-1][0].strip()) < size * 0.2:
        tail = out.pop()
        prev, prev_start = out[-1]
        out[-1] = (prev + tail[0], prev_start)
    return out


def _merge_short(blocks, size, floor_ratio=0.4):
    """연속된 짧은 덩어리를 상한까지 묶는다.

    구조 경계 전략은 목차 페이지에서 무너진다. `7.7. USB` 같은 항목이
    한 줄씩 끊겨 8~10자짜리 조각을 수백 개 만든다. 이웃끼리 묶어 준다.
    """
    floor = size * floor_ratio
    out = []
    for body, start in blocks:
        if out and len(body.strip()) < floor and len(out[-1][0]) + len(body) + 1 <= size:
            prev, prev_start = out[-1]
            out[-1] = (prev + "\n" + body, prev_start)
        else:
            out.append((body, start))
    return out


def chunk_fixed(doc, size):
    pages, text = doc["pages"], doc["text"]
    out = []
    for i in range(0, len(text), size):
        piece = text[i:i + size]
        if piece.strip():
            out.append(_mk(piece, i, pages, len(out), "fixed"))
    return out


def chunk_structure(doc, size):
    pages, text = doc["pages"], doc["text"]
    lines = text.split("\n")

    # 제목 줄에서 끊어 덩어리를 만든다
    blocks, cur, cur_start, pos = [], [], 0, 0
    for ln in lines:
        if _HEADING.match(ln) and cur:
            blocks.append(("\n".join(cur), cur_start))
            cur, cur_start = [], pos
        cur.append(ln)
        pos += len(ln) + 1
    if cur:
        blocks.append(("\n".join(cur), cur_start))

    blocks = _merge_short(blocks, size)

    out = []
    for body, start in blocks:
        if not body.strip():
            continue
        for piece, off in (_split_long(body, start, size) if len(body) > size
                           else [(body, start)]):
            if piece.strip():
                out.append(_mk(piece, off, pages, len(out), "structure"))
    return out


def chunk_paragraph(doc, size):
    pages, text = doc["pages"], doc["text"]

    # 빈 줄로 문단을 나누되 시작 위치를 함께 들고 간다
    paras, pos = [], 0
    for part in re.split(r"\n\s*\n", text):
        paras.append((part, pos))
        pos += len(part) + 2

    out, buf, buf_start = [], "", None
    for body, start in paras:
        if not body.strip():
            continue
        if len(body) > size:                          # 문단 하나가 상한을 넘으면
            if buf:
                out.append(_mk(buf, buf_start, pages, len(out), "paragraph"))
                buf, buf_start = "", None
            for piece, off in _split_long(body, start, size):
                if piece.strip():
                    out.append(_mk(piece, off, pages, len(out), "paragraph"))
            continue
        if buf and len(buf) + len(body) + 2 > size:   # 더 담으면 넘친다
            out.append(_mk(buf, buf_start, pages, len(out), "paragraph"))
            buf, buf_start = "", None
        if not buf:
            buf, buf_start = body, start
        else:
            buf += "\n\n" + body
    if buf:
        out.append(_mk(buf, buf_start, pages, len(out), "paragraph"))
    return out


_FN = {"fixed": chunk_fixed, "structure": chunk_structure, "paragraph": chunk_paragraph}


def chunk(doc, strategy, size=None):
    if strategy not in _FN:
        raise ValueError("모르는 전략: %s" % strategy)
    size = int(size or config.CHUNK_SIZE_DEFAULT)
    size = max(config.CHUNK_SIZE_MIN, min(config.CHUNK_SIZE_MAX, size))
    chunks = _FN[strategy](doc, size)
    for i, c in enumerate(chunks):             # 번호를 다시 매긴다
        c["index"] = i
    return chunks


def summarize(chunks):
    if not chunks:
        return {"count": 0, "min": 0, "max": 0, "avg": 0}
    sizes = [c["n_chars"] for c in chunks]
    return {
        "count": len(chunks),
        "min": min(sizes),
        "max": max(sizes),
        "avg": round(sum(sizes) / len(sizes)),
    }
