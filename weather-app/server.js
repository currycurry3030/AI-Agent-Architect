// 정적 파일 서빙 + OpenAI 챗봇 프록시 서버.
// OPENAI_API_KEY는 이 서버(.env)에만 보관되고, 브라우저로는 절대 전달되지 않는다.
// 프론트는 /api/chat 을 호출하고, 이 서버가 그 요청을 OpenAI로 대신 전달한다.

const http = require("http");
const fs = require("fs");
const path = require("path");

function loadEnv(file) {
  let content;
  try {
    content = fs.readFileSync(file, "utf8");
  } catch {
    return; // .env가 없으면 무시 (환경변수를 다른 방식으로 설정했을 수도 있음)
  }
  content.split("\n").forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return;
    const idx = trimmed.indexOf("=");
    if (idx === -1) return;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = value;
  });
}

loadEnv(path.join(__dirname, ".env"));

const PORT = Number(process.env.PORT) || 8765;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";
const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";

const STATIC_ROOT = __dirname;
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

function serveStatic(req, res) {
  let urlPath = decodeURIComponent(req.url.split("?")[0]);
  if (urlPath === "/") urlPath = "/index.html";

  const filePath = path.normalize(path.join(STATIC_ROOT, urlPath));
  if (!filePath.startsWith(STATIC_ROOT) || path.basename(filePath) === ".env") {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}

function readJsonBody(req, maxBytes = 1_000_000) {
  return new Promise((resolve, reject) => {
    let body = "";
    let tooLarge = false;
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > maxBytes) {
        tooLarge = true;
        req.destroy();
      }
    });
    req.on("end", () => {
      if (tooLarge) return reject(new Error("요청 본문이 너무 큽니다."));
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error("잘못된 JSON 형식입니다."));
      }
    });
    req.on("error", reject);
  });
}

// 같은 도시를 반복 조회할 때 Open-Meteo 호출을 줄여 요청 한도(429)에 덜 걸리도록 캐싱한다.
const WEATHER_CACHE_TTL_MS = 10 * 60 * 1000; // 10분
const weatherCache = new Map(); // "lat,lon" -> { data, timestamp }

function weatherCacheKey(lat, lon) {
  return `${lat.toFixed(2)},${lon.toFixed(2)}`;
}

async function handleWeather(req, res, searchParams) {
  const lat = Number(searchParams.get("lat"));
  const lon = Number(searchParams.get("lon"));
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "lat, lon 쿼리 파라미터가 필요합니다." }));
    return;
  }

  const key = weatherCacheKey(lat, lon);
  const cached = weatherCache.get(key);
  const now = Date.now();

  if (cached && now - cached.timestamp < WEATHER_CACHE_TTL_MS) {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(cached.data));
    return;
  }

  try {
    const url = new URL("https://api.open-meteo.com/v1/forecast");
    url.searchParams.set("latitude", lat);
    url.searchParams.set("longitude", lon);
    url.searchParams.set(
      "current",
      "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation"
    );
    url.searchParams.set("hourly", "temperature_2m,weather_code,precipitation_probability");
    url.searchParams.set(
      "daily",
      "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    );
    url.searchParams.set("timezone", "Asia/Seoul");
    url.searchParams.set("forecast_days", "7");

    const upstreamRes = await fetch(url.toString());
    const data = await upstreamRes.json().catch(() => null);

    if (!upstreamRes.ok || !data) {
      // 업스트림이 요청 한도 등으로 실패했을 때, 예전 캐시라도 있으면 그걸 내려준다.
      if (cached) {
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ ...cached.data, _stale: true }));
        return;
      }
      const message = data?.reason || `날씨 API 오류 (HTTP ${upstreamRes.status})`;
      res.writeHead(upstreamRes.status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: message }));
      return;
    }

    weatherCache.set(key, { data, timestamp: now });
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(data));
  } catch (err) {
    if (cached) {
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ ...cached.data, _stale: true }));
      return;
    }
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "날씨 API 호출 중 오류가 발생했습니다: " + err.message }));
  }
}

async function handleChat(req, res) {
  if (!OPENAI_API_KEY) {
    res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "서버에 OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요." }));
    return;
  }

  let parsed;
  try {
    parsed = await readJsonBody(req);
  } catch (err) {
    res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: err.message }));
    return;
  }

  const messages = Array.isArray(parsed.messages) ? parsed.messages : [];
  const isValidMessage = (m) =>
    m && typeof m.content === "string" && ["system", "user", "assistant"].includes(m.role);

  if (messages.length === 0 || !messages.every(isValidMessage)) {
    res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "messages 형식이 올바르지 않습니다." }));
    return;
  }

  try {
    const openaiRes = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({ model: OPENAI_MODEL, messages, temperature: 0.5 }),
    });

    const data = await openaiRes.json().catch(() => ({}));

    if (!openaiRes.ok) {
      res.writeHead(openaiRes.status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: data?.error?.message || `OpenAI API 오류 (HTTP ${openaiRes.status})` }));
      return;
    }

    const reply = data.choices?.[0]?.message?.content?.trim() || "";
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ reply }));
  } catch (err) {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "OpenAI API 호출 중 오류가 발생했습니다: " + err.message }));
  }
}

const server = http.createServer((req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "POST" && parsedUrl.pathname === "/api/chat") {
    handleChat(req, res);
    return;
  }
  if (req.method === "GET" && parsedUrl.pathname === "/api/weather") {
    handleWeather(req, res, parsedUrl.searchParams);
    return;
  }
  if (req.method === "GET" || req.method === "HEAD") {
    serveStatic(req, res);
    return;
  }
  res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("Method Not Allowed");
});

server.listen(PORT, () => {
  console.log(`Weather app server running at http://localhost:${PORT}`);
  if (!OPENAI_API_KEY) {
    console.warn("경고: OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일에 OPENAI_API_KEY=sk-... 를 추가하세요.");
  }
});
