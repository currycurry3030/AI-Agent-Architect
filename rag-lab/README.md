# rag-lab — 2·3교시 실습 앱

PDF 한 편을 조각으로 잘라 벡터로 저장하고, 질문과 가까운 조각을 꺼내 답을 만드는
naive RAG 를 화면에서 단계별로 관찰하는 앱입니다. 3교시에는 이 앱 위에
Metadata Filter · Query Rewrite · Reranking 을 직접 붙입니다.

## 실행

```
copy .env.example .env      ← 1교시에 발급받은 OPENAI_API_KEY 를 넣는다
pip install -r requirements.txt
run.bat                     ← 또는 python app.py
```

브라우저가 `http://127.0.0.1:8765/` 를 엽니다. 시작할 때 `chromadb` · `pypdf` · 키 세 가지를
확인하고, 빠진 것이 있으면 무엇을 설치할지 알려 준 뒤 멈춥니다.

## 화면

네 구획이 왼쪽에서 오른쪽으로 이어지고, 각 구획은 앞 구획의 산출물을 받습니다.

1. **문서** — PDF 를 올리면 페이지별 글자 수가 막대로 보입니다. 표를 복원하지 않으므로
   그림으로 된 표가 있던 페이지는 글자가 거의 나오지 않습니다. 그 모습을 그대로 봅니다.
2. **청킹** — 전략 세 가지(고정 길이 · 구조 경계 · 문단)와 조각 크기를 고르면 조각이 카드로 나옵니다.
   오버랩은 쓰지 않습니다. 경계가 어디서 생기는지가 보여야 하기 때문입니다.
3. **임베딩·적재** — 조각을 `text-embedding-3-small`(1536차원) 으로 벡터화해 ChromaDB 에 넣습니다.
   조각마다 문서명 · 청크 번호 · 페이지 · 전략을 함께 저장합니다.
4. **검색** — 질문을 같은 모델로 임베딩해 가까운 순으로 K 개를 꺼내고,
   그 조각만 근거로 `gpt-5.4-mini` 가 답을 씁니다.

## 폴더

```
app.py              시작점. 의존성·키 확인 뒤 서버를 띄운다
run.bat             더블클릭 실행 (UTF-8 콘솔, py/python 자동 탐색)
requirements.txt    chromadb, pypdf
lab/config.py       모델·포트·청킹 기본값. 수업 중 바꾸지 않는다
lab/parsing.py      PDF → 글자 (pypdf). 표 복원 없음
lab/chunking.py     fixed / structure / paragraph
lab/llm.py          임베딩·생성 HTTP 호출 (SDK 없음). 원문이 밖으로 나가는 유일한 지점
lab/store.py        ChromaDB 적재·검색. 메타데이터를 처음부터 담는다
lab/answer.py       꺼낸 조각으로 답 생성
lab/web.py          로컬 HTTP 서버와 /api/*
static/             index.html · app.js · style.css
data/               올린 PDF 가 놓이는 곳
chroma_db/          적재 결과 (실행 중 생김)
```

## API

`GET /api/status` · `/api/document` · `/api/chunks`
`POST /api/upload` · `/api/chunk` · `/api/embed` · `/api/search` · `/api/vector` · `/api/reset`

파싱·청킹 결과는 메모리에만 있고 서버를 끄면 사라집니다. 적재된 것만 `chroma_db/` 에 남습니다.

## 고정된 설계

- 임베딩은 문서와 질문을 같은 모델·같은 차원으로 만듭니다. 이 모델에는 문서용·질문용 구분이 없습니다.
- 생성은 Responses API 에 `reasoning.effort = none` 으로 부릅니다. 추론 토큰 없이 곧바로 답합니다.
- BM25 · 하이브리드 · Metadata Filter · Reranking 은 이 앱에 없습니다. 2·3교시에 수강생이 만듭니다.
