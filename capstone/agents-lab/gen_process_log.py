# -*- coding: utf-8 -*-
"""가상 공정 로그 CSV 생성기. 표준 라이브러리만 사용 (random, csv, datetime).

2026-08-01 ~ 2026-08-30, 장비 2대(EQP_X, EQP_Y), 하루 8회 측정.
2026-08-20부터 pressure 상승 + temperature 변동성 증가 + EQP_Y 의 defect_rate 급증을 심는다.

재실행하면 data/process/process_log.csv 와 data/seed/process_log.csv 를 둘 다 새로 만든다
(고정 시드라 매번 같은 값이 나온다). 화면의 "데이터 초기화" 버튼은 seed 를 process 로
복사할 뿐이므로, 데이터 자체를 다시 만들고 싶을 때만 이 스크립트를 쓴다.
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATHS = [
    os.path.join(ROOT, "data", "process", "process_log.csv"),
    os.path.join(ROOT, "data", "seed", "process_log.csv"),
]

EQUIPMENTS = ["EQP_X", "EQP_Y"]
READINGS_PER_DAY = 8
DAYS = 30
ONSET_DAY = 20            # 이 날부터 이상 시작 (1-indexed)
RAMP_DAYS = 3              # 20,21,22 에 걸쳐 서서히 심해짐

START = datetime(2026, 8, 1)

rows = []
wafer_seq = 0

for day in range(1, DAYS + 1):
    date = START + timedelta(days=day - 1)
    ramp = 0.0 if day < ONSET_DAY else min(1.0, (day - (ONSET_DAY - 1)) / RAMP_DAYS)

    for equip in EQUIPMENTS:
        lot_id = "LOT_%s%02d" % (equip[-1], day)   # LOT_X01, LOT_Y01 ...

        for i in range(READINGS_PER_DAY):
            wafer_seq += 1
            wafer_id = "WF_%04d" % wafer_seq
            ts = date + timedelta(hours=i * 3)

            pressure = random.gauss(100 + 12 * ramp, 1.5)
            temperature = random.gauss(220, 1.0 + 2.0 * ramp)
            gas_flow = random.gauss(50, 2.0)
            rf_power = random.gauss(1200, 20.0)
            etch_time = random.gauss(60, 1.5)
            cd = random.gauss(45, 0.4 + 0.3 * ramp)

            if equip == "EQP_Y":
                defect_rate = max(0.0, random.gauss(1.5 + 4.0 * ramp, 0.3 + 0.4 * ramp))
            else:
                defect_rate = max(0.0, random.gauss(1.5 + 1.0 * ramp, 0.3 + 0.1 * ramp))

            yield_ = 98.5 - defect_rate * 1.5 - max(0.0, pressure - 100) * 0.2 \
                + random.gauss(0, 0.5)
            yield_ = max(75.0, min(99.5, yield_))

            rows.append({
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "lot_id": lot_id,
                "wafer_id": wafer_id,
                "equipment": equip,
                "pressure": round(pressure, 2),
                "temperature": round(temperature, 2),
                "gas_flow": round(gas_flow, 2),
                "rf_power": round(rf_power, 1),
                "etch_time": round(etch_time, 2),
                "cd": round(cd, 3),
                "defect_rate": round(defect_rate, 3),
                "yield": round(yield_, 2),
            })

fieldnames = ["timestamp", "lot_id", "wafer_id", "equipment", "pressure", "temperature",
              "gas_flow", "rf_power", "etch_time", "cd", "defect_rate", "yield"]

for path in OUT_PATHS:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

print("rows: %d, written to: %s" % (len(rows), ", ".join(OUT_PATHS)))
