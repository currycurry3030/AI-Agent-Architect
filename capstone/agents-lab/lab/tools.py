# -*- coding: utf-8 -*-
"""이 앱이 AI 에게 건네주는 내장 도구 — 가상 공정 로그 CSV 하나를 분석한다.

Process Detective: LLM 이 원인을 추측하는 것이 아니라, LLM 이 필요한 분석 도구를
고르고 그 도구가 실제로 계산한 값을 근거로 원인 후보를 정리한다.

설명문은 화면에서 고칠 수 있다. 여기 적힌 것은 기본값이며,
화면에서 고친 값은 state/tool_overrides.json 에 저장되어 이 값 위에 덮인다.
"""

import csv
import os
import statistics

from . import config

NUMERIC_FIELDS = ("pressure", "temperature", "gas_flow", "rf_power",
                   "etch_time", "cd", "defect_rate", "yield")
GROUP_FIELDS = ("equipment", "lot_id", "wafer_id")


# ── 공정 로그 읽기 ────────────────────────────────────────────────────

def _load():
    path = config.process_log_path()
    if not os.path.exists(path):
        raise IOError("공정 로그 파일을 찾을 수 없습니다: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for field in NUMERIC_FIELDS:
            try:
                row[field] = float(row[field])
            except (KeyError, ValueError, TypeError):
                row[field] = None
    return rows


def _in_range(row, start_date, end_date):
    date = row["timestamp"][:10]
    if start_date and date < start_date:
        return False
    if end_date and date > end_date:
        return False
    return True


def _filter(rows, start_date=None, end_date=None, equipment=None):
    out = rows
    if start_date or end_date:
        out = [r for r in out if _in_range(r, start_date, end_date)]
    if equipment:
        out = [r for r in out if r.get("equipment") == equipment]
    return out


def _dates(rows):
    return sorted({r["timestamp"][:10] for r in rows})


def read_recent(limit=20):
    """화면에 최근 로그를 보여주기 위한 것. AI 에게 주는 도구가 아니다."""
    try:
        rows = _load()
    except (IOError, ValueError):
        return []
    tail = rows[-limit:]
    out = []
    for r in reversed(tail):
        out.append({
            "title": "%s · %s" % (r["timestamp"], r["equipment"]),
            "body": "pressure=%.1f  temperature=%.1f  defect_rate=%.2f%%  yield=%.1f%%"
                    % (r["pressure"], r["temperature"], r["defect_rate"], r["yield"]),
        })
    return out


def reset_process_log():
    """seed 원본으로 되돌린다. 화면의 초기화 버튼이 부른다."""
    with open(config.SEED_PROCESS_LOG_PATH, "r", encoding="utf-8") as f:
        seed_text = f.read()
    os.makedirs(os.path.dirname(config.PROCESS_LOG_PATH), exist_ok=True)
    with open(config.PROCESS_LOG_PATH, "w", encoding="utf-8") as f:
        f.write(seed_text)
    if os.path.exists(config.DATA_PATH_OVERRIDE):
        os.remove(config.DATA_PATH_OVERRIDE)
    with open(config.PROCESS_LOG_PATH, "r", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


# ── 도구 함수 ─────────────────────────────────────────────────────────

def compare_period(target_start="", target_end="", baseline_start="", baseline_end="",
                    equipment=""):
    """두 기간의 변수 평균을 비교한다.

    target_* 를 비우면 데이터의 마지막 7일을 target 으로 쓰고, baseline_* 를 비우면
    target 이전 구간 전체를 baseline 으로 쓴다 — "최근에 무엇이 바뀌었나" 질문에
    바로 답할 수 있게 하기 위해서다.
    """
    rows = _load()
    if not rows:
        return {"오류": "데이터가 없습니다."}
    all_dates = _dates(rows)

    if not target_start and not target_end:
        cutoff = all_dates[max(0, len(all_dates) - 7)]
        target_start, target_end = cutoff, all_dates[-1]
    if not baseline_start and not baseline_end:
        baseline_end_idx = all_dates.index(target_start) - 1
        if baseline_end_idx < 0:
            return {"오류": "baseline 으로 쓸 이전 기간이 없습니다. baseline_start/end 를 직접 지정하세요."}
        baseline_start, baseline_end = all_dates[0], all_dates[baseline_end_idx]

    base_rows = _filter(rows, baseline_start, baseline_end, equipment or None)
    tgt_rows = _filter(rows, target_start, target_end, equipment or None)
    if not base_rows or not tgt_rows:
        return {"오류": "지정한 기간에 데이터가 없습니다.",
                "가능한 날짜 범위": [all_dates[0], all_dates[-1]]}

    diffs = {}
    for field in NUMERIC_FIELDS:
        b = statistics.mean(r[field] for r in base_rows)
        t = statistics.mean(r[field] for r in tgt_rows)
        diffs[field] = {
            "baseline_평균": round(b, 3),
            "target_평균": round(t, 3),
            "변화량": round(t - b, 3),
            "변화율(%)": round((t - b) / b * 100, 2) if b else None,
        }

    return {
        "baseline 기간": [baseline_start, baseline_end],
        "target 기간": [target_start, target_end],
        "baseline 건수": len(base_rows),
        "target 건수": len(tgt_rows),
        "변수별 비교": diffs,
    }


def find_outliers(by="equipment", metric="defect_rate", top_n=5,
                   start_date="", end_date=""):
    """장비·LOT·wafer 중 어디에 이상이 몰려 있는지 찾는다.

    by 로 묶은 그룹별 metric 평균을 전체 평균·표준편차와 비교해, 표준편차의 1배를
    넘게 벗어난 그룹을 이상 후보로 표시한다.
    """
    if by not in GROUP_FIELDS:
        return {"오류": "by 는 equipment, lot_id, wafer_id 중 하나여야 합니다."}
    if metric not in NUMERIC_FIELDS:
        return {"오류": "metric 이 올바르지 않습니다.", "허용값": list(NUMERIC_FIELDS)}

    rows = _filter(_load(), start_date or None, end_date or None)
    if not rows:
        return {"오류": "지정한 기간에 데이터가 없습니다."}

    overall = [r[metric] for r in rows]
    overall_mean = statistics.mean(overall)
    overall_std = statistics.pstdev(overall) or 1e-9

    groups = {}
    for r in rows:
        groups.setdefault(r[by], []).append(r[metric])

    ranked = []
    for key, values in groups.items():
        m = statistics.mean(values)
        se = overall_std / (len(values) ** 0.5)          # 그룹 평균의 표준오차
        z = (m - overall_mean) / se if se else 0.0
        ranked.append({
            "group": key,
            "건수": len(values),
            "%s_평균" % metric: round(m, 3),
            "전체평균과의_편차(z-score)": round(z, 2),
            "이상_후보": abs(z) >= 2.0,
        })
    ranked.sort(key=lambda x: abs(x["전체평균과의_편차(z-score)"]), reverse=True)

    return {
        "기준 변수": metric,
        "그룹 기준": by,
        "전체 평균": round(overall_mean, 3),
        "전체 표준편차": round(overall_std, 3),
        "상위 그룹": ranked[:top_n],
    }


def rank_features(target="yield", top_n=5, start_date="", end_date=""):
    """target 과 상관관계가 큰 변수를 순위로 매긴다 (Pearson 상관계수).

    상관관계이지 인과관계가 아니다 — 결과 해석 시 유의해야 한다.
    """
    if target not in NUMERIC_FIELDS:
        return {"오류": "target 이 올바르지 않습니다.", "허용값": list(NUMERIC_FIELDS)}

    rows = _filter(_load(), start_date or None, end_date or None)
    if len(rows) < 3:
        return {"오류": "상관계수를 계산하기에 데이터가 부족합니다."}

    target_values = [r[target] for r in rows]
    ranked = []
    for field in NUMERIC_FIELDS:
        if field == target:
            continue
        values = [r[field] for r in rows]
        try:
            corr = statistics.correlation(values, target_values)
        except statistics.StatisticsError:
            continue
        ranked.append({"변수": field, "상관계수": round(corr, 3)})
    ranked.sort(key=lambda x: abs(x["상관계수"]), reverse=True)

    return {
        "target": target,
        "표본 수": len(rows),
        "순위": ranked[:top_n],
        "주의": "상관관계이며 인과관계를 의미하지 않습니다.",
    }


def plot_trend(metric="pressure", start_date="", end_date="", equipment=""):
    """변수의 일별 추이를 계산하고, 기준 구간(맨 앞 7일) 대비 언제부터 벗어났는지 찾는다.

    화면에는 그래프 대신 날짜별 평균값 표를 그대로 보여준다.
    """
    if metric not in NUMERIC_FIELDS:
        return {"오류": "metric 이 올바르지 않습니다.", "허용값": list(NUMERIC_FIELDS)}

    rows = _filter(_load(), start_date or None, end_date or None, equipment or None)
    if not rows:
        return {"오류": "지정한 기간에 데이터가 없습니다."}

    by_date = {}
    for r in rows:
        by_date.setdefault(r["timestamp"][:10], []).append(r[metric])
    dates = sorted(by_date)

    daily = []
    for d in dates:
        values = by_date[d]
        daily.append({
            "date": d,
            "평균": round(statistics.mean(values), 3),
            "표준편차": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0,
            "최소": round(min(values), 3),
            "최대": round(max(values), 3),
            "건수": len(values),
        })

    baseline_window = daily[:min(7, len(daily))]
    baseline_mean = statistics.mean(d["평균"] for d in baseline_window)
    baseline_std = statistics.pstdev(d["평균"] for d in baseline_window) if len(baseline_window) > 1 else 0.0
    threshold = max(baseline_std * 3.0, abs(baseline_mean) * 0.02, 1e-6)

    # 하루만 튄 값이 아니라 이후 며칠도 계속 벗어나 있어야 "바뀌었다"고 본다.
    changed_since = None
    for idx, d in enumerate(daily):
        following = daily[idx:idx + 3]
        if len(following) < 2:
            break
        if all(abs(f["평균"] - baseline_mean) > threshold for f in following):
            changed_since = d["date"]
            break

    return {
        "변수": metric,
        "기준(맨 앞 %d일) 평균" % len(baseline_window): round(baseline_mean, 3),
        "벗어났다고 판단하는 날짜": changed_since,
        "일별 추이": daily,
    }


# ── 도구 목록 ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "compare_period",
        "description": (
            "두 기간(baseline vs target)의 공정 변수 평균을 비교한다. "
            "\"수율이 낮아진 전후에 무엇이 변했어?\" 처럼 기간 전후 변화를 물을 때 쓴다. "
            "target_start/target_end 를 비우면 최근 7일을, baseline_start/baseline_end 를 "
            "비우면 그 이전 전체 기간을 자동으로 쓴다. 날짜는 YYYY-MM-DD. "
            "특정 장비만 보려면 equipment 에 EQP_X 또는 EQP_Y 를 넣는다. "
            "장비·LOT·wafer 중 어디에 이상이 몰렸는지는 find_outliers 를 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_start": {"type": "string", "description": "비교 대상 기간 시작일 YYYY-MM-DD (비우면 최근 7일)"},
                "target_end": {"type": "string", "description": "비교 대상 기간 종료일 YYYY-MM-DD (비우면 최근 7일)"},
                "baseline_start": {"type": "string", "description": "기준 기간 시작일 YYYY-MM-DD (비우면 target 이전 전체)"},
                "baseline_end": {"type": "string", "description": "기준 기간 종료일 YYYY-MM-DD (비우면 target 이전 전체)"},
                "equipment": {"type": "string", "description": "특정 장비만 볼 때 EQP_X 또는 EQP_Y. 비우면 전체."},
            },
            "required": [],
        },
        "function": compare_period,
    },
    {
        "name": "find_outliers",
        "description": (
            "equipment · lot_id · wafer_id 중 하나로 묶어, 어느 그룹에 이상이 몰려 있는지 찾는다. "
            "\"특정 장비에 문제가 몰려 있어?\", \"이상 LOT를 찾아줘\" 처럼 특정 대상을 지목하는 "
            "질문에 쓴다. 기간 전후 평균 변화를 보려면 compare_period, 어떤 변수가 결과와 "
            "관련이 큰지 보려면 rank_features 를 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "by": {"type": "string", "description": "묶을 기준: equipment, lot_id, wafer_id 중 하나 (기본 equipment)"},
                "metric": {"type": "string", "description": "비교할 변수 (기본 defect_rate)"},
                "top_n": {"type": "integer", "description": "상위 몇 개를 보여줄지 (기본 5)"},
                "start_date": {"type": "string", "description": "조회 시작일 YYYY-MM-DD. 비우면 전체 기간."},
                "end_date": {"type": "string", "description": "조회 종료일 YYYY-MM-DD. 비우면 전체 기간."},
            },
            "required": [],
        },
        "function": find_outliers,
    },
    {
        "name": "rank_features",
        "description": (
            "target 변수(기본 yield)와 상관관계가 큰 다른 변수를 순위로 매긴다. "
            "\"수율과 관련이 큰 변수는 무엇이야?\" 처럼 원인이 될 만한 변수를 좁힐 때 쓴다. "
            "상관관계일 뿐 인과관계를 확정하지 않는다. 기간별 실제 변화량을 보려면 "
            "compare_period 를 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "기준이 될 변수 (기본 yield)"},
                "top_n": {"type": "integer", "description": "상위 몇 개를 보여줄지 (기본 5)"},
                "start_date": {"type": "string", "description": "조회 시작일 YYYY-MM-DD. 비우면 전체 기간."},
                "end_date": {"type": "string", "description": "조회 종료일 YYYY-MM-DD. 비우면 전체 기간."},
            },
            "required": [],
        },
        "function": rank_features,
    },
    {
        "name": "plot_trend",
        "description": (
            "한 변수의 날짜별 평균 추이를 계산하고, 맨 앞 7일을 기준으로 언제부터 벗어났는지 "
            "찾는다. \"Pressure가 언제부터 변했어?\", \"시간 추이를 보여줘\" 처럼 시점을 묻는 "
            "질문에 쓴다. 특정 장비만 보려면 equipment 를 넣는다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "추이를 볼 변수 (필수, 예: pressure)"},
                "start_date": {"type": "string", "description": "조회 시작일 YYYY-MM-DD. 비우면 전체 기간."},
                "end_date": {"type": "string", "description": "조회 종료일 YYYY-MM-DD. 비우면 전체 기간."},
                "equipment": {"type": "string", "description": "특정 장비만 볼 때 EQP_X 또는 EQP_Y. 비우면 전체."},
            },
            "required": ["metric"],
        },
        "function": plot_trend,
    },
]
