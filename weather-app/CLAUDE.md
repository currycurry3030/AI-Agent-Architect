# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page Korean weather app: click a city marker on a Leaflet map to see current
conditions, hourly/7-day forecast, and chat with an OpenAI-backed weather assistant about
what's on screen. No frameworks, no bundler, no `package.json` — plain HTML/CSS/JS on the
frontend and a zero-dependency Node.js `http` server on the backend.

This was built as the running example for a "vibe coding" workshop (course notes for that
workshop live in a sibling `ai-agent-course/course-notes/` directory, not part of this app).

## Commands

There is no build step, package manager, or test suite. Run the server directly:

```powershell
node server.js
```

Serves the app at `http://localhost:8765` (override with `PORT` in `.env`). There is no
watch/reload — restart `node server.js` after editing `server.js`; static frontend files
(`*.html`, `*.js`, `*.css`) are served fresh on every request, so just reload the browser.

## Architecture

**Backend (`server.js`)** — a single-file Node `http` server, no Express/frameworks, no
`node_modules`. It does three things:
1. Serves static files from the project root (with `.env` and path-traversal blocked).
2. `GET /api/weather?lat=&lon=` — proxies Open-Meteo, with an in-memory `Map` cache
   (10 min TTL, keyed by lat/lon rounded to 2 decimals) that also serves stale data on
   upstream failure so the UI doesn't break on rate limits.
3. `POST /api/chat` — proxies OpenAI's chat completions endpoint using `OPENAI_API_KEY`
   from `.env`. This is the load-bearing security boundary: the key never reaches the
   browser, only this server-side handler holds it.

`.env` is parsed by a hand-rolled `loadEnv()` (no `dotenv` package) — existing
`process.env` values take precedence over the file.

**Frontend (vanilla JS, loaded in this order via `index.html`):**
- `cities.js` — static list of Korean cities with lat/lon (`CITIES`).
- `weather.js` — `fetchWeather()` calls `/api/weather`; `describeWeatherCode()` maps
  Open-Meteo weather codes to Korean labels/emoji (`WEATHER_CODES`).
- `chat.js` — chat panel logic. Keeps `chatHistory` in memory (module-level array, reset
  per city selection) and posts it to `/api/chat` on each turn; the system prompt is built
  from the currently displayed weather data so the assistant only "knows" what's on screen.
- `app.js` — Leaflet map setup, marker click handling, and rendering the weather detail
  panel (current conditions, hourly scroll, daily list) into `#panel`. Calls `setupChat()`
  from `chat.js` after rendering weather for a newly selected city.

Data flow on a city click: `app.js` marker handler → `weather.js: fetchWeather()` →
`/api/weather` (server-side Open-Meteo proxy/cache) → `app.js` renders panel →
`chat.js: setupChat()` seeds a new chat session scoped to that city's weather.

## Key constraints

- **Keep it dependency-free.** No `npm install`, no bundler, no frameworks — this is
  intentional for the course exercise. Don't introduce `package.json` unless explicitly
  asked.
- **Never let `OPENAI_API_KEY` reach the browser.** All OpenAI calls must go through
  `POST /api/chat` on the server; the frontend only ever talks to `/api/chat` and
  `/api/weather`, never directly to OpenAI or with the key inlined.
- `.env` is gitignored and only prevents accidental repo leaks — it does not hide secrets
  from an agent with filesystem/shell access to this project.
