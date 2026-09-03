# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Course material for a 1-day "vibe coding" workshop (RAG → Tool Calling → MCP →
Multi-Agent), all under `course-notes/`. There is no application code here — the running
example app built during the workshop exercises lives separately in a sibling
`../weather-app/` directory (its own `CLAUDE.md` documents that).

## `course-notes/` structure

**Source docs (edit these):**
- `README.md` + `01-*.md` … `08-*.md` — the 8-session lecture notes ("학습노트").
- `실습가이드-00-*.md` … `실습가이드-07-*.md` — matching hands-on checklists ("실습가이드"),
  meant to be followed standalone (self-study), with copy-pasteable Claude Code prompts.
- `easy/` — a parallel, persona-adapted rewrite of **every** file above (same filenames,
  same directory-relative structure), aimed at a non-engineer audience (design-tool analogies
  instead of jargon). This is a full duplicate content track, not a diff/patch.

**Generated artifacts (don't hand-edit):**
- `webapp.html` / `AI-Agent-워크북.html` — a single-page interactive workbook that inlines
  *all 17 general docs + all 17 easy docs* as JSON and renders them client-side with
  `marked.js`, with sidebar nav, a general/easy toggle, and localStorage-backed checkbox
  progress tracking. `webapp.html` is the Artifact-published fragment (no
  `<html>`/`<head>`/`<body>`); `AI-Agent-워크북.html` is the same content wrapped as a
  standalone file for double-click opening. Both are built from the `course-notes/*.md`
  and `course-notes/easy/*.md` sources by a Python generator script — **that script is not
  currently checked into this repo** (it was run from an external scratch location), so
  regenerating these HTML files after editing the markdown currently requires recreating
  that build step.
- `pdf/*.pdf` — one PDF per source `.md` (17 general-doc PDFs; the `easy/` variants have no
  PDF export), rendered via headless Chrome printing a styled HTML conversion. Also a
  manual, one-off export with no in-repo script.

**Content invariant if you touch checklists:** the general and `easy/` version of a doc
share checkbox progress state by index (same position in the file = same localStorage key
in the webapp), so if you add/remove a `- [ ] ...` line in one version of a doc, make the
matching edit in the other version too, in the same order — otherwise progress tracking
and the (external) build script's checkbox-count assertion will desync.
