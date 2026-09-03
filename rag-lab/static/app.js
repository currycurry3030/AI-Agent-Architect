"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const el = (t, c, txt) => {
  const n = document.createElement(t);
  if (c) n.className = c;
  if (txt !== undefined) n.textContent = txt;
  return n;
};
const nf = (n) => (n ?? 0).toLocaleString("ko-KR");

let PAGE = 1, NPAGES = 1;
let STRATEGY_LABELS = {};
const HAVE = { doc: false, chunks: 0, store: 0 };

// 청크 카드를 한 번에 다 그리면 브라우저가 버벅인다. 문서가 크면 천 장이 넘는다.
// 미리보기는 앞에서부터 이만큼만 그리고, 더 필요하면 눌러서 이어 붙인다.
const PREVIEW_STEP = 40;
let ALL_CHUNKS = [], SHOWN = 0;

// ── 탭 ──────────────────────────────────────────────────────────
function show(pane) {
  $$(".pane").forEach((p) => p.classList.toggle("on", p.id === pane));
  $$(".tab").forEach((t) => t.classList.toggle("on", t.dataset.pane === pane));
  gate();
}
$$(".tab").forEach((t) => { t.onclick = () => show(t.dataset.pane); });

/** 앞 단계가 안 끝났으면 무엇을 먼저 해야 하는지 알려 준다. 막지는 않는다. */
function gate() {
  $("#p2-need").classList.toggle("hidden", HAVE.doc);
  $("#p3-need").classList.toggle("hidden", HAVE.chunks > 0);
  $("#p4-need").classList.toggle("hidden", HAVE.store > 0);
  $$(".tab").forEach((t) => {
    const done = (t.dataset.pane === "p1" && HAVE.doc)
      || (t.dataset.pane === "p2" && HAVE.chunks > 0)
      || (t.dataset.pane === "p3" && HAVE.store > 0);
    t.classList.toggle("done", !!done);
  });
}

// ── 상단 현황 ───────────────────────────────────────────────────
function setStatus(part) {
  if (part.doc !== undefined) {
    const d = part.doc;
    HAVE.doc = !!(d && d.loaded);
    $("#st-doc").textContent = HAVE.doc
      ? (d.name.length > 26 ? d.name.slice(0, 26) + "…" : d.name) : "—";
    $("#st-size").textContent = HAVE.doc
      ? nf(d.n_pages) + "쪽 · " + nf(d.n_chars) + "자" : "—";
  }
  if (part.chunks !== undefined) {
    HAVE.chunks = part.chunks.count || 0;
    $("#st-chunks").textContent = HAVE.chunks
      ? nf(HAVE.chunks) + "개 · " + (part.chunks.label || "") : "—";
  }
  if (part.store !== undefined) {
    const s = part.store;
    HAVE.store = s.total || 0;
    $("#st-store").textContent = nf(HAVE.store);
    $("#st-model").textContent = s.model ? s.model + " · " + nf(s.dim) + "차원" : "—";
  }
  gate();
}

function msg(id, text, kind) {
  const n = $(id);
  n.textContent = text || "";
  n.className = "msg" + (kind ? " " + kind : "");
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ error: "응답을 읽지 못했습니다" }));
  if (!res.ok || data.error) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}

function cards(target, items) {
  const box = $(target);
  box.innerHTML = "";
  box.classList.remove("hidden");
  items.forEach(([k, v, warn]) => {
    const c = el("div", "card" + (warn ? " warn" : ""));
    c.appendChild(el("span", "k", k));
    c.appendChild(el("span", "v", v));
    box.appendChild(c);
  });
}

// ── ① PDF 업로드 ────────────────────────────────────────────────
function showDoc(d) {
  if (!d.loaded) return;
  const thin = (d.thin_pages || []).length;
  cards("#doc-summary", [
    ["쪽", nf(d.n_pages)],
    ["뽑아낸 글자", nf(d.n_chars)],
    ["글자가 거의 없는 쪽", nf(thin), thin > 0],
  ]);
  NPAGES = d.n_pages; PAGE = 1;
  $("#doc-view").classList.remove("hidden");
  drawBars(d.pages || []);
  loadPage();
  setStatus({ doc: d });
}

function drawBars(pages) {
  const box = $("#page-bars");
  box.innerHTML = "";
  const max = Math.max(1, ...pages.map((p) => p.n_chars));
  pages.forEach((p) => {
    const b = el("i");
    b.style.height = Math.max(3, Math.round((p.n_chars / max) * 42)) + "px";
    if (p.thin) b.classList.add("thin");
    b.title = p.page + "쪽 · " + nf(p.n_chars) + "자";
    b.onclick = () => { PAGE = p.page; loadPage(); };
    box.appendChild(b);
  });
}

async function loadPage() {
  const d = await api("/api/document?page=" + PAGE);
  if (!d.loaded) return;
  PAGE = d.page; NPAGES = d.n_pages;
  $("#page-label").textContent = PAGE + " / " + NPAGES;
  $("#page-chars").textContent = nf(d.n_chars) + "자"
    + (d.thin ? " — 글자가 거의 없습니다. 원본 PDF 의 이 쪽을 열어 보세요." : "");
  $("#page-chars").className = "hint" + (d.thin ? " warn-text" : "");
  $("#doc-text").textContent = d.text || "(뽑아낸 글자가 없습니다)";
  const bars = $("#page-bars").children;
  for (let i = 0; i < bars.length; i++) bars[i].classList.toggle("cur", i === PAGE - 1);
}

$("#btn-upload").onclick = async () => {
  const f = $("#file").files[0];
  if (!f) return msg("#upload-msg", "PDF 를 골라 주세요", "err");
  msg("#upload-msg", "파싱 중…");
  const fd = new FormData();
  fd.append("file", f);
  try {
    const d = await api("/api/upload", { method: "POST", body: fd });
    showDoc(d);
    setStatus({ chunks: { count: 0 } });     // 문서가 바뀌면 청크는 무효
    $("#chunk-list").innerHTML = "";
    $("#chunk-summary").classList.add("hidden");
    msg("#upload-msg", "파싱 완료 — ② 청킹으로 넘어가세요", "ok");
  } catch (e) { msg("#upload-msg", e.message, "err"); }
};

$("#page-prev").onclick = () => { if (PAGE > 1) { PAGE--; loadPage(); } };
$("#page-next").onclick = () => { if (PAGE < NPAGES) { PAGE++; loadPage(); } };

// ── ② 청킹 ──────────────────────────────────────────────────────
function chunkNode(c, extra) {
  const n = el("div", "chunk");
  const meta = el("div", "meta");
  if (extra && extra.rank !== undefined) meta.appendChild(el("span", "no", extra.rank + "위"));
  meta.appendChild(el("span", "no", "#" + (c.chunk_index ?? c.index)));
  if (extra && extra.score !== undefined)
    meta.appendChild(el("span", "score", (extra.scoreLabel || "유사도") + " " + extra.score));
  if (extra && extra.note) meta.appendChild(el("span", null, extra.note));
  meta.appendChild(el("span", null, (c.n_chars ?? c.text.length) + "자"));
  if (c.page) meta.appendChild(el("span", null, c.page + "쪽"));
  if (c.document) meta.appendChild(el("span", null, c.document));
  n.appendChild(meta);
  n.appendChild(el("div", "body", c.text));
  n.onclick = () => n.classList.toggle("open");
  return n;
}

function renderMoreChunks() {
  const list = $("#chunk-list");
  const old = $("#chunk-more");
  if (old) old.remove();

  const next = ALL_CHUNKS.slice(SHOWN, SHOWN + PREVIEW_STEP);
  next.forEach((c) => list.appendChild(chunkNode({ ...c, chunk_index: c.index })));
  SHOWN += next.length;

  if (SHOWN < ALL_CHUNKS.length) {
    const bar = el("div", "more");
    bar.id = "chunk-more";
    bar.appendChild(el("span", "hint",
      ALL_CHUNKS.length + "개 중 " + SHOWN + "개를 보고 있습니다"));
    const b = el("button", null, "더 보기");
    b.onclick = renderMoreChunks;
    bar.appendChild(b);
    list.appendChild(bar);
  }
}

$("#btn-chunk").onclick = async () => {
  const strategy = document.querySelector("input[name=strategy]:checked").value;
  const size = Number($("#size").value) || 500;
  msg("#chunk-msg", "자르는 중…");
  try {
    const d = await api("/api/chunk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategy, size }),
    });
    cards("#chunk-summary", [
      ["전략", d.strategy_label],
      ["청크", nf(d.summary.count)],
      ["가장 긴 조각", nf(d.summary.max) + "자"],
      ["가장 짧은 조각", nf(d.summary.min) + "자"],
      ["평균", nf(d.summary.avg) + "자"],
    ]);
    ALL_CHUNKS = d.chunks;
    SHOWN = 0;
    $("#chunk-list").innerHTML = "";
    renderMoreChunks();
    setStatus({ chunks: { count: d.summary.count, label: d.strategy_label } });
    msg("#chunk-msg", "청크 " + d.summary.count + "개 — ③ 임베딩으로 넘어가세요", "ok");
  } catch (e) { msg("#chunk-msg", e.message, "err"); }
};

// ── ③ 임베딩 ────────────────────────────────────────────────────
function showStore(s) {
  cards("#store-summary", [
    ["적재된 청크", nf(s.total)],
    ["임베딩 모델", s.model || "-"],
    ["차원", s.dim ? nf(s.dim) : "-"],
  ]);
  const wrap = $("#store-docs");
  wrap.innerHTML = "";
  if (s.documents && s.documents.length) {
    const t = el("table");
    const hr = el("tr");
    ["문서", "청크", "청킹 전략"].forEach((h) => hr.appendChild(el("th", null, h)));
    const thead = el("thead"); thead.appendChild(hr); t.appendChild(thead);
    const tb = el("tbody");
    s.documents.forEach((d) => {
      const tr = el("tr");
      tr.appendChild(el("td", null, d.document));
      tr.appendChild(el("td", null, nf(d.chunks)));
      tr.appendChild(el("td", null, STRATEGY_LABELS[d.strategy] || d.strategy));
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t);
  }
  setStatus({ store: s });
  renderDocFilter(s.documents || []);
}

// ── ④ 검색 대상 문서 필터 ──────────────────────────────────────
function renderDocFilter(documents) {
  const box = $("#doc-filter");
  const prevChecked = new Set($$("#doc-filter input:checked").map((c) => c.value));
  box.innerHTML = "";
  box.classList.toggle("hidden", documents.length === 0);
  documents.forEach((d) => {
    const label = el("label", "doc-check");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = d.document;
    cb.checked = prevChecked.has(d.document);
    label.appendChild(cb);
    label.appendChild(el("span", null, d.document + " (" + nf(d.chunks) + ")"));
    box.appendChild(label);
  });
}

function selectedDocuments() {
  return $$("#doc-filter input:checked").map((c) => c.value);
}

$("#btn-embed").onclick = async () => {
  msg("#embed-msg", "임베딩 중… 창을 닫지 마세요");
  $("#btn-embed").disabled = true;
  try {
    const d = await api("/api/embed", { method: "POST" });
    showStore(d.status);
    msg("#embed-msg", d.added + "건 적재 완료 — ④ 검색으로 넘어가세요", "ok");
  } catch (e) { msg("#embed-msg", e.message, "err"); }
  finally { $("#btn-embed").disabled = false; }
};

$("#btn-reset").onclick = async () => {
  const d = await api("/api/reset", { method: "POST" });
  showStore(d.status);
  msg("#embed-msg", "저장소를 비웠습니다", "ok");
};

$("#btn-peek").onclick = async () => {
  const idx = Number($("#peek-idx").value) || 0;
  const st = await api("/api/status");
  const docs = st.store.documents || [];
  if (!docs.length) return msg("#peek-msg", "적재된 문서가 없습니다", "err");
  try {
    const d = await api("/api/vector", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document: docs[0].document, chunk_index: idx }),
    });
    const out = $("#peek-out");
    out.classList.remove("hidden");
    out.textContent = "#" + idx + " → " + d.dim + "차원 중 앞 10개  ["
      + d.head.join(", ") + ", …]";
    msg("#peek-msg", "", "ok");
  } catch (e) { msg("#peek-msg", e.message, "err"); }
};

// ── ④ 검색 ──────────────────────────────────────────────────────
const SCORE_LABEL = { semantic: "유사도", bm25: "BM25", hybrid: "RRF" };

function renderSearchColumn(kind, part) {
  const a = $("#answer-" + kind);
  if (part.answer) {
    a.innerHTML = "";
    a.classList.remove("hidden");
    const head = el("div", "head");
    head.appendChild(el("span", null, "답변 · " + part.answer.model));
    head.appendChild(el("span", null, "근거 " + part.answer.used.length + "조각"));
    head.appendChild(el("span", null, "프롬프트 " + nf(part.answer.prompt_chars) + "자"));
    head.appendChild(el("span", null, part.answer.latency + "초"));
    a.appendChild(head);
    a.appendChild(el("div", "text", part.answer.text));
  } else {
    a.classList.add("hidden");
  }

  const box = $("#hits-" + kind);
  box.innerHTML = "";
  if (!part.hits.length) {
    // 저장소가 비었을 수도 있고(둘 다 0건), BM25 는 저장소가 있어도 질문과
    // 겹치는 단어가 하나도 없으면 0건이 정상이다. 원인이 다르니 문구도 다르다.
    box.appendChild(el("p", "hint", HAVE.store
      ? "겹치는 조각이 없습니다."
      : "저장소가 비어 있습니다. ③ 에서 먼저 적재하세요."));
  } else {
    part.hits.forEach((h) =>
      box.appendChild(chunkNode(h, { rank: h.rank, score: h.score, scoreLabel: SCORE_LABEL[kind] })));
  }
}

function renderRerankColumn(part) {
  $("#rerank-latency").textContent = part.latency + "초";

  const cbox = $("#rerank-candidates");
  cbox.innerHTML = "";
  part.candidates.forEach((h) =>
    cbox.appendChild(chunkNode(h, { rank: h.rank, score: h.score, scoreLabel: "RRF" })));

  const a = $("#answer-rerank");
  if (part.answer) {
    a.innerHTML = "";
    a.classList.remove("hidden");
    const head = el("div", "head");
    head.appendChild(el("span", null, "답변 · " + part.answer.model));
    head.appendChild(el("span", null, "근거 " + part.answer.used.length + "조각"));
    head.appendChild(el("span", null, "프롬프트 " + nf(part.answer.prompt_chars) + "자"));
    head.appendChild(el("span", null, part.answer.latency + "초"));
    a.appendChild(head);
    a.appendChild(el("div", "text", part.answer.text));
  } else {
    a.classList.add("hidden");
  }

  const box = $("#hits-rerank");
  box.innerHTML = "";
  if (!part.hits.length) {
    box.appendChild(el("p", "hint", "재정렬된 결과가 없습니다."));
  } else {
    part.hits.forEach((h) =>
      box.appendChild(chunkNode(h, { rank: h.rank, note: "하이브리드 " + h.prior_rank + "위" })));
  }
}

function showRewrite(r) {
  const box = $("#rewrite-box");
  if (!r) { box.classList.add("hidden"); return; }
  box.innerHTML = "";
  box.classList.remove("hidden");
  const mk = (label, text) => {
    const item = el("div", "rewrite-item");
    item.appendChild(el("span", "k", label));
    item.appendChild(el("span", "v", text));
    return item;
  };
  box.appendChild(mk("원래 질의", r.original));
  box.appendChild(mk("다시 쓴 질의 · " + r.latency + "초", r.rewritten));
}

$("#rerank").addEventListener("change", () => {
  const on = $("#rerank").checked;
  $("#k").disabled = on;
  $("#search-cols").classList.toggle("hidden", on);
  $("#rerank-panel").classList.toggle("hidden", !on);
});

async function search() {
  const query = $("#query").value.trim();
  const k = Number($("#k").value) || 5;
  const wantAnswer = $("#gen").checked;
  const wantRerank = $("#rerank").checked;
  const wantRewrite = $("#rewrite").checked;
  const documents = selectedDocuments();
  if (!query) return msg("#search-msg", "질문을 입력하세요", "err");
  msg("#search-msg", wantAnswer ? "검색하고 답을 만드는 중…" : "검색 중…");
  ["semantic", "bm25", "hybrid", "rerank"].forEach((k2) => $("#answer-" + k2).classList.add("hidden"));
  try {
    const d = await api("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query, k, answer: wantAnswer, rerank: wantRerank, rewrite: wantRewrite, documents,
      }),
    });

    showRewrite(d.rewrite);

    const v = $("#query-vec");
    v.classList.remove("hidden");
    v.textContent = "질문 벡터 " + d.dim + "차원 중 앞 10개 — ["
      + d.query_vector_head.join(", ") + ", …]";

    if (d.rerank) {
      renderRerankColumn(d.rerank);
      msg("#search-msg", "후보 " + d.rerank.candidates.length + "개 → 재정렬 "
        + d.rerank.hits.length + "개 · " + d.rerank.latency + "초", "ok");
    } else {
      renderSearchColumn("semantic", d.semantic);
      renderSearchColumn("bm25", d.bm25);
      renderSearchColumn("hybrid", d.hybrid);
      msg("#search-msg", "의미 " + d.semantic.hits.length + "건 · BM25 "
        + d.bm25.hits.length + "건 · 하이브리드 " + d.hybrid.hits.length + "건", "ok");
    }
  } catch (e) { msg("#search-msg", e.message, "err"); }
}

$("#btn-search").onclick = search;
$("#query").addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });

// ── 시작 ────────────────────────────────────────────────────────
(async () => {
  try {
    const s = await api("/api/status");
    STRATEGY_LABELS = s.strategies || {};
    showStore(s.store);
    if (s.document && s.document.loaded) showDoc(s.document);
    // 새로고침해도 청킹까지 온 상태가 현황에 남아 있어야 한다
    const c = s.chunking || {};
    if (c.summary && c.summary.count) {
      setStatus({ chunks: { count: c.summary.count, label: c.label } });
      const r = document.querySelector('input[name=strategy][value="' + c.strategy + '"]');
      if (r) r.checked = true;
      if (c.size) $("#size").value = c.size;
    }
  } catch (e) { /* 서버가 막 떴을 때는 조용히 넘어간다 */ }
  gate();
})();
