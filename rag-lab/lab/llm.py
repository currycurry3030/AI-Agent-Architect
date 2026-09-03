# -*- coding: utf-8 -*-
"""OpenAI 임베딩·생성 호출.

SDK 를 쓰지 않고 HTTP 로 직접 부른다. 무엇이 오가는지 코드에서 보이는 편이
수업에 낫다. 청크 원문이 외부로 전송되는 지점이 여기 한 곳뿐인 것도 중요하다.
"""

import json
import time
import urllib.error
import urllib.request

from . import config

BASE = "https://api.openai.com/v1"
TIMEOUT = 60


class LLMError(Exception):
    pass


# 모델이 temperature 를 거부하면(400) 그 뒤로는 보내지 않는다.
_STATE = {"temperature_ok": True}


def _explain(code, raw):
    """API 오류를 수강생이 읽을 수 있는 한 줄로 바꾼다.

    원문 JSON 을 그대로 띄우면 아무도 읽지 않는다. 자주 나오는 것만 골라
    무엇을 하면 되는지까지 적는다. 그 밖의 것은 원문을 짧게 붙인다.
    """
    try:
        msg = json.loads(raw)["error"]["message"]
    except Exception:                          # noqa: BLE001
        msg = raw[:160]
    if code == 401:
        return "API 키가 유효하지 않습니다. .env 파일의 OPENAI_API_KEY 를 확인하세요."
    if code == 403:
        return "이 키로는 호출할 수 없습니다. 발급한 프로젝트와 허용 모델을 확인하세요."
    if code == 429:
        if "quota" in msg.lower() or "billing" in msg.lower():
            return "이 키의 사용 한도(잔액)가 소진되었습니다. 보조강사를 불러 주세요."
        return "호출 한도에 걸렸습니다. 1~2분 뒤에 다시 시도하세요."
    if code >= 500:
        return "OpenAI 쪽 일시적인 오류입니다(%d). 잠시 뒤 다시 시도하세요." % code
    return "요청이 거절되었습니다(%d) — %s" % (code, msg)


def _post(path, payload, retries=2):
    key = config.api_key()
    if not key:
        raise LLMError("OPENAI_API_KEY 가 없습니다. .env 파일을 확인하세요.")
    url = "%s/%s" % (BASE, path)
    body = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer %s" % key)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            last = LLMError(_explain(e.code, raw))
            # 429(한도)와 5xx 는 잠깐 쉬고 다시
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last
        except (urllib.error.URLError, OSError) as e:
            # 연결 실패(URLError)와 응답 대기 중 끊김(TimeoutError) 둘 다 여기로 온다.
            last = LLMError("네트워크 실패 — %s" % (getattr(e, "reason", None) or e.__class__.__name__))
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last
    raise last


def embed_many(texts, on_progress=None):
    """여러 문장 → 여러 벡터. 배치로 나눠 부른다.

    질문과 문서를 같은 모델·같은 설정으로 임베딩한다. 이 모델에는 문서용·질문용 구분이 없다.
    """
    out = []
    total = len(texts)
    for i in range(0, total, config.EMBED_BATCH):
        batch = texts[i:i + config.EMBED_BATCH]
        res = _post("embeddings", {
            "model": config.EMBED_MODEL,
            "input": [t if t.strip() else " " for t in batch],   # 빈 문자열은 거절된다
            "dimensions": config.EMBED_DIM,
            "encoding_format": "float",
        })
        rows = sorted(res["data"], key=lambda d: d["index"])
        out += [d["embedding"] for d in rows]
        if on_progress:
            on_progress(min(i + len(batch), total), total)
    return out


def embed_one(text):
    """문장 하나 → 벡터 하나."""
    return embed_many([text])[0]


def generate(prompt, max_tokens=None):
    """프롬프트 하나 → 답변 문자열. RAG 의 마지막 단계인 생성에 쓴다."""
    payload = {
        "model": config.GEN_MODEL,
        "input": prompt,
        "max_output_tokens": max_tokens or config.GEN_MAX_TOKENS,
        "reasoning": {"effort": "none"},   # 추론 토큰 없이 곧바로 답한다
        "store": False,
    }
    if _STATE["temperature_ok"]:
        payload["temperature"] = 0
    try:
        res = _post("responses", payload)
    except LLMError as exc:
        if "temperature" in payload and "temperature" in str(exc):
            _STATE["temperature_ok"] = False
            payload.pop("temperature", None)
            res = _post("responses", payload)
        else:
            raise

    texts = []
    for item in res.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    text = "".join(texts).strip()
    if not text:
        reason = (res.get("incomplete_details") or {}).get("reason") or res.get("status", "이유 불명")
        raise LLMError("답변이 비어 있습니다 (%s). 다시 시도해 보세요." % reason)
    return text
