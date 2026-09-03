# 실습 가이드 5 · MCP — 서버 연결로 도구 늘리기

목표: 성격이 다른 로컬/원격 MCP 서버를 실제로 연결해보고, 붙이는 절차가 왜 항상 "버튼 하나"인지 체감한다. 04에서 만든 `agent-lab`을 이어서 사용.

원본은 [학습노트 05](05-MCP.md) 참고. 원본이 쓰는 사내 전용 "자료 조사 서버"는 배포 불가라, **직접 만드는 로컬 MCP 서버**로 대체하고, Microsoft Learn(실재 공개 서버)·Tavily(본인 키)는 원본과 동일하게 진행합니다.

## 체크리스트

### 1. MCP 연결 기능을 앱에 추가
```
이 앱에 MCP(Model Context Protocol) 서버 연결 기능을 추가해줘.
- mcp_catalog.json 파일에 서버 목록(이름, 로컬이면 command/args, 원격이면 url)을 등록하는 구조로 만들어줘.
- [MCP] 탭을 추가해서 카탈로그의 서버들을 목록으로 보여주고, 각 서버 옆에 [연결]/[끊기] 버튼을 넣어줘.
- 연결하면 그 서버가 제공하는 도구들을 가져와서 기존 도구 목록에 합쳐줘. 도구 옆에 어느 서버 출신인지 표시해줘.
- 끊으면 그 서버의 도구가 목록에서 사라지게 해줘.
- [도구] 탭의 "지금 쓸 수 있는 도구" 목록에 MCP로 붙은 도구도 함께 보이게 해줘.
```
(서버 재시작)

### 2. 로컬 MCP 서버 직접 만들기 (자료 조사 서버 대체)
- [ ] 참고할 짧은 문서(md) 2~3개를 `docs/` 폴더에 준비 (본인 관심 주제로 직접 작성해도 됨)
```
mcp-servers/doc-search 폴더에 간단한 MCP 서버를 만들어줘 (파이썬, stdio 방식).
- 도구 이름은 doc_search, 인자는 query(string) 하나.
- docs/ 폴더의 md 파일들에서 query와 관련된 부분을 찾아 텍스트로 반환해줘.
- mcp_catalog.json 에 "자료 조사 서버"라는 이름으로 등록해줘 (command: python, args: 이 서버 경로).
```
(서버 재시작) `[MCP]` 탭에서 연결 → `[도구]` 탭에서 문서 내용 관련 질문 던져보기

### 3. 연결이 곧 프로세스라는 것 확인
```powershell
Get-Process python
```
- [ ] 자료 조사 서버 연결 상태에서 프로세스 수 확인
- [ ] `[MCP]` 탭에서 연결 끊고 다시 확인 → 프로세스 수 변화 관찰

### 4. 원격 공개 서버 연결 — Microsoft Learn
```
mcp_catalog.json 에 Microsoft Learn 문서 서버를 추가해줘.
url은 https://learn.microsoft.com/api/mcp 야. 이름은 "Microsoft Learn 문서 서버"로 표시해줘.
```
(서버 재시작) 연결 → `Get-Process python`으로 로컬 프로세스 수가 안 느는 것 확인 (원격이라서) → 질문 테스트
```
PowerShell 실행 정책을 CurrentUser 만 RemoteSigned 로 바꾸는 명령은?
```

### 5. 두 서버 갈림길 테스트
- [ ] 두 서버 모두에 걸릴 법한 질문을 던져 어느 도구가 선택되는지, 왜 그런지 설명문을 비교해 확인

### 6. 원격 API 키 서버 — Tavily 웹 검색
- [ ] `app.tavily.com`에서 발급받은 키를 `.env`에 추가: `TAVILY_API_KEY=발급받은키`
```
mcp_catalog.json 에 Tavily 웹 검색 서버를 추가해 줘.
- 원격 HTTP 서버이고, 주소 형식은 https://mcp.tavily.com/mcp/?tavilyApiKey=<API키> 야.
- API 키는 .env 의 TAVILY_API_KEY 에서 읽어서 채워줘. 카탈로그 파일에 키가 그대로 적히면 안 돼.
- 화면의 서버 목록에 "Tavily 웹 검색" 으로 보이게 해 줘.
```
(서버 재시작) 연결 → `오늘 주요 뉴스 알려줘` 테스트 → 확인 끝나면 연결 끊어두기

## 완료 기준
- [ ] 로컬 서버(자체 제작)와 원격 서버(Microsoft Learn) 둘 다 "버튼 하나"로 연결/해제됨을 확인
- [ ] 연결 여부에 따라 로컬 프로세스 수가 달라지는 것을 확인
- [ ] API 키가 필요한 원격 서버(Tavily)까지 등록해 실제 웹 검색을 성공시킴

다음: [06-MultiAgent 실습 가이드](실습가이드-06-MultiAgent.md) (같은 `agent-lab` 폴더에서 이어서 진행)
