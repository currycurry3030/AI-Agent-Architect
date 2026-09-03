# Process Detective 캡스톤 세션 정리

작성일: 2026-09-03  
참고 자료: `AI-Agent-워크북(1).html`  
주제: AI Agent 교육 캡스톤 주제 선정 및 구현 범위 확정

---

## 1. 세션 목표

AI Agent 교육 워크북의 캡스톤 조건과 기존 업무 경험을 함께 고려하여, 100분 안에 실제로 완주할 수 있는 캡스톤 주제를 선정한다.

선정 시 고려한 기준은 다음과 같다.

- 100분 안에 정상 동작하는 결과물을 완성할 수 있는가?
- 교육에서 배운 Agent 및 Tool Calling 개념이 명확히 드러나는가?
- 반도체 공정 및 데이터 분석 업무와 연결되는가?
- 발표 시 동작 원리와 개선 과정을 쉽게 설명할 수 있는가?
- 실제 사내 데이터 없이도 구현할 수 있는가?
- 기능을 작게 시작한 뒤 시간이 남으면 확장할 수 있는가?

워크북의 핵심 방향은 큰 시스템을 절반만 만드는 것보다 작은 기능 하나를 끝까지 완주하는 것이다.

---

## 2. 검토한 캡스톤 후보

### 후보 1. 공정 이상 원인 분석 Agent

가상의 공정 데이터를 기반으로 사용자의 자연어 질문을 해석하고, 필요한 분석 도구를 선택·실행한 뒤 이상 원인 후보를 정리하는 Agent다.

예시 질문:

> 최근 품질 지표가 나빠진 원인을 분석해줘.

예상 실행 흐름:

1. 정상기간과 이상기간 비교
2. 주요 공정 변수 변화 확인
3. 이상 LOT·wafer·equipment 탐색
4. 품질 지표와 관련된 변수 순위 계산
5. 데이터 근거와 함께 원인 후보 정리

장점:

- Tool Calling의 핵심을 직접 시연할 수 있다.
- 기존 공정 및 데이터 분석 경험을 활용할 수 있다.
- 질문 → 도구 선택 → 실제 계산 → 근거 기반 결론의 흐름이 명확하다.
- 가상 CSV만으로 구현할 수 있어 보안 부담이 낮다.
- Tool description 수정 전후를 평가하여 개선 과정을 수치로 보여줄 수 있다.

주의점:

- 상관관계를 실제 인과관계로 표현하지 않는다.
- 원인 확정이 아니라 데이터상 연관성이 높은 원인 후보로 표현한다.
- 확률처럼 보이는 임의의 신뢰도 수치를 사용하지 않는다.

### 후보 2. 공정 변경 Risk Simulation Agent

가상의 공정 전환 조건을 입력받아 목표 품질 또는 수율에 도달하는 기간과 실패 위험을 Monte Carlo 방식으로 추정하는 Agent다.

예시 질문:

> 공정 A에서 B로 전환할 때 목표 수율 달성까지 걸리는 기간과 주요 리스크를 분석해줘.

가능한 역할 구성:

- Researcher: 변수 의미 및 계산 가정 조사
- Simulator: CSV 로딩, Monte Carlo, percentile 및 sensitivity 계산
- Manager: 결과 취합 및 최종 판단

예상 결과:

- 목표 달성 기간의 median, P05, P95
- 목표 실패 확률
- 결과에 큰 영향을 주는 변수 순위
- 조건 변경 전후의 결과 비교

장점:

- 조사 리포트 트랙과 잘 맞는다.
- 수치 분석과 Multi-Agent 구조를 보여주기 좋다.
- 교육 내용을 폭넓게 활용했다는 인상을 줄 수 있다.

단점:

- 100분 안에 역할, 계산식, 분포, UI까지 구현하기에는 범위가 넓다.
- 교육 예제의 도메인 변경판처럼 보일 수 있다.
- 계산 가정의 타당성을 설명하는 데 시간이 많이 필요하다.

### 후보 3. 기술 문서 Version Conflict RAG

서로 다른 revision의 가상 기술 문서를 검색하여 최신 기준, 과거 기준, 문서 간 충돌 및 문서에 없는 정보를 구분해 답하는 RAG 시스템이다.

예시 문서:

```text
Process Guide Rev 1
Maximum temperature = 420°C

Process Guide Rev 2
Maximum temperature = 400°C
```

예시 질문:

- 최신 revision의 값은 무엇인가?
- Rev 1 기준 값은 무엇인가?
- 두 문서가 충돌하는가?
- 문서에 없는 parameter의 값은 무엇인가?
- revision 간 변경된 항목은 무엇인가?

개선 단계 예시:

1. Naive RAG
2. Hybrid Search
3. Metadata Filter
4. Reranking

장점:

- 구조가 명확하며 구현 성공 확률이 높다.
- 기준선과 개선 후 점수를 비교하기 쉽다.
- RAG의 대표적인 실패 유형을 보여주기 좋다.

단점:

- 기존 공정 데이터 분석 경험을 활용하는 정도가 후보 1보다 낮다.
- Tool Calling 중심의 Agent 시연 효과는 상대적으로 약하다.

### 기타 검토 후보

- 대용량 DB Query Planner Agent
- SQL 분석 Agent
- 실험조건 추천 Agent
- 장비 Trouble Shooting 문서 RAG
- 이상 wafer 자동 분석 Agent
- 실험 결과 자동 Report Agent
- Wafer 이상 분석 Multi-Agent

대용량 DB Query Planner Agent는 업무 활용성이 높지만, 캡스톤에서는 실제 DB 연결과 안전한 쿼리 실행 환경을 구성하는 데 시간이 많이 들 수 있다. 따라서 실제 DB 대신 CSV 또는 SQLite를 사용하는 축소 구현이 필요하다.

---

## 3. 최종 결정

> **Process Detective — AI Process Trouble Shooting Agent**

트랙: 자유 트랙

자연어 질문을 받으면 AI Agent가 적절한 데이터 분석 Tool을 선택·실행하고, 실제 계산 결과를 근거로 공정 이상 원인 후보를 정리하는 웹앱으로 결정한다.

핵심 문장:

> LLM에게 공정 원인을 추측하게 하는 것이 아니라, LLM이 필요한 분석을 선택하고 실제 데이터 분석 결과를 근거로 원인 후보를 정리하게 한다.

### 최종 선정 이유

1. 100분 내 MVP 완주 가능성이 높다.
2. 단순 챗봇과 Agent의 차이를 명확히 보여준다.
3. Tool Calling의 교육 내용을 직접 적용할 수 있다.
4. 공정 및 데이터 분석 경험과 자연스럽게 연결된다.
5. 가상 데이터만 사용해도 충분한 시연이 가능하다.
6. Tool description 개선 전후를 정량적으로 평가할 수 있다.
7. 시간이 남을 경우 RAG를 독립적인 확장 기능으로 붙일 수 있다.

---

## 4. 문제 정의

### 문제

공정 데이터에 이상이 발생하면 분석 담당자가 기간 비교, 변수 변화 확인, 이상치 탐색, 장비별 비교, 영향 변수 분석을 각각 수행해야 한다. 사용자가 분석 목적에 맞는 방법과 코드를 직접 선택해야 하므로 초기 조사에 반복 작업이 많다.

### 해결 방식

사용자가 자연어로 이상 현상을 질문하면 Agent가 다음 작업을 수행한다.

1. 질문의 분석 의도를 판단한다.
2. 적절한 Python 분석 Tool을 선택한다.
3. Tool을 실행하여 실제 분석 결과를 얻는다.
4. 여러 Tool 결과를 종합한다.
5. 데이터상 근거가 있는 원인 후보와 추가 확인 항목을 제시한다.

### 포함하지 않는 것

- 실제 원인의 자동 확정
- 실제 생산 데이터 연결
- 운영 DB 직접 쿼리
- 복잡한 causal inference
- 모델 기반 고정밀 수율 예측
- 불필요한 Multi-Agent 구조

---

## 5. MVP 범위

### 입력 데이터

가상의 CSV 파일 하나를 사용한다.

```text
timestamp
lot_id
wafer_id
equipment
pressure
temperature
gas_flow
rf_power
etch_time
cd
defect_rate
yield
```

실제 값이나 내부 식별자는 사용하지 않고 다음과 같은 익명화된 값을 사용한다.

- LOT: `LOT_A`, `LOT_B`
- Wafer: `WF_01`, `WF_02`
- 장비: `EQP_X`, `EQP_Y`
- Recipe: `RECIPE_v1`, `RECIPE_v2`

### 데이터에 심을 가상 패턴

정상기간 예시:

```text
pressure 평균 ≈ 100
temperature 표준편차 ≈ 1
yield 평균 ≈ 95%
```

이상기간 예시:

```text
pressure 평균 ≈ 112
temperature 분산 증가
특정 equipment에서 defect_rate 증가
yield 평균 ≈ 88%
```

이 패턴은 Agent의 분석 흐름을 시연하기 위한 가상 상관 패턴이며, 실제 공정 메커니즘을 주장하는 용도로 사용하지 않는다.

---

## 6. 분석 Tool 설계

MVP에서는 Tool을 정확히 4개로 제한한다.

| Tool | 역할 | 대표 질문 |
|---|---|---|
| `compare_period` | 정상기간과 이상기간의 주요 변수 차이를 계산 | 수율이 낮아진 전후에 무엇이 변했어? |
| `find_outliers` | 이상 LOT, wafer 또는 equipment와 이상 집중 구간을 탐색 | 특정 장비에 이상이 몰려 있어? |
| `rank_features` | target과 관련성이 큰 수치형 변수를 순위화 | 수율과 관련이 큰 변수는 무엇이야? |
| `plot_trend` | 선택 변수의 시간 추이를 시각화 | Pressure가 언제부터 변했어? |

### 질문별 Tool 선택 예시

| 사용자 질문 | 예상 Tool |
|---|---|
| 수율이 왜 낮아졌어? | `compare_period`, `rank_features` |
| 특정 장비에 문제가 몰려 있어? | `find_outliers` |
| Pressure가 언제부터 변했어? | `plot_trend` |
| 최근 이상 원인을 전체적으로 조사해줘. | 4개 Tool 중 필요한 도구를 연쇄 실행 |

### Tool description 설계 원칙

Tool description은 함수 내부 구현보다 Agent의 선택 행동에 직접 영향을 준다. 따라서 다음 정보를 명확히 포함한다.

- 어떤 질문에 사용하는가?
- 어떤 질문에는 사용하지 않는가?
- 입력 인자는 무엇인가?
- 출력에는 어떤 값이 포함되는가?
- 비슷한 다른 Tool과 무엇이 다른가?

예시:

```text
Before
공정 데이터의 이상을 분석한다.

After
특정 LOT, wafer 또는 equipment에 이상값이 집중되어 있는지
확인할 때 사용한다. 기간 간 평균 차이를 비교하는 용도에는
compare_period를 사용한다.
```

---

## 7. Agent 출력 형식

최종 답변은 다음 구조를 사용한다.

```text
분석 요약
- 이상 발생 시점 또는 구간
- 정상기간 대비 주요 변화

주요 원인 후보
1. Pressure 변화 — 데이터 근거
2. Temperature 변동성 증가 — 데이터 근거
3. 특정 equipment 집중 — 데이터 근거

해석 주의사항
- 현재 결과는 관찰 데이터의 연관성 분석이다.
- 인과관계 확정을 위해 추가 공정 검증이 필요하다.

추가 확인 항목
- Recipe 변경 이력
- Equipment maintenance 이력
- 대상 LOT 전후의 공정 조건
```

임의의 확률값 대신 `High`, `Medium`, `Low` 또는 단순 순위를 사용한다. 신뢰도 수치를 표시하려면 계산 근거가 있어야 한다.

---

## 8. UI 초안

화면은 단순하게 구성한다.

```text
Process Detective

[질문 입력]
최근 품질 지표가 나빠진 원인을 분석해줘.

[분석 실행]

분석 진행
- compare_period 완료
- find_outliers 완료
- rank_features 완료
- plot_trend 완료

분석 결과
- Pressure 평균 +12%
- Temperature 변동성 +34%
- EQP_Y에서 defect 증가 집중

결론
- 데이터상 Pressure 변화와 특정 장비 그룹이 수율 저하와
  강하게 연관되어 있다.
- 실제 원인 판단을 위해 추가 공정 검증이 필요하다.
```

발표에서는 호출된 Tool과 각 Tool의 핵심 결과를 함께 보여준다.

---

## 9. 평가 및 개선 계획

### 평가 질문

분석 의도가 다른 테스트 질문 10개를 준비한다.

예시:

1. 정상기간과 이상기간의 변수 차이를 알려줘.
2. 수율 저하와 관련이 큰 변수를 찾아줘.
3. 장비별로 defect가 몰리는지 확인해줘.
4. Pressure가 언제부터 상승했는지 보여줘.
5. 특정 wafer가 이상치인지 확인해줘.
6. 전체적인 이상 원인을 조사해줘.
7. Temperature의 시간 추이를 보여줘.
8. LOT별 이상치 집중 여부를 알려줘.
9. 정상기간 대비 gas flow가 얼마나 변했어?
10. yield와 관련성이 높은 변수 순위를 알려줘.

### Round 0

초기 Tool description으로 도구 선택 정확도를 측정한다.

예시:

```text
Correct tool selection: 7 / 10
```

실패 사례:

```text
질문:
장비별로 이상이 몰리는지 확인해줘.

Agent 선택:
rank_features

기대 Tool:
find_outliers
```

### 개선

틀린 질문에서 Agent가 선택한 Tool과 기대 Tool의 description을 비교하고, 적용 대상과 제외 대상을 명확하게 수정한다.

### Round 1

동일한 질문으로 다시 평가한다.

예시:

```text
Correct tool selection: 9 / 10
```

발표 핵심 메시지:

> 모델을 교체한 것이 아니라 Tool description을 구체화하여 Agent의 행동 정확도를 개선했다.

---

## 10. 아키텍처 결정

### MVP 아키텍처

```text
가상 CSV
  ↓
Python Analysis Tools
  ↓
Single LLM Agent
  ↓
근거 기반 분석 결과
```

### Multi-Agent를 사용하지 않는 이유

이번 MVP는 각 역할이 서로 다른 자료, 권한 또는 독립적인 작업 환경을 필요로 하지 않는다. Manager, Analyst, Process Expert로 분리하면 100분 내 구현에서 통신, 상태 관리 및 디버깅 비용만 늘어날 가능성이 높다.

따라서 다음 구조를 선택한다.

> Single Agent + Multiple Tools

발표에서는 Multi-Agent를 몰라서 제외한 것이 아니라, 문제 규모와 역할 분리 필요성을 검토한 뒤 단일 Agent가 더 적절하다고 판단했다고 설명한다.

---

## 11. Stretch Goal

MVP를 완성하고 시간이 남을 때만 가상의 Troubleshooting Guide를 RAG로 연결한다.

확장 구조:

```text
사용자 질문
  ↓
Agent
  ├─ 데이터 분석 Tools
  └─ Troubleshooting Guide RAG
          ↓
데이터 근거 + 문서 근거를 포함한 종합 답변
```

예시 질문:

> Pressure 상승과 defect 증가가 관찰됐는데 왜 이런 현상이 발생할 수 있어?

예상 답변 구성:

- 데이터 근거: 이상기간 Pressure 평균이 정상기간 대비 상승
- 문서 근거: 가상 가이드에서 Pressure 변화가 공정 거동에 영향을 줄 수 있다고 설명
- 한계: 데이터 연관성과 문서상 가능성을 종합한 원인 후보이며 추가 검증 필요

RAG는 처음부터 포함하지 않는다. MVP가 정상 동작한 뒤 남는 시간에만 추가한다.

---

## 12. 구현 우선순위

1. 가상 CSV 생성
2. 4개 분석 Tool 구현 및 단위 확인
3. Agent에 Tool 연결
4. 대표 질문 4개로 정상 동작 확인
5. 결과 화면 구성
6. 테스트 질문 10개로 Round 0 평가
7. Tool description 수정
8. Round 1 재평가
9. 결과 및 한계 정리
10. 시간이 남으면 RAG 확장

### 시간 부족 시 반드시 남길 것

- 가상 CSV
- 최소 3개 이상의 정상 동작 Tool
- 질문에 따른 Tool 선택
- 실제 계산 결과 기반 답변
- Tool 호출 기록
- 최소한의 Round 0/1 비교

### 시간 부족 시 제거할 것

- Multi-Agent
- 실제 DB 연결
- 복잡한 RAG
- 고급 시각화
- 모델 학습
- 인과 추론
- 배포 자동화

---

## 13. 발표 스토리라인

1. 문제: 공정 이상 조사에는 반복적인 분석 작업이 필요하다.
2. 아이디어: 사용자는 자연어로 질문하고 Agent가 필요한 분석을 선택한다.
3. 구조: Single Agent와 4개의 Python Tool을 사용한다.
4. 시연: 질문에 따라 서로 다른 Tool이 호출된다.
5. 근거: 답변은 LLM의 추측이 아니라 실제 계산 결과를 기반으로 한다.
6. 개선: Tool description 수정으로 선택 정확도가 향상됐다.
7. 한계: 현재 결과는 상관 기반 원인 후보이며 실제 공정 검증이 필요하다.
8. 확장: 향후 기술 문서 RAG와 실제 분석 환경 연결이 가능하다.

### 발표용 한 문장

> Process Detective는 LLM이 공정 원인을 임의로 추측하는 시스템이 아니라, 질문에 맞는 분석 도구를 선택하고 실제 데이터 분석 결과를 근거로 원인 후보를 정리하는 Agent다.

---

## 14. 최종 결론

최종 캡스톤은 `Process Detective — AI Process Trouble Shooting Agent`로 결정한다.

핵심 구현 범위는 가상 CSV, 4개 Python 분석 Tool, Single Agent, 근거 기반 결과 요약, Tool description 개선 전후 평가다. RAG는 Stretch Goal로만 두며 Multi-Agent와 실제 운영 DB 연결은 MVP에서 제외한다.

이 범위는 업무 연관성, Agent 개념의 명확성, 구현 성공 가능성, 발표 스토리 및 보안 측면의 균형이 가장 좋다.
