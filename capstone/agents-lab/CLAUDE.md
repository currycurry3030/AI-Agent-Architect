# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This is a capstone build ("Process Detective") on top of the original agent-lab template: a local web
app (Korean UI, README in Korean) for handing an LLM tools and watching it work. It has three panels:

- **도구 (Tools)** — four built-in process-analysis tools (`compare_period`, `find_outliers`,
  `rank_features`, `plot_trend`) over a virtual process log CSV (`data/process/process_log.csv`,
  seeded from `data/seed/process_log.csv`). Their descriptions and role prompts can be edited live
  from the screen — see `PROCESS_DETECTIVE.md` for the scenario, injected anomaly, and eval questions.
- **MCP** — attach external tool servers (local stdio or remote Streamable HTTP) via a catalog/config
  pair; the merged tool list shows each tool's source.
- **에이전트 (Agents)** — only shown when `run6.bat` sets `AGENT_LAB_MULTI=1`. A "principal
  investigator" (this app, port 8770) delegates to two researcher subprocesses (ports 8771, 8772) via
  function-call tools. All delegation traffic (instructions in, results out) is logged and streamed to
  the UI in real time.

Pure Python standard library — no `pip install`, no dependency manifest, no build step.

## Running

```
copy .env.example .env      # put OPENAI_API_KEY in it
run.bat                     # Tools + MCP tabs only
run6.bat                    # also opens the Agents tab (sets AGENT_LAB_MULTI=1)
```

Opens `http://127.0.0.1:8770/`. With the Agents tab on, researcher subprocesses run on 8771/8772 and are
cleaned up when the main window closes (and on next startup if a prior run left them behind — see
`orchestrator.cleanup_stale`). There is no test suite, linter, or package manifest in this repo.

Run directly (equivalent to the .bat files, e.g. on non-Windows or when iterating):
```
python app.py                       # Tools + MCP only
AGENT_LAB_MULTI=1 python app.py     # also enables Agents
```

Set `AGENT_LAB_NO_BROWSER=1` to skip the automatic browser launch.

## Architecture

### Server and state
`app.py` is a stdlib `ThreadingHTTPServer`. All routes are POST handlers registered via the `@route`
decorator into `ROUTES`/`NO_LOCK`, plus a few hardcoded GETs in `Handler.do_GET`. **Every POST request is
serialized through a single global `LOCK`**, because `/api/research` can hold it for minutes while
delegation runs. Two GET-only endpoints deliberately bypass the lock so the UI can still poll during a
running research session:
- `/api/research/progress` (GET) — reads the in-progress delegation log without waiting for the lock.
- `/api/research/stop` (POST, registered with `lock=False`) — sets a stop flag read after the *next*
  delegation call returns; it cannot interrupt work already handed to a researcher.

Editable state (tool description overrides, system prompt, notes file path override) lives under
`state/`, created at runtime — not checked in. Resetting via the UI removes these override files, falling
back to code defaults in `lab/tools.py` / `lab/config.py`.

### Tool registry (`lab/registry.py`)
Every tool — built-in or MCP — is normalized to `{name, description, parameters, source, call}` and
merged in `registry.build()`. Description overrides made from the UI are stored in
`state/tool_overrides.json` and layered on top of the code defaults at build time (no restart needed).
Duplicate tool names: first registered wins.

### MCP (`lab/mcp_client.py`, `mcp_catalog.json`, `mcp_config.json`)
`mcp_catalog.json` lists servers connectable from the UI (both local stdio and remote Streamable HTTP,
same UI action for both); server specs use `${VAR}` placeholders for secrets. `mcp_config.json` is the
subset currently connected — written by `app.py:write_mcp_config`, which resolves `${VAR}` from `.env` at
connect time only, so no secret ever lands in either JSON file on disk. If a key is missing, only that
server errors; the rest of the app keeps working.

### Chat loop (`lab/runner.py`, `lab/llm.py`)
`runner.run()` drives the tool-calling loop against the OpenAI Responses API (`lab/llm.py`), bounded by
`MAX_TOOL_STEPS` (chat), `ORCH_MAX_STEPS` (orchestrator), or `AGENT_MAX_STEPS` (researchers) from
`lab/config.py`. `runner.run` also accepts a `history` (for follow-up turns) and a `should_stop` callback
(used by the orchestrator's stop button).

### Multi-agent mode (`lab/orchestrator.py`, `lab/roles.py`, `agents/`)
- **Role/tool split is deliberate**: role boundaries are enforced by prompt text (`lab/roles.py`); tool
  boundaries are enforced by code (`roles.tools_for`). The research role can see MCP tools + built-in web
  search but never `run_python`/`read_data_file`; the experiment role sees only those two and never MCP
  tools. Built-in memo tools go to neither. The two researchers have no way to call each other — the
  orchestrator is the only router, and each delegation is a `delegate_research`/`delegate_experiment`
  function-call tool implemented in `orchestrator._delegate_entries`, so the instruction text and
  returned result are captured as literal tool-call arguments/output in the log.
- Each researcher is its own subprocess (`agents/_serve.py` common HTTP server + `agents/research_agent.py`
  / `agents/experiment_agent.py`), started/stopped by `orchestrator.start`/`stop`, identified via a
  `/info` endpoint carrying `{role, pid, tools}`. On startup, `app.py` calls
  `orchestrator.cleanup_stale()`, which SIGTERMs any leftover process from a prior run *only if* its
  `/info` reports the same role name — it never touches an unrelated process. This matters because a
  forcibly-closed parent window on Windows skips `atexit`, so children can leak across runs and block the
  fixed ports (8771/8772) on next launch.
- A research run (`orchestrator.research`) keeps a session (`_SESSION["items"]`) so a follow-up question
  can continue the same conversation instead of restarting delegation from scratch; whether to re-delegate
  research or just recompute is left to the orchestrator's own judgment, not hardcoded.
- Ports: 8770 (main/orchestrator), 8771 (research), 8772 (experiment) — chosen to avoid colliding with
  sibling local labs on 8765/8766 (see `lab/config.py`).

### Sandboxed execution (`lab/sandbox.py`, `lab/config.py`)
`run_python` runs in a separate process with a 20s timeout (`PY_TIMEOUT`), 4000-char output cap
(`PY_MAX_OUTPUT`), 2 retries (`PY_RETRIES`), and an import allowlist (`PY_ALLOWED_IMPORTS` in
`lab/config.py`: math, random, statistics, csv, json, itertools, collections, datetime, re, time, heapq,
functools, bisect, fractions, decimal, pathlib). Errors are returned to the calling agent as-is so it can
read and fix its own code.

### Data file access (`lab/datafile.py`)
`read_data_file` and the UI's upload/delete controls are confined to `data/research/`, kept separate from
`data/process/process_log.csv` on purpose — mixing them would make the experiment agent's tool log noisy
with irrelevant process-log reads. Only the experiment role gets this tool; the orchestrator must ask it
to read values rather than inventing business assumptions itself.

### Model config (`lab/config.py`)
Generation model `gpt-5.6-luna`, `reasoning.effort = "none"`, `temperature = 0`, `store: false` (no
server-side conversation retention). Built-in web search is enabled by adding `{"type": "web_search"}` to
the `tools` array alongside custom function declarations — only the research role gets it
(`roles.ROLES["research"]["web_search"]`).

## Key files

| Path | Role |
|---|---|
| `app.py` | HTTP server, `/api/*` routes, screen state |
| `lab/config.py` | model/port/paths/execution-limit constants, `.env` loading |
| `lab/llm.py` | OpenAI Responses API call (function calling + built-in web search) |
| `lab/tools.py` | built-in process-analysis tools (`compare_period`, `find_outliers`, `rank_features`, `plot_trend`) |
| `lab/registry.py` | merges built-in + MCP tools, applies description overrides |
| `lab/mcp_client.py` | MCP client (stdio and Streamable HTTP) |
| `lab/runner.py` | the tool-calling chat loop |
| `lab/roles.py` | the three roles' prompts and tool allocation |
| `lab/orchestrator.py` | subprocess lifecycle, `delegate_*` tools, delegation log, follow-up sessions |
| `lab/sandbox.py` | `run_python` |
| `lab/datafile.py` | `read_data_file`, scoped to `data/research/` |
| `agents/_serve.py` | shared HTTP server for one researcher process |
| `agents/research_agent.py` | research role server (:8771) |
| `agents/experiment_agent.py` | experiment role server (:8772) |
| `mcp-servers/doc-search/` | example local stdio MCP server (`doc_list`/`doc_search` over `docs/*.md`) |
