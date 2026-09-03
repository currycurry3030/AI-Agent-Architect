const map = L.map("map", { zoomControl: true }).setView([36.2, 127.9], 7);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
}).addTo(map);

const panel = document.getElementById("panel");
const markers = {};
let activeCity = null;

const cityIcon = L.divIcon({
  className: "city-marker",
  html: '<div class="city-marker-dot"></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

CITIES.forEach((city) => {
  const marker = L.marker([city.lat, city.lon], { icon: cityIcon }).addTo(map);
  const onSelect = () => selectCity(city, marker);

  marker.on("click", onSelect);

  // permanent 툴팁은 이미 지도에 추가된 마커에 bindTooltip을 호출하는 순간
  // 곧바로(동기적으로) 열리므로, 리스너는 bindTooltip 호출 "전"에 걸어야 놓치지 않는다.
  marker.on("tooltipopen", (e) => {
    const labelEl = e.tooltip.getElement();
    if (labelEl) labelEl.addEventListener("click", onSelect);
  });

  marker.bindTooltip(city.name, { permanent: true, direction: "top", offset: [0, -8], className: "city-label" });

  markers[city.name] = marker;
});

function setActiveMarker(name) {
  Object.entries(markers).forEach(([cityName, marker]) => {
    const el = marker.getElement();
    if (!el) return;
    el.classList.toggle("active", cityName === name);
  });
}

async function selectCity(city, marker) {
  activeCity = city.name;
  setActiveMarker(city.name);
  map.panTo([city.lat, city.lon]);

  renderLoading(city);

  try {
    const data = await fetchWeather(city.lat, city.lon);
    if (activeCity !== city.name) return; // 다른 도시를 그새 클릭했다면 무시
    renderWeather(city, data);
  } catch (err) {
    if (activeCity !== city.name) return;
    renderError(city, err);
  }
}

function renderLoading(city) {
  panel.classList.remove("panel-empty");
  panel.innerHTML = `
    <div class="panel-header">
      <h2>${city.name}</h2>
    </div>
    <div class="panel-loading">날씨 정보를 불러오는 중...</div>
  `;
}

function renderError(city, err) {
  panel.innerHTML = `
    <div class="panel-header">
      <h2>${city.name}</h2>
    </div>
    <div class="panel-error">⚠️ ${err.message}</div>
  `;
}

function renderWeather(city, data) {
  const current = data.current;
  const weather = describeWeatherCode(current.weather_code);
  const now = new Date();

  // 다음 12시간 예보 (현재 시각 이후) — API가 반환하는 current.time(KST 로컬 문자열) 기준으로 비교
  const hourlyItems = buildHourlyItems(data.hourly, 12, current.time);

  // 7일 예보
  const dailyItems = buildDailyItems(data.daily);

  panel.classList.remove("panel-empty");
  panel.innerHTML = `
    <div class="panel-header">
      <h2>${city.name}</h2>
      <span class="updated">업데이트: ${now.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</span>
    </div>

    <div class="section chat-section">
      <h3>💬 날씨 챗봇 (OpenAI)</h3>
      <div id="chat-messages" class="chat-messages"></div>
      <form id="chat-form" class="chat-form" autocomplete="off">
        <input id="chat-input" type="text" placeholder="예: 우산 챙겨야 할까?" />
        <button type="submit">전송</button>
      </form>
    </div>

    <div class="current-weather">
      <div class="current-icon">${weather.icon}</div>
      <div class="current-main">
        <div class="current-temp">${Math.round(current.temperature_2m)}°C</div>
        <div class="current-label">${weather.label}</div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span class="detail-label">체감온도</span>
        <span class="detail-value">${Math.round(current.apparent_temperature)}°C</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">습도</span>
        <span class="detail-value">${current.relative_humidity_2m}%</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">풍속</span>
        <span class="detail-value">${current.wind_speed_10m} km/h</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">강수량</span>
        <span class="detail-value">${current.precipitation} mm</span>
      </div>
    </div>

    <div class="section">
      <h3>시간별 예보</h3>
      <div class="hourly-scroll">
        ${hourlyItems
          .map(
            (h) => `
          <div class="hourly-item">
            <span class="hourly-time">${h.time}</span>
            <span class="hourly-icon">${h.icon}</span>
            <span class="hourly-temp">${h.temp}°</span>
            <span class="hourly-pop">💧${h.pop}%</span>
          </div>`
          )
          .join("")}
      </div>
    </div>

    <div class="section">
      <h3>주간 예보</h3>
      <div class="daily-list">
        ${dailyItems
          .map(
            (d) => `
          <div class="daily-item">
            <span class="daily-day">${d.day}</span>
            <span class="daily-icon">${d.icon}</span>
            <span class="daily-label">${d.label}</span>
            <span class="daily-temp"><b>${d.max}°</b> / ${d.min}°</span>
          </div>`
          )
          .join("")}
      </div>
    </div>
  `;

  setupChat(city, data);
}

function buildHourlyItems(hourly, count, currentTimeIso) {
  // hourly.time과 currentTimeIso 모두 API가 준 KST 로컬 문자열이므로 그대로 비교 가능
  let startIdx = hourly.time.findIndex((t) => t >= currentTimeIso);
  if (startIdx === -1) startIdx = 0;

  const items = [];
  for (let i = startIdx; i < startIdx + count && i < hourly.time.length; i++) {
    const date = new Date(hourly.time[i]);
    const weather = describeWeatherCode(hourly.weather_code[i]);
    items.push({
      time: date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false }),
      icon: weather.icon,
      temp: Math.round(hourly.temperature_2m[i]),
      pop: hourly.precipitation_probability[i],
    });
  }
  return items;
}

function buildDailyItems(daily) {
  return daily.time.map((t, i) => {
    const date = new Date(t);
    const weather = describeWeatherCode(daily.weather_code[i]);
    const isToday = i === 0;
    return {
      day: isToday ? "오늘" : `${date.getMonth() + 1}/${date.getDate()} (${WEEKDAYS_KR[date.getDay()]})`,
      icon: weather.icon,
      label: weather.label,
      max: Math.round(daily.temperature_2m_max[i]),
      min: Math.round(daily.temperature_2m_min[i]),
    };
  });
}
