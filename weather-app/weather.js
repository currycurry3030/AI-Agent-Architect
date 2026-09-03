// Open-Meteo 날씨 데이터를 우리 서버(/api/weather)를 통해 받아온다.
// 서버가 응답을 캐싱하기 때문에 브라우저에서 Open-Meteo를 직접 호출할 때보다
// 요청 한도(429)에 덜 걸린다. (원본: https://open-meteo.com/en/docs)

const WEATHER_CODES = {
  0: { label: "맑음", icon: "☀️" },
  1: { label: "대체로 맑음", icon: "🌤️" },
  2: { label: "구름 조금", icon: "⛅" },
  3: { label: "흐림", icon: "☁️" },
  45: { label: "안개", icon: "🌫️" },
  48: { label: "짙은 안개", icon: "🌫️" },
  51: { label: "이슬비(약)", icon: "🌦️" },
  53: { label: "이슬비(보통)", icon: "🌦️" },
  55: { label: "이슬비(강)", icon: "🌦️" },
  56: { label: "어는 이슬비", icon: "🌧️" },
  57: { label: "어는 이슬비(강)", icon: "🌧️" },
  61: { label: "비(약)", icon: "🌧️" },
  63: { label: "비(보통)", icon: "🌧️" },
  65: { label: "비(강)", icon: "🌧️" },
  66: { label: "어는 비", icon: "🌨️" },
  67: { label: "어는 비(강)", icon: "🌨️" },
  71: { label: "눈(약)", icon: "🌨️" },
  73: { label: "눈(보통)", icon: "🌨️" },
  75: { label: "눈(강)", icon: "❄️" },
  77: { label: "싸락눈", icon: "❄️" },
  80: { label: "소나기(약)", icon: "🌦️" },
  81: { label: "소나기(보통)", icon: "🌦️" },
  82: { label: "소나기(강)", icon: "⛈️" },
  85: { label: "소낙눈(약)", icon: "🌨️" },
  86: { label: "소낙눈(강)", icon: "🌨️" },
  95: { label: "뇌우", icon: "⛈️" },
  96: { label: "뇌우(우박 약)", icon: "⛈️" },
  99: { label: "뇌우(우박 강)", icon: "⛈️" },
};

function describeWeatherCode(code) {
  return WEATHER_CODES[code] || { label: "알 수 없음", icon: "❔" };
}

const WEEKDAYS_KR = ["일", "월", "화", "수", "목", "금", "토"];

async function fetchWeather(lat, lon) {
  const url = new URL("/api/weather", window.location.origin);
  url.searchParams.set("lat", lat);
  url.searchParams.set("lon", lon);

  const res = await fetch(url.toString());
  const data = await res.json().catch(() => null);

  if (!res.ok || !data) {
    throw new Error(data?.error || `날씨 정보를 불러오지 못했습니다 (HTTP ${res.status})`);
  }
  return data;
}
