const DATA_URL = "./assets/data/port_liner_timetable.json";
const SETTINGS_URL = "./assets/config/app_settings.json";
const METADATA_URL = "./assets/config/app_metadata.json";
const TOKYO_TIMEZONE = "Asia/Tokyo";
const DAY_TYPE_LABELS = { weekday: "平日ダイヤ", holiday: "土日祝ダイヤ" };

const stationSelect = document.querySelector("#station-select");
const directionSelect = document.querySelector("#direction-select");
const clockValue = document.querySelector("#clock-value");
const dayTypeBadge = document.querySelector("#day-type-badge");
const fetchedAt = document.querySelector("#fetched-at");
const stationCode = document.querySelector("#station-code");
const statusText = document.querySelector("#status-text");
const siteTitle = document.querySelector("#site-title");
const siteDescription = document.querySelector("#site-description");
const versionBadge = document.querySelector("#version-badge");
const footerVersion = document.querySelector("#footer-version");
const changelogList = document.querySelector("#changelog-list");
const cards = Array.from(document.querySelectorAll(".train-card"));

const state = {
  data: null,
  settings: null,
  metadata: null,
  blinkOn: false,
};

function stationCodeSortKey(code) {
  const match = /^([A-Z]+)(\d+)$/.exec(code || "");
  if (!match) {
    return [code || "", 0];
  }
  return [match[1], Number(match[2])];
}

function activeTimezone() {
  return state.settings?.timezone || TOKYO_TIMEZONE;
}

function compareStationCodes(left, right) {
  const [leftPrefix, leftNumber] = stationCodeSortKey(left);
  const [rightPrefix, rightNumber] = stationCodeSortKey(right);
  if (leftPrefix !== rightPrefix) {
    return leftPrefix.localeCompare(rightPrefix, "ja");
  }
  return leftNumber - rightNumber;
}

function parseQuery() {
  const url = new URL(window.location.href);
  return {
    station: url.searchParams.get("station"),
    direction: url.searchParams.get("direction"),
  };
}

function getTokyoParts(date = new Date()) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: activeTimezone(),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(formatter.formatToParts(date).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    second: Number(parts.second),
  };
}

function formatTokyoDateTime(date = new Date()) {
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: activeTimezone(),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function logicalDate(year, month, day) {
  return new Date(Date.UTC(year, month - 1, day));
}

function addLogicalDays(date, days) {
  return new Date(date.getTime() + days * 24 * 60 * 60 * 1000);
}

function formatLogicalDate(date) {
  return date.toISOString().slice(0, 10);
}

function nthWeekday(year, month, weekday, nth) {
  const first = logicalDate(year, month, 1);
  const delta = (weekday - first.getUTCDay() + 7) % 7;
  return addLogicalDays(first, delta + (nth - 1) * 7);
}

function vernalEquinoxDay(year) {
  return Math.trunc(20.8431 + 0.242194 * (year - 1980) - Math.floor((year - 1980) / 4));
}

function autumnalEquinoxDay(year) {
  return Math.trunc(23.2488 + 0.242194 * (year - 1980) - Math.floor((year - 1980) / 4));
}

function logicalDateKey(date) {
  return formatLogicalDate(date);
}

function japaneseHolidays(year) {
  const holidays = new Set([
    logicalDateKey(logicalDate(year, 1, 1)),
    logicalDateKey(nthWeekday(year, 1, 1, 2)),
    logicalDateKey(logicalDate(year, 2, 11)),
    logicalDateKey(logicalDate(year, 3, vernalEquinoxDay(year))),
    logicalDateKey(logicalDate(year, 4, 29)),
    logicalDateKey(logicalDate(year, 5, 3)),
    logicalDateKey(logicalDate(year, 5, 5)),
    logicalDateKey(logicalDate(year, 9, autumnalEquinoxDay(year))),
    logicalDateKey(logicalDate(year, 11, 3)),
    logicalDateKey(logicalDate(year, 11, 23)),
    logicalDateKey(nthWeekday(year, 9, 1, 3)),
  ]);

  if (year >= 2020) {
    holidays.add(logicalDateKey(logicalDate(year, 2, 23)));
  }

  if (year === 2020) {
    holidays.add(logicalDateKey(logicalDate(2020, 7, 23)));
    holidays.add(logicalDateKey(logicalDate(2020, 8, 10)));
    holidays.add(logicalDateKey(logicalDate(2020, 7, 24)));
  } else if (year === 2021) {
    holidays.add(logicalDateKey(logicalDate(2021, 7, 22)));
    holidays.add(logicalDateKey(logicalDate(2021, 8, 8)));
    holidays.add(logicalDateKey(logicalDate(2021, 7, 23)));
  } else {
    holidays.add(logicalDateKey(nthWeekday(year, 7, 1, 3)));
    holidays.add(logicalDateKey(nthWeekday(year, 10, 1, 2)));
    if (year >= 2016) {
      holidays.add(logicalDateKey(logicalDate(year, 8, 11)));
    }
  }

  for (let month = 1; month <= 12; month += 1) {
    let current = logicalDate(year, month, 1);
    while (current.getUTCMonth() === month - 1) {
      const previous = addLogicalDays(current, -1);
      const next = addLogicalDays(current, 1);
      if (
        current.getUTCDay() >= 1 &&
        current.getUTCDay() <= 5 &&
        !holidays.has(logicalDateKey(current)) &&
        holidays.has(logicalDateKey(previous)) &&
        holidays.has(logicalDateKey(next))
      ) {
        holidays.add(logicalDateKey(current));
      }
      current = addLogicalDays(current, 1);
    }
  }

  Array.from(holidays)
    .sort()
    .forEach((holidayKey) => {
      const holiday = new Date(`${holidayKey}T00:00:00Z`);
      if (holiday.getUTCDay() !== 0) {
        return;
      }
      let substitute = addLogicalDays(holiday, 1);
      while (holidays.has(logicalDateKey(substitute))) {
        substitute = addLogicalDays(substitute, 1);
      }
      holidays.add(logicalDateKey(substitute));
    });

  return holidays;
}

function currentDayType(logicalTargetDate) {
  const holidaySet = japaneseHolidays(logicalTargetDate.getUTCFullYear());
  if (logicalTargetDate.getUTCDay() === 0 || logicalTargetDate.getUTCDay() === 6) {
    return "holiday";
  }
  return holidaySet.has(logicalDateKey(logicalTargetDate)) ? "holiday" : "weekday";
}

function sortedStations(data) {
  return [...(data.stations || [])].sort((left, right) => compareStationCodes(left.station_code, right.station_code));
}

function getStationByName(stationName) {
  return sortedStations(state.data).find((station) => station.station_name === stationName) || null;
}

function getDirectionNames(station) {
  return (station?.directions || []).map((direction) => direction.direction_name);
}

function resolveDefaults() {
  const query = parseQuery();
  const stations = sortedStations(state.data);
  const availableStationNames = stations.map((station) => station.station_name);

  const preferredStation = query.station || state.settings.default_station_name;
  const stationName = availableStationNames.includes(preferredStation) ? preferredStation : availableStationNames[0];
  const station = getStationByName(stationName);
  const directionNames = getDirectionNames(station);

  const preferredDirection = query.direction || state.settings.default_direction_name;
  const directionName = directionNames.includes(preferredDirection) ? preferredDirection : directionNames[0];

  return { stationName, directionName };
}

function fillStationOptions() {
  const stations = sortedStations(state.data);
  stationSelect.innerHTML = "";

  stations.forEach((station) => {
    const option = document.createElement("option");
    option.value = station.station_name;
    option.textContent = station.station_name;
    stationSelect.append(option);
  });
}

function fillDirectionOptions() {
  const station = getStationByName(stationSelect.value);
  const directions = getDirectionNames(station);
  directionSelect.innerHTML = "";

  directions.forEach((directionName) => {
    const option = document.createElement("option");
    option.value = directionName;
    option.textContent = directionName;
    directionSelect.append(option);
  });

  if (!directions.includes(directionSelect.value)) {
    directionSelect.value = directions[0] || "";
  }
}

function computeNextDepartures(stationName, directionName, nowParts) {
  const currentDate = logicalDate(nowParts.year, nowParts.month, nowParts.day);
  const currentAbsMinutes = nowParts.hour * 60 + nowParts.minute + nowParts.second / 60;
  const station = getStationByName(stationName);
  const direction = (station?.directions || []).find((item) => item.direction_name === directionName);

  if (!direction) {
    return [];
  }

  const results = [];

  for (let offset = 0; offset < 3; offset += 1) {
    const targetDate = addLogicalDays(currentDate, offset);
    const dayType = currentDayType(targetDate);
    const departures = direction.departures?.[dayType] || [];

    for (const departure of departures) {
      const departureAbsMinutes = offset * 1440 + departure.minutes;
      if (departureAbsMinutes <= currentAbsMinutes) {
        continue;
      }

      const departureDate = addLogicalDays(currentDate, Math.floor(departureAbsMinutes / 1440));
      const displayMinutes = departure.minutes % 1440;
      const displayHour = String(Math.floor(displayMinutes / 60)).padStart(2, "0");
      const displayMinute = String(displayMinutes % 60).padStart(2, "0");

      results.push({
        ...departure,
        timetable_time: departure.time,
        time: `${displayHour}:${displayMinute}`,
        date_label: formatLogicalDate(departureDate),
        day_type: dayType,
        day_type_label: DAY_TYPE_LABELS[dayType],
        is_next_day: formatLogicalDate(departureDate) > formatLogicalDate(currentDate),
        minutes_until: Math.max(0, Math.floor(departureAbsMinutes - currentAbsMinutes)),
      });

      if (results.length >= 3) {
        return results;
      }
    }
  }

  return results;
}

function renderCards(departures) {
  cards.forEach((card, index) => {
    const timeNode = card.querySelector(".card-time");
    const destinationNode = card.querySelector(".card-destination");
    const metaNode = card.querySelector(".card-meta");
    const departure = departures[index];

    if (!departure) {
      card.classList.remove("urgent", "blink");
      timeNode.textContent = "--:--";
      destinationNode.textContent = "該当なし";
      metaNode.textContent = "";
      return;
    }

    const whenLabel = departure.is_next_day ? "翌日" : "当日";
    const pieces = [`${whenLabel} ${departure.date_label}`, departure.day_type_label, `あと ${departure.minutes_until} 分`];
    if (departure.timetable_time !== departure.time) {
      pieces.push(`時刻表表記 ${departure.timetable_time}`);
    }
    if (departure.symbol) {
      pieces.push(`種別記号 ${departure.symbol}`);
    }

    timeNode.textContent = departure.time;
    destinationNode.textContent = departure.destination || directionSelect.value;
    metaNode.textContent = pieces.join(" / ");

    const urgent = departure.minutes_until <= 5;
    card.classList.toggle("urgent", urgent);
    card.classList.toggle("blink", urgent && state.blinkOn);
  });
}

function renderChangelog(entries) {
  changelogList.innerHTML = "";

  if (!Array.isArray(entries) || entries.length === 0) {
    const fallback = document.createElement("article");
    fallback.className = "changelog-entry";
    fallback.innerHTML = '<p class="changelog-entry-title">更新履歴はまだありません。</p>';
    changelogList.append(fallback);
    return;
  }

  entries.forEach((entry) => {
    const article = document.createElement("article");
    article.className = "changelog-entry";

    const header = document.createElement("div");
    header.className = "changelog-entry-header";

    const version = document.createElement("p");
    version.className = "changelog-entry-version";
    version.textContent = `ver${entry.version || "--"}`;
    header.append(version);

    const date = document.createElement("p");
    date.className = "changelog-entry-date";
    date.textContent = entry.date || "";
    header.append(date);

    const title = document.createElement("p");
    title.className = "changelog-entry-title";
    title.textContent = entry.title || "";

    article.append(header);
    article.append(title);

    if (Array.isArray(entry.items) && entry.items.length > 0) {
      const list = document.createElement("ul");
      list.className = "changelog-entry-items";
      entry.items.forEach((item) => {
        const node = document.createElement("li");
        node.textContent = item;
        list.append(node);
      });
      article.append(list);
    }

    changelogList.append(article);
  });
}

function refreshBoard() {
  const now = new Date();
  const nowParts = getTokyoParts(now);
  const logicalCurrentDate = logicalDate(nowParts.year, nowParts.month, nowParts.day);

  clockValue.textContent = formatTokyoDateTime(now);
  dayTypeBadge.textContent = DAY_TYPE_LABELS[currentDayType(logicalCurrentDate)];

  const station = getStationByName(stationSelect.value);
  stationCode.textContent = station?.station_code || "--";

  const departures = computeNextDepartures(stationSelect.value, directionSelect.value, nowParts);
  renderCards(departures);
}

function attachEvents() {
  stationSelect.addEventListener("change", () => {
    fillDirectionOptions();
    refreshBoard();
  });

  directionSelect.addEventListener("change", refreshBoard);
}

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`読み込みに失敗しました: ${url}`);
  }
  return response.json();
}

async function initialize() {
  try {
    const [data, settings, metadata] = await Promise.all([
      loadJson(DATA_URL),
      loadJson(SETTINGS_URL),
      loadJson(METADATA_URL),
    ]);
    state.data = data;
    state.settings = settings;
    state.metadata = metadata;

    document.title = `${settings.web_site_title || "トレイン発車 Web"} ver${metadata.version || "--"}`;
    siteTitle.textContent = settings.web_site_title || "トレイン発車 Web";
    siteDescription.textContent = settings.web_site_description || siteDescription.textContent;
    fetchedAt.textContent = data.fetched_at || "不明";
    versionBadge.textContent = `ver${metadata.version || "--"}`;
    footerVersion.textContent = `ver${metadata.version || "--"}`;
    renderChangelog(metadata.changelog || []);

    fillStationOptions();
    const defaults = resolveDefaults();
    stationSelect.value = defaults.stationName;
    fillDirectionOptions();
    const availableDirections = Array.from(directionSelect.options).map((option) => option.value);
    directionSelect.value = availableDirections.includes(defaults.directionName) ? defaults.directionName : availableDirections[0] || "";

    attachEvents();
    refreshBoard();

    statusText.textContent = `${data.line_name} の公開用ページを表示しています。Google Sites にはこの URL を埋め込んでください。`;
    window.setInterval(() => {
      state.blinkOn = !state.blinkOn;
      refreshBoard();
    }, 1000);
  } catch (error) {
    console.error(error);
    statusText.textContent = "公開用データの読み込みに失敗しました。";
  }
}

initialize();
