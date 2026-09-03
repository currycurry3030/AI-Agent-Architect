# -*- coding: utf-8 -*-
"""LLM 이 만든 파이썬 코드를 통제된 조건에서 실행한다.

사양이 다른 여러 PC 에서 돌아가므로 다음 셋을 반드시 지킨다.
  · **시간 제한** — 무한 루프를 끊는다
  · **라이브러리 제한** — 표준 라이브러리 중에서도 정한 것만 허용한다
  · **오류를 그대로 돌려준다** — 에이전트가 고쳐서 다시 시도할 수 있어야 한다

실패 처리는 폐기할 수 없다. 코드가 안 돌면 결과물이 없다.
"""

import ast
import os
import subprocess
import sys
import tempfile

from . import config


def check_imports(code):
    """허용 목록 밖의 import 를 찾는다. 문법 오류면 그 사실을 돌려준다."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return "문법 오류입니다 (%d행): %s" % (exc.lineno or 0, exc.msg)

    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            head = name.split(".")[0]
            if head and head not in config.PY_ALLOWED_IMPORTS:
                return ("%s 는 쓸 수 없습니다. 허용된 것은 %s 입니다."
                        % (head, ", ".join(config.PY_ALLOWED_IMPORTS)))
    return None


def run(code, cwd=None):
    """코드를 실행하고 {"ok", "output", "error"} 를 돌려준다."""
    code = (code or "").strip()
    if not code:
        return {"ok": False, "output": "", "error": "실행할 코드가 비어 있습니다."}

    blocked = check_imports(code)
    if blocked:
        return {"ok": False, "output": "", "error": blocked}

    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=".py", prefix="agentlab_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("OPENAI_API_KEY", None)          # 자식 코드에 키를 물려주지 않는다

        proc = subprocess.run(
            [sys.executable, path],
            cwd=cwd or config.ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=config.PY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "",
                "error": "%d초 안에 끝나지 않아 중단했습니다. 시행 횟수를 줄이거나 계산을 가볍게 해서 "
                         "다시 시도하세요." % config.PY_TIMEOUT}
    except OSError as exc:
        return {"ok": False, "output": "", "error": "실행하지 못했습니다: %s" % exc}
    finally:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    out = proc.stdout.decode("utf-8", "replace")[:config.PY_MAX_OUTPUT]
    err = proc.stderr.decode("utf-8", "replace")[-1200:]
    if proc.returncode != 0:
        return {"ok": False, "output": out, "error": err.strip() or "실행이 실패했습니다."}
    if not out.strip():
        return {"ok": True, "output": "",
                "error": "코드는 돌았지만 아무것도 출력하지 않았습니다. print 로 결과를 찍으세요."}
    return {"ok": True, "output": out, "error": ""}


# ── 도구로 내보내는 형태 ──────────────────────────────────────────────

def tool_run_python(code=""):
    result = run(code)
    if result["ok"] and not result["error"]:
        return {"출력": result["output"]}
    if result["ok"]:
        return {"출력": result["output"], "알림": result["error"]}
    return {"오류": result["error"], "출력": result["output"]}


TOOL = {
    "name": "run_python",
    "description": ("파이썬 코드를 실행하고 표준 출력을 돌려준다. 계산·시뮬레이션에 쓴다. "
                    "결과는 반드시 print 로 찍어야 보인다. "
                    "표준 라이브러리(math, random, statistics, csv, json 등)만 쓸 수 있다. numpy 는 없다. "
                    "실행 시간은 %d초로 제한된다. 순수 파이썬이므로 반복 횟수는 수만 회 안쪽으로 잡는다. "
                    "자료 파일은 read_data_file 로 먼저 읽는다. 그 결과가 알려주는 경로를 쓰면 "
                    "코드에서도 열 수 있다. 파일 이름만으로는 열리지 않는다." % config.PY_TIMEOUT),
    "parameters": {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "실행할 파이썬 코드"}},
        "required": ["code"],
    },
    "function": tool_run_python,
    "source": "내장",
}
