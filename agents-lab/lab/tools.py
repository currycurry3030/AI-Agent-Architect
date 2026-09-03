# -*- coding: utf-8 -*-
"""이 앱이 AI 에게 건네주는 내장 도구 — 메모 파일 하나를 검색·저장·삭제한다.

파라미터는 셋 다 `text` 하나로 통일했고, 이름은 `memo_tool_1/2/3` 이다.
설명문은 화면에서 고칠 수 있다. 여기 적힌 것은 기본값이며,
화면에서 고친 값은 state/tool_overrides.json 에 저장되어 이 값 위에 덮인다.
"""

import json
import os

from . import config


# ── 메모 파일 읽고 쓰기 ───────────────────────────────────────────────

def _load():
    path = config.notes_path()
    if not os.path.exists(path):
        raise IOError("메모 파일을 찾을 수 없습니다: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(notes):
    path = config.notes_path()
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        raise IOError("저장할 폴더가 없습니다: %s" % directory)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _matches(note, text):
    """낱말 단위 일치. "회의 메모" 처럼 두 낱말이 와도 "회의" 가 든 메모가 잡힌다.

    부분 문자열 일치("회의 메모" in "주간 회의 정리")로 두면 0건이 된다.
    """
    words = (text or "").split()
    if not words:
        return True
    hay = note.get("title", "") + " " + note.get("body", "")
    return any(w in hay for w in words)


def read_notes():
    """화면에 메모 목록을 보여주기 위한 것. AI 에게 주는 도구가 아니다."""
    try:
        return _load()
    except (IOError, ValueError):
        return []


def reset_notes():
    """seed 원본으로 되돌린다. 화면의 초기화 버튼이 부른다."""
    with open(config.SEED_NOTES_PATH, "r", encoding="utf-8") as f:
        seed = json.load(f)
    os.makedirs(os.path.dirname(config.NOTES_PATH), exist_ok=True)
    with open(config.NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if os.path.exists(config.DATA_PATH_OVERRIDE):
        os.remove(config.DATA_PATH_OVERRIDE)
    return len(seed)


# ── 도구 함수 ─────────────────────────────────────────────────────────

def note_search(text=""):
    notes = _load()
    found = [n for n in notes if _matches(n, text)]
    return {
        "찾은 메모": [{"제목": n.get("title", ""), "내용": n.get("body", ""),
                    "날짜": n.get("date", "")} for n in found],
        "찾은 건수": len(found),
    }


def note_save(text=""):
    body = (text or "").strip()
    if not body:
        return {"오류": "저장할 내용이 비어 있습니다."}
    notes = _load()
    title = body.split("\n")[0][:30]
    notes.append({"title": title, "body": body, "date": ""})
    _save(notes)
    return {"저장한 제목": title, "전체 건수": len(notes)}


def note_delete(text=""):
    notes = _load()
    hit = [n for n in notes if _matches(n, text)]
    kept = [n for n in notes if not _matches(n, text)]
    _save(kept)
    return {"지운 메모": [n.get("title", "") for n in hit],
            "지운 건수": len(hit), "남은 건수": len(kept)}


def note_replace(text=""):
    """text 첫 줄은 키워드, 둘째 줄부터는 새 내용 — 다른 도구처럼 인자를 text 하나로 두려면
    이렇게 한 문자열 안에서 나눠 받는 수밖에 없다."""
    lines = (text or "").split("\n", 1)
    keyword = lines[0].strip()
    new_body = lines[1].strip() if len(lines) > 1 else ""
    if not keyword or not new_body:
        return {"오류": "인자 형식이 올바르지 않습니다. 첫 줄에 키워드, 둘째 줄부터 새 내용을"
                       " 적어 주세요. 예: \"회의실 예약\\n3층 대회의실은 이틀 전까지 신청한다.\""}
    notes = _load()
    hit = [n for n in notes if _matches(n, keyword)]
    for n in hit:
        n["body"] = new_body
    _save(notes)
    return {"바꾼 메모": [n.get("title", "") for n in hit], "바꾼 건수": len(hit)}


# ── 도구 목록 ─────────────────────────────────────────────────────────
# parameters 는 셋 다 동일하다.

_TEXT_PARAM = {
    "type": "object",
    "properties": {"text": {"type": "string", "description": "입력 문자열"}},
    "required": ["text"],
}

TOOLS = [
    {
        "name": "memo_tool_1",
        "description": "저장된 메모 중 키워드에 해당하는 것을 찾아 목록으로 보여준다.",
        "parameters": _TEXT_PARAM,
        "function": note_search,
    },
    {
        "name": "memo_tool_2",
        "description": "새 메모를 저장한다.",
        "parameters": _TEXT_PARAM,
        "function": note_save,
    },
    {
        "name": "memo_tool_3",
        "description": "키워드에 해당하는 메모를 삭제한다. 되돌릴 수 없다.",
        "parameters": _TEXT_PARAM,
        "function": note_delete,
    },
    {
        "name": "memo_tool_4",
        "description": "키워드에 해당하는 메모를 찾아 내용을 새 내용으로 바꾼다. "
                       "입력은 첫 줄에 키워드, 둘째 줄부터 새 내용을 적는다.",
        "parameters": _TEXT_PARAM,
        "function": note_replace,
    },
]
