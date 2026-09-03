// 날씨 챗봇. OpenAI API 키는 서버(.env)에만 보관되고,
// 프론트는 이 서버가 제공하는 /api/chat 엔드포인트만 호출한다.

let chatHistory = [];

function buildWeatherSummaryText(city, data) {
  const current = data.current;
  const weather = describeWeatherCode(current.weather_code);
  const todayMax = Math.round(data.daily.temperature_2m_max[0]);
  const todayMin = Math.round(data.daily.temperature_2m_min[0]);
  const pop = data.daily.precipitation_probability_max[0];

  return [
    `도시: ${city.name}`,
    `현재 날씨: ${weather.label}, 기온 ${Math.round(current.temperature_2m)}°C (체감 ${Math.round(current.apparent_temperature)}°C)`,
    `습도 ${current.relative_humidity_2m}%, 풍속 ${current.wind_speed_10m}km/h, 강수량 ${current.precipitation}mm`,
    `오늘 최고/최저 기온: ${todayMax}°C / ${todayMin}°C, 강수확률 ${pop}%`,
  ].join("\n");
}

function resetChat(city, weatherSummaryText) {
  chatHistory = [
    {
      role: "system",
      content:
        `당신은 한국어로 답하는 친절한 날씨 도우미입니다. ` +
        `사용자가 지금 보고 있는 도시와 날씨 정보는 다음과 같습니다:\n${weatherSummaryText}\n\n` +
        `이 정보를 바탕으로 우산 필요 여부, 옷차림, 야외활동 적합도 같은 질문에 자연스럽고 간결하게 한국어로 답하세요. ` +
        `제공된 정보에 없는 것은 추측하지 말고 모른다고 답하세요.`,
    },
  ];

  const messagesEl = document.getElementById("chat-messages");
  if (messagesEl) messagesEl.innerHTML = "";
}

function appendChatMessage(role, text) {
  const messagesEl = document.getElementById("chat-messages");
  if (!messagesEl) return null;
  const bubble = document.createElement("div");
  bubble.className = `chat-msg chat-msg-${role}`;
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

function setupChat(city, data) {
  const summary = buildWeatherSummaryText(city, data);
  resetChat(city, summary);
  appendChatMessage("system", `${city.name} 날씨에 대해 무엇이든 물어보세요. (예: 우산 챙겨야 할까?)`);

  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  if (!form || !input) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendChatMessage(text);
  });
}

async function sendChatMessage(userText) {
  appendChatMessage("user", userText);
  chatHistory.push({ role: "user", content: userText });

  const loadingBubble = appendChatMessage("assistant", "생각 중...");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.error || `서버 오류 (HTTP ${res.status})`);
    }

    const reply = data.reply || "(빈 응답을 받았어요)";
    chatHistory.push({ role: "assistant", content: reply });
    loadingBubble.textContent = reply;
  } catch (err) {
    loadingBubble.textContent = `⚠️ ${err.message}`;
    loadingBubble.classList.add("chat-msg-error");
  }
}
