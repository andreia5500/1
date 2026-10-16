/* Дача PRO — дашборд одной карточкой (custom:dacha-pro-card). v2.0.0 */
const E = {
  alarm: "alarm_control_panel.alarmo",
  power: "sensor.summa_moshchnostei",
  mainPower: "sensor.avtomat_63a_obshchii_z2_power",
  mainVolt: "sensor.avtomat_63a_obshchii_z2_voltage",
  mainCurrent: "sensor.avtomat_63a_obshchii_z2_current",
  mainEnergy: "sensor.avtomat_63a_obshchii_z2_energy",
  mainSw: "switch.avtomat_63a_obshchii_z2",
  heatPower: "sensor.0x385b44fffe95c528_power",
  heatVolt: "sensor.0x385b44fffe95c528_voltage",
  heatEnergy: "sensor.0x385b44fffe95c528_energy",
  heatSw: "switch.0x385b44fffe95c528",
  plita: "switch.plita_380",
  septik: "switch.0x0c4314fffe54b11f",
  septikPower: "sensor.0x0c4314fffe54b11f_power",
  outTemp: "sensor.yandex_weather_temperature",
  weather: ["weather.yandex_weather", "weather.forecast_home_assistant"],
  inTemp: "sensor.0xa4c138c3897b0e8d_temperature",
  minZone: "sensor.min_temp_zhiloi_zony",
  doors: "binary_sensor.dveri_dacha",
  leak: "binary_sensor.protechki_dacha",
  smoke: "binary_sensor.dym_i_co_dacha",
  ups: "sensor.myups_battery_charge",
  upsVolt: "sensor.myups_input_voltage",
  upsStatus: "sensor.myups_status_data",
  fps: "sensor.frigate_detection_fps",
  heatEta: "sensor.otoplenie_vremia_do_progreva",
  heatZonePower: "sensor.otoplenie_moshchnost_zhiloi_zony",
  heatDuty: "automation.otoplenie_dezhurnyi_rezhim_stupeni",
  season: "input_boolean.bassein_sezon_otkryt",
  poolTemp: "sensor.0xa4c1380cdb14ffff_temperature",
  poolFilter: "switch.0xa4c138d89acf4e98",
  poolHeat: "switch.0x70b3d52b600ab5b6",
  poolFlow: "binary_sensor.0xa4c138bf5d7ee1b8_water_leak",
  poolSmart: "automation.umnyi_filtr_basseina",
  poolStatus: "sensor.status_filtratsii",
  barrelTemp: "sensor.0xa4c138e3964a27b2_temperature",
  soil: "sensor.0xa4c1384c85f8d435_soil_moisture",
  autoWater: "automation.poliv_avtomaticheskii",
  cpu: "sensor.system_monitor_processor_use",
  cpuTemp: "sensor.system_monitor_processor_temperature",
  mem: "sensor.system_monitor_memory_usage",
  disk: "sensor.system_monitor_disk_usage",
  backupOk: "sensor.backup_last_successful_automatic_backup",
  backupState: "sensor.backup_state",
  os: "sensor.home_assistant_operating_system_version",
};

const CLIMATE = [
  { name: "Комната", climate: "climate.temperatura_komnata", temp: "sensor.0xa4c138c3897b0e8d_temperature", heater: "switch.0xa4c138d117a0a7ae", power: "sensor.0xa4c138d117a0a7ae_power", color: "var(--blue)" },
  { name: "Кухня", climate: "climate.temperatura_kukhnia", temp: "sensor.0xa4c1387166d89ee9_temperature", heater: "switch.0xa4c138477e1d1b01", power: "sensor.0xa4c138477e1d1b01_power", color: "var(--orange)" },
  { name: "Тамбур", climate: "climate.temperatura_tambur", temp: "sensor.0xa4c13856cdfde690_temperature", heater: "switch.obogrev_tambur_z2", power: "sensor.obogrev_tambur_z2_power", color: "var(--grey)" },
];
// Ступени обогрева жилой зоны
const STAGES = ["switch.0xa4c138d117a0a7ae", "switch.0xa4c138477e1d1b01", "switch.0xa4c1388cfa5f06ae"];
const HEATERS = [
  ["Комната", "switch.0xa4c138d117a0a7ae"],
  ["Кухня", "switch.0xa4c138477e1d1b01"],
  ["Лестница", "switch.0xa4c1388cfa5f06ae"],
  ["Тамбур", "switch.obogrev_tambur_z2"],
];
const PRESETS = [["away", "Дежурный", "mdi:home-export-outline"], ["home", "Дома", "mdi:home-outline"], ["comfort", "Комфорт", "mdi:sofa-outline"]];

const LIGHTS = [
  { group: "Улица", items: [["Улица", "switch.svet_ulitsa_z2", "mdi:coach-lamp"], ["Баня", "switch.svet_bania_z2", "mdi:outdoor-lamp"], ["Терраса", "switch.svet_terrasa_z2", "mdi:ceiling-light"]] },
  { group: "1 этаж", items: [["Туал.", "switch.0xa4c1382800b07340", "mdi:toilet"], ["Комн. 1", "switch.0xa4c1387e50957968_left", "mdi:ceiling-light-outline"], ["Комн. 2", "switch.0xa4c1387e50957968_right", "mdi:ceiling-light-outline"], ["Спальня", "switch.0xa4c138459a6af661", "mdi:bed-outline"]] },
  { group: "2 этаж", items: [["Л1", "switch.0xa4c138a71f7d780b_l1", "mdi:lightbulb-outline"], ["Л2", "switch.0xa4c138a71f7d780b_l2", "mdi:lightbulb-outline"], ["Л3", "switch.0xa4c138a71f7d780b_l3", "mdi:lightbulb-outline"], ["Л4", "switch.0xa4c138a71f7d780b_l4", "mdi:lightbulb-outline"]] },
];

const LOADS = [
  ["Вода", "switch.0xa4c13841d4a7bb3a", "mdi:water-pump"],
  ["Вытяжка", "switch.0xa4c138150cd653bd", "mdi:fan"],
  ["Бойлер", "switch.obogrev_lestnitsa", "mdi:water-boiler"],
  ["Пол туал.", "switch.0xa4c13859b38594c2", "mdi:heating-coil"],
  ["Штора", "cover.0x7cc6b6fffec1a5dd", "mdi:curtains"],
  ["Пылесос", "vacuum.robot_pylesos_dacha_robot_pylesos_dacha", "mdi:robot-vacuum"],
];

const WATERING = [["Газон", "switch.0xa4c138850a555bb4_l1", "mdi:grass"], ["Клубника", "switch.0xa4c138850a555bb4_l2", "mdi:fruit-cherries"], ["Бочка", "switch.0xa4c138850a555bb4_l3", "mdi:barrel"]];

const CAMERAS = [
  ["Ворота", "camera.auto_door"],
  ["Вход", "camera.front_door"],
  ["Баня", "camera.banya"],
  ["Терраса", "camera.terrasa"],
  ["Бассейн", "camera.bassein"],
  ["Дом", "camera.dom3"],
];
const CAM_WHERE = { auto_door: "у ворот", front_door: "у входа", banya: "у бани", terrasa: "на террасе", bassein: "у бассейна", dom3: "у дома", ulica: "на улице" };

const WEATHER_ICON = {
  "clear-night": "mdi:weather-night", sunny: "mdi:weather-sunny", partlycloudy: "mdi:weather-partly-cloudy",
  cloudy: "mdi:weather-cloudy", rainy: "mdi:weather-rainy", pouring: "mdi:weather-pouring",
  snowy: "mdi:weather-snowy", "snowy-rainy": "mdi:weather-snowy", fog: "mdi:weather-fog",
};

// Базовый размер, под который свёрстана сетка; на экране она масштабируется целиком
const BASE_W = 1180, BASE_H = 760, MOBILE_W = 760;

const BAD = ["unknown", "unavailable", "", undefined, null];
const nf = (v, d = 1) => Number(v).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(Math.abs(v), d);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const hm = (d) => d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
const dur = (min) => {
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return h ? `${h} ч ${m} мин` : `${m} мин`;
};
const ic = (name, cls = "") => `<ha-icon class="i ${cls}" icon="${name}"></ha-icon>`;

class DachaProCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hist = {};
    this._nav = "overview";
    this._theme = null;
    this._fit = { mobile: false, style: "" };
    try { this._theme = localStorage.getItem("dacha-pro-theme"); } catch (e) { /* storage недоступен */ }
  }

  setConfig(config) { this._config = config || {}; }
  getCardSize() { return 12; }
  getGridOptions() { return { columns: "full" }; }

  connectedCallback() {
    if (!document.getElementById("dacha-pro-font")) {
      const l = document.createElement("link");
      l.id = "dacha-pro-font";
      l.rel = "stylesheet";
      l.href = "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap";
      document.head.appendChild(l);
    }
    this._clock = setInterval(() => this._render(true), 30000);
    this._histTimer = setInterval(() => this._loadHistory(), 5 * 60000);
    this._onResize = () => this._measure();
    window.addEventListener("resize", this._onResize);
    this._ro = new ResizeObserver(() => this._measure());
    this._ro.observe(this);
    if (this._hass) this._loadHistory();
    requestAnimationFrame(() => this._measure());
  }

  disconnectedCallback() {
    clearInterval(this._clock);
    clearInterval(this._histTimer);
    window.removeEventListener("resize", this._onResize);
    if (this._ro) this._ro.disconnect();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._loadHistory();
    this._render();
  }

  /* Подгонка под экран: сетка всегда занимает ровно видимую область без прокрутки */
  _measure() {
    const w = this.clientWidth;
    if (!w) return;
    const top = this.getBoundingClientRect().top + (window.scrollY || 0);
    const h = Math.max(320, window.innerHeight - Math.max(0, top));
    let fit;
    if (w < MOBILE_W || this._config.fit === false) {
      fit = { mobile: w < MOBILE_W, style: "" };
    } else {
      const s = Math.max(0.55, Math.min(w / BASE_W, h / BASE_H, this._config.max_scale || 1.4));
      const useZoom = CSS.supports("zoom", "1");
      const size = `width:${(w / s).toFixed(1)}px;height:${(h / s).toFixed(1)}px;`;
      fit = {
        mobile: false,
        style: useZoom ? `${size}zoom:${s.toFixed(4)};` : `${size}transform:scale(${s.toFixed(4)});transform-origin:0 0;`,
        hostH: h,
      };
    }
    const key = JSON.stringify(fit);
    if (key === this._fitKey) return;
    this._fitKey = key;
    this._fit = fit;
    this.style.height = fit.hostH ? `${fit.hostH}px` : "";
    this.style.overflow = fit.hostH ? "hidden" : "";
    this._render(true);
  }

  /* ---------- данные ---------- */
  st(id) { return this._hass && this._hass.states[id]; }
  s(id) { const o = this.st(id); return o ? o.state : undefined; }
  on(id) { return this.s(id) === "on"; }
  n(id) {
    const v = this.s(id);
    if (BAD.includes(v)) return null;
    const x = parseFloat(v);
    return Number.isFinite(x) ? x : null;
  }
  a(id, attr) { const o = this.st(id); return o ? o.attributes[attr] : undefined; }

  weatherEntity() { return E.weather.find((w) => this.st(w) && !BAD.includes(this.s(w))) || E.outTemp; }

  outside() {
    const t = this.n(E.outTemp);
    for (const w of E.weather) {
      const o = this.st(w);
      if (o && !BAD.includes(o.state)) {
        const wind = o.attributes.wind_speed;
        const unit = o.attributes.wind_speed_unit || "km/h";
        const ms = wind == null ? null : unit === "m/s" ? wind : wind / 3.6;
        return { t: t ?? o.attributes.temperature, wind: ms, cond: o.state };
      }
    }
    return { t, wind: null, cond: null };
  }

  async _loadHistory() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    const end = new Date();
    const start = new Date(end.getTime() - 24 * 3600e3);
    const ids = [E.power, E.poolTemp, E.poolFilter, E.mainEnergy, E.heatEnergy, ...CLIMATE.map((c) => c.temp)];
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: ids,
        minimal_response: true,
        no_attributes: true,
        significant_changes_only: false,
      });
      const out = {};
      for (const id of ids) {
        out[id] = (res[id] || []).map((p) => ({ t: (p.lu ?? p.lc) * 1000, s: p.s }));
      }
      this._hist = out;
      this._histAt = end;
      this._render(true);
    } catch (e) {
      console.warn("dacha-pro-card: history", e);
    } finally {
      this._loading = false;
    }
  }

  // ряд значений с шагом step мс за последние hours часов (перенос последнего значения)
  series(id, hours = 24, step = 15 * 60e3) {
    const pts = (this._hist[id] || []).filter((p) => !BAD.includes(p.s) && Number.isFinite(parseFloat(p.s)));
    if (!pts.length) return [];
    const end = Date.now();
    const start = end - hours * 3600e3;
    const out = [];
    let i = 0, cur = null;
    for (let t = start; t <= end; t += step) {
      while (i < pts.length && pts[i].t <= t) cur = parseFloat(pts[i++].s);
      if (cur === null && i === 0) cur = parseFloat(pts[0].s);
      out.push(cur);
    }
    const live = this.n(id);
    if (live !== null) out[out.length - 1] = live;
    return out;
  }

  energyDay() {
    let sum = 0, ok = false;
    for (const id of [E.mainEnergy, E.heatEnergy]) {
      const pts = (this._hist[id] || []).map((p) => parseFloat(p.s)).filter(Number.isFinite);
      const now = this.n(id);
      if (pts.length && now !== null) { sum += Math.max(0, now - pts[0]); ok = true; }
    }
    return ok ? sum : null;
  }

  filterWindows() {
    const pts = this._hist[E.poolFilter] || [];
    const end = Date.now(), start = end - 24 * 3600e3;
    const wins = [];
    let open = null;
    for (const p of pts) {
      const t = Math.max(p.t, start);
      if (p.s === "on" && open === null) open = t;
      else if (p.s !== "on" && open !== null) { wins.push([open, t]); open = null; }
    }
    if (open !== null) wins.push([open, end]);
    const total = wins.reduce((m, [a, b]) => m + (b - a), 0) / 60e3;
    return { wins: wins.map(([a, b]) => [(a - start) / (end - start), (b - start) / (end - start)]), total };
  }

  heatRate() {
    const s = this.series(CLIMATE[0].temp, 2, 10 * 60e3).filter((v) => v !== null);
    if (s.length < 3) return null;
    return (s[s.length - 1] - s[0]) / 2;
  }

  /* ---------- графики ---------- */
  path(vals, w, h, min, max, pad = 2) {
    const pts = vals.map((v, i) => [
      (i / Math.max(1, vals.length - 1)) * w,
      v === null ? null : pad + (1 - (v - min) / (max - min || 1)) * (h - pad * 2),
    ]).filter((p) => p[1] !== null);
    if (pts.length < 2) return "";
    let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
      const cx = (x0 + x1) / 2;
      d += ` C${cx.toFixed(1)},${y0.toFixed(1)} ${cx.toFixed(1)},${y1.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`;
    }
    return d;
  }

  spark(vals, { fill = true, color = "var(--blue)", cls = "spark" } = {}) {
    const v = vals.filter((x) => x !== null);
    if (v.length < 2) return `<div class="${cls}"></div>`;
    const w = 300, h = 60;
    let min = Math.min(...v), max = Math.max(...v);
    if (max - min < 1e-6) { min -= 1; max += 1; }
    const d = this.path(vals, w, h, min, max);
    const area = fill ? `<path d="${d} L${w},${h} L0,${h} Z" fill="var(--spark-fill)"/>` : "";
    return `<svg class="${cls}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${area}<path d="${d}" fill="none" stroke="${color}" stroke-width="1.8" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>`;
  }

  climateChart() {
    const series = CLIMATE.map((c) => this.series(c.temp, 24));
    const all = series.flat().filter((x) => x !== null);
    const w = 600, h = 130;
    if (all.length < 2) return `<div class="chart chart-empty">загрузка истории…</div>`;
    const min = Math.floor(Math.min(...all) - 1), max = Math.ceil(Math.max(...all) + 1);
    const grid = [0.25, 0.5, 0.75, 1].map((f) => `<line x1="0" x2="${w}" y1="${(h * f).toFixed(1)}" y2="${(h * f).toFixed(1)}" stroke="var(--grid)" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join("");
    const lines = series.map((s, i) => `<path d="${this.path(s, w, h, min, max, 6)}" fill="none" stroke="${CLIMATE[i].color}" stroke-width="1.8" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`).join("");
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${grid}${lines}</svg>`;
  }

  /* ---------- блоки ---------- */
  chip(name, id, icon, opts = {}) {
    const st = this.s(id);
    const active = opts.active ?? (["on", "open", "opening", "cleaning", "heat"].includes(st));
    const off = BAD.includes(st);
    return `<button class="chip ${active ? "on" : ""} ${off ? "na" : ""}" data-act="${opts.act || "toggle"}" data-id="${id}" title="${esc(name)}">${ic(icon)}<span class="lbl">${esc(name)}</span></button>`;
  }

  head(icon, title, meta = "") {
    return `<div class="ch"><span class="ct">${ic(icon)}<span class="eyebrow">${title}</span></span>${meta ? `<span class="meta">${meta}</span>` : ""}</div>`;
  }

  status() {
    if (this.on(E.leak)) return { text: "Протечка! Вода перекрыта", lvl: "bad" };
    if (this.on(E.smoke)) return { text: "Дым или CO!", lvl: "bad" };
    if (this.s(E.alarm) === "triggered") return { text: "Тревога!", lvl: "bad" };
    if (this.on(E.doors)) return { text: "Открыта дверь", lvl: "warn" };
    if (this.s(E.upsStatus) && !String(this.s(E.upsStatus)).startsWith("OL")) return { text: "Работа от ИБП", lvl: "warn" };
    return { text: "Всё спокойно", lvl: "ok" };
  }

  doorCount() {
    const members = this.a(E.doors, "entity_id") || [];
    const open = members.filter((m) => this.on(m)).length;
    return { total: members.length, open };
  }

  batteries() {
    const skip = /myups|24117|mi_pad|robot_pylesos/;
    const list = Object.values(this._hass.states).filter((o) =>
      o.entity_id.startsWith("sensor.") && o.entity_id.endsWith("_battery") && !skip.test(o.entity_id) &&
      o.attributes.unit_of_measurement === "%" && !BAD.includes(o.state));
    const vals = list.map((o) => parseFloat(o.state)).filter(Number.isFinite);
    if (!vals.length) return { text: "—", cls: "" };
    const low = vals.filter((v) => v < 20).length;
    const min = Math.min(...vals);
    if (low) return { text: `${low} ниже 20 % · мин ${Math.round(min)} %`, cls: "warn" };
    return { text: `все выше ${Math.floor(min / 10) * 10} %`, cls: "" };
  }

  backup() {
    const v = this.s(E.backupOk);
    if (BAD.includes(v)) return { text: "нет данных", cls: "warn" };
    const d = new Date(v), now = new Date();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400e3);
    const when = diff === 0 ? "сегодня" : diff === 1 ? "вчера" : d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
    const err = this.s(E.backupState) === "error";
    return { text: `${err ? "ошибка · " : ""}${when} ${hm(d)}`, cls: err || diff > 2 ? "warn" : "" };
  }

  lastPerson() {
    let best = null;
    for (const key of Object.keys(CAM_WHERE)) {
      const o = this.st(`binary_sensor.${key}_person_occupancy`);
      if (!o || BAD.includes(o.state)) continue;
      const active = o.state === "on";
      const t = active ? new Date() : new Date(o.last_changed);
      if (!active && Date.now() - t > 24 * 3600e3) continue;
      if (!best || t > best.t) best = { t, key, active };
    }
    return best;
  }

  presetNow() {
    const ps = CLIMATE.map((c) => this.a(c.climate, "preset_mode")).filter(Boolean);
    return ps.length && ps.every((p) => p === ps[0]) ? ps[0] : null;
  }

  /* ---------- рендер ---------- */
  _render(force = false) {
    if (!this._hass || !this.shadowRoot) return;
    if (!force) {
      if (this._raf) return;
      this._raf = requestAnimationFrame(() => { this._raf = null; this._draw(); });
      return;
    }
    this._draw();
  }

  _draw() {
    const html = this._html();
    if (html === this._last) return;
    this._last = html;
    this.shadowRoot.innerHTML = `<style>${STYLES}</style>${html}`;
    this._bind();
  }

  /* --- летние и зимние карточки --- */
  poolCard() {
    const pool = this.n(E.poolTemp);
    const fw = this.filterWindows();
    const flow = this.on(E.poolFlow);
    const smartOn = this.on(E.poolSmart);
    const meta = `поток ${flow ? "есть" : "<b class='warn'>нет</b>"} · ${smartOn ? "по расписанию" : esc(this.s(E.poolStatus) || "вручную")}`;
    return `<div class="card a-heat" id="sec-pool">
      ${this.head("mdi:pool", "Бассейн", meta)}
      <div class="pool-top">
        <div class="big tap" data-act="more" data-id="${E.poolTemp}">${pool === null ? "—" : nf(pool, 1) + "°"}<small>вода</small></div>
        ${this.spark(this.series(E.poolTemp, 24), { fill: false, cls: "spark spark-pool" })}
      </div>
      <div class="track">${fw.wins.map(([a, b]) => `<i style="left:${(a * 100).toFixed(2)}%;width:${Math.max(0.6, (b - a) * 100).toFixed(2)}%"></i>`).join("")}</div>
      <div class="cf"><span>окна фильтрации за сутки</span><span>${fw.total ? dur(fw.total) : "0 мин"}</span></div>
      <div class="chips n3 grow-end">
        ${this.chip("Фильтр", E.poolFilter, "mdi:air-filter")}
        ${this.chip("Нагрев", E.poolHeat, "mdi:fire")}
        ${this.chip("Умный", E.poolSmart, "mdi:robot-outline")}
      </div>
    </div>`;
  }

  heatingCard() {
    const preset = this.presetNow();
    const rows = CLIMATE.map((c) => {
      const cur = this.a(c.climate, "current_temperature") ?? this.n(c.temp);
      const tgt = this.a(c.climate, "temperature");
      const heating = this.on(c.heater);
      return `<div class="trow">
        <span class="tname tap" data-act="more" data-id="${c.climate}">${ic("mdi:radiator", heating ? "hot" : "")}${c.name}</span>
        <span class="tcur">${cur == null ? "—" : sgn(cur, 1) + "°"}</span>
        <span class="tset">
          <button class="rb" data-act="tdown" data-id="${c.climate}" title="Ниже">${ic("mdi:minus")}</button>
          <span class="tval">${tgt == null ? "—" : nf(tgt, 1) + "°"}</span>
          <button class="rb" data-act="tup" data-id="${c.climate}" title="Выше">${ic("mdi:plus")}</button>
        </span>
      </div>`;
    }).join("");
    return `<div class="card a-heat" id="sec-pool">
      <div class="ch"><span class="ct">${ic("mdi:radiator")}<span class="eyebrow">Отопление</span></span>
        <span class="seg mini">${PRESETS.map(([k, t, i]) => `<button class="${preset === k ? "sel" : ""}" data-act="preset" data-id="${k}" title="${t}">${ic(i)}<span>${t}</span></button>`).join("")}</span>
      </div>
      <div class="thead"><span>помещение</span><span>сейчас</span><span>цель</span></div>
      <div class="trows">${rows}</div>
    </div>`;
  }

  wateringCard() {
    return `<div class="card a-side" id="sec-water">
      ${this.head("mdi:sprinkler-variant", "Полив", `бочка ${this.tmp(this.n(E.barrelTemp))}`)}
      <div class="chips n2">
        ${WATERING.map(([n, id, i]) => this.chip(n, id, i)).join("")}
        <button class="chip" data-act="stopwater">${ic("mdi:stop-circle-outline")}<span class="lbl">Стоп</span></button>
      </div>
      <div class="list grow-end">
        <div class="row tap" data-act="more" data-id="${E.soil}"><span>${ic("mdi:water-percent")}Теплица</span><span class="val">${this.n(E.soil) === null ? "—" : Math.round(this.n(E.soil)) + " %"}</span></div>
        <div class="row tap" data-act="toggle" data-id="${E.autoWater}"><span>${ic("mdi:calendar-clock")}Автополив</span><span class="val">${this.on(E.autoWater) ? "по расписанию" : "выключен"}</span></div>
      </div>
    </div>`;
  }

  heatersCard() {
    const eta = this.n(E.heatEta);
    const zp = this.n(E.heatZonePower);
    return `<div class="card a-side" id="sec-water">
      ${this.head("mdi:snowflake-thermometer", "Обогреватели", zp ? `${nf(zp, 1)} кВт` : "")}
      <div class="chips n2">${HEATERS.map(([n, id]) => this.chip(n, id, "mdi:radiator")).join("")}</div>
      <div class="list grow-end">
        <div class="row tap" data-act="more" data-id="${E.heatEta}"><span>${ic("mdi:home-thermometer-outline")}До прогрева</span><span class="val">${eta ? "~" + dur(eta * 60) : "—"}</span></div>
        <div class="row tap" data-act="toggle" data-id="${E.heatDuty}"><span>${ic("mdi:robot-outline")}Дежурный режим</span><span class="val">${this.on(E.heatDuty) ? "включён" : "выключен"}</span></div>
      </div>
    </div>`;
  }

  tmp(x) { return x === null ? "—" : `${sgn(x, 1)}°`; }

  _html() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
    const theme = this._theme || "dark";
    const status = this.status();
    const out = this.outside();
    const ups = this.n(E.ups), upsV = this.n(E.upsVolt), fps = this.n(E.fps);
    const upsOk = String(this.s(E.upsStatus) || "OL").startsWith("OL");
    const temp = (x) => this.tmp(x);
    const v = (x, d = 1, suf = "") => (x === null ? "—" : nf(x, d) + suf);
    const summer = this.on(E.season);
    const wEnt = this.weatherEntity();

    /* охрана */
    const al = this.s(E.alarm);
    const alText = { disarmed: "Снято с охраны", armed_away: "На охране", armed_home: "Охрана · дома", armed_night: "Охрана · ночь", arming: "Постановка…", pending: "Ожидание…", triggered: "Тревога!" }[al] || "Нет связи";
    const dc = this.doorCount();
    const armed = al && al.startsWith("armed");

    /* энергия */
    const p = this.n(E.power);
    const kwh = this.energyDay();
    const mainV = this.n(E.mainVolt);
    const mainA = this.n(E.mainCurrent);

    /* климат */
    const inT = this.n(E.inTemp), minZ = this.n(E.minZone);
    const stage = STAGES.filter((id) => this.on(id)).length;
    const rate = this.heatRate();
    const eta = this.n(E.heatEta);
    const targets = CLIMATE.map((c) => this.a(c.climate, "temperature")).filter((x) => x != null);
    const maxTarget = targets.length ? Math.max(...targets) : null;
    const climMeta = [
      `ступень ${stage} из ${STAGES.length}`,
      rate !== null ? `≈${nf(rate, 2)} °C/ч` : null,
      maxTarget !== null ? `до ${sgn(maxTarget, 0)}°${eta ? ` ~${dur(eta * 60)}` : ""}` : null,
    ].filter(Boolean).join(" · ");

    /* свет */
    const lightIds = LIGHTS.flatMap((g) => g.items.map((i) => i[1]));
    const lightsOn = lightIds.filter((id) => this.on(id)).length;

    /* камеры */
    const lp = this.lastPerson();
    const camMeta = lp ? (lp.active ? `человек ${CAM_WHERE[lp.key]} · сейчас` : `человек ${CAM_WHERE[lp.key]} · ${hm(lp.t)}`) : "людей не было";

    /* система */
    const bat = this.batteries();
    const bk = this.backup();
    const osv = this.s(E.os);
    const host = this._config.host_label || (osv && !BAD.includes(osv) ? `HAOS ${osv}` : "");

    const climateCards = CLIMATE.map((c) => {
      const cur = this.a(c.climate, "current_temperature") ?? this.n(c.temp);
      const tgt = this.a(c.climate, "temperature");
      const heating = this.on(c.heater);
      const pw = this.n(c.power);
      const sub = heating ? `обогрев ${pw !== null && pw > 0 ? nf(pw / 1000, 1) + " кВт" : "вкл"}` : "обогрев выкл";
      return `<div class="room tap" data-act="more" data-id="${c.climate}">
        <div class="room-h"><span class="room-n"><i class="dotc" style="background:${c.color}"></i>${c.name}</span><span class="muted">${tgt != null ? `цель ${Math.round(tgt)}°` : ""}</span></div>
        <div class="big2">${temp(cur)}</div>
        <div class="muted ${heating ? "hot" : ""}">${sub}</div>
      </div>`;
    }).join("");

    const loadTile = (title, icon, value, sub, id, onState) => `
      <div class="load tap ${onState ? "on" : ""}" data-act="more" data-id="${id}">
        <div class="load-h">${ic(icon)}<span>${title}</span></div>
        <div class="load-v">${value}</div>
        <div class="muted">${sub}</div>
      </div>`;
    const septP = this.n(E.septikPower);
    const septOn = this.on(E.septik);
    const plitaOn = this.on(E.plita);
    const heatP = this.n(E.heatPower), mainP = this.n(E.mainPower);
    const W = (x) => (x === null ? "—" : `${Math.round(x).toLocaleString("ru-RU")} Вт`);

    const NAV = [
      ["overview", "Обзор", "mdi:view-dashboard-outline"], ["light", "Свет", "mdi:lightbulb-outline"],
      ["climate", "Климат", "mdi:thermometer"],
      summer ? ["pool", "Бассейн", "mdi:pool"] : ["pool", "Отопл.", "mdi:radiator"],
      summer ? ["water", "Полив", "mdi:sprinkler-variant"] : ["water", "Обогрев", "mdi:snowflake-thermometer"],
      ["cams", "Камеры", "mdi:cctv"], ["energy", "Энергия", "mdi:lightning-bolt-outline"], ["system", "Система", "mdi:server-outline"],
    ];

    return `
<div class="root theme-${theme} ${this._fit.mobile ? "mobile" : "fit"}" style="${this._fit.style}">
  <aside class="rail">
    <div class="logo" title="${esc(this._config.title || "Дача")}">${esc((this._config.title || "Дача").slice(0, 1))}</div>
    <nav>${NAV.map(([k, t, i]) => `<button class="nav ${this._nav === k ? "active" : ""}" data-act="nav" data-id="${k}">${ic(i)}<span>${t}</span></button>`).join("")}</nav>
    <div class="upd">${hm(this._histAt || now)}</div>
  </aside>

  <main class="main">
    <header class="top">
      <div class="ttl">
        <div class="eyebrow">${esc(this._config.title || "Дача")} · ${esc(dateStr)} · ${hm(now)}</div>
        <h1 class="title lvl-${status.lvl}">${status.text}</h1>
      </div>
      <div class="pills">
        <span class="seg season">
          <button class="${summer ? "sel" : ""}" data-act="season" data-id="on">${ic("mdi:white-balance-sunny")}<span>Лето</span></button>
          <button class="${summer ? "" : "sel"}" data-act="season" data-id="off">${ic("mdi:snowflake")}<span>Зима</span></button>
        </span>
        <span class="pill tap" data-act="more" data-id="${wEnt}">${ic(WEATHER_ICON[out.cond] || "mdi:weather-partly-cloudy")}${temp(out.t)}</span>
        <span class="pill tap ${upsOk ? "" : "warn"}" data-act="more" data-id="${E.ups}">${ic("mdi:battery-charging-high")}ИБП ${ups === null ? "—" : Math.round(ups) + "%"}${upsV !== null ? ` · ${Math.round(upsV)} В` : ""}</span>
        <span class="pill tap" data-act="more" data-id="${E.fps}">${ic("mdi:cctv")}${v(fps, 1)} fps</span>
        <button class="pill icon" data-act="theme" title="Тема">${ic(theme === "dark" ? "mdi:weather-sunny" : "mdi:weather-night")}</button>
      </div>
    </header>

    <section class="grid">
      <div class="card a-sec" id="sec-security">
        ${this.head(armed ? "mdi:shield-lock-outline" : "mdi:shield-off-outline", "Охрана", `${dc.total} зон`)}
        <div class="h2 ${al === "triggered" ? "bad" : ""}">${alText}</div>
        <div class="muted ${dc.open ? "warn" : ""}">${dc.open ? `открыто дверей: ${dc.open}` : "все двери закрыты"}</div>
        <div class="btns grow-end">
          <button class="btn ${armed ? "primary" : ""}" data-act="disarm">${ic("mdi:home-outline")}Я дома</button>
          <button class="btn ${armed ? "" : "primary"}" data-act="arm">${ic("mdi:home-export-outline")}Ухожу</button>
        </div>
      </div>

      <div class="card a-pow tap" id="sec-energy" data-act="more" data-id="${E.power}">
        ${this.head("mdi:lightning-bolt-outline", "Мощность сети", "сейчас")}
        <div class="pow">
          <div class="big">${p === null ? "—" : Math.round(p).toLocaleString("ru-RU")}<small>Вт</small></div>
          ${this.spark(this.series(E.power, 12, 10 * 60e3))}
        </div>
        <div class="cf grow-end"><span>Общий 63 А · ${v(mainV, 0)} В</span><span>сутки ${kwh === null ? "—" : nf(kwh, 1)} кВт·ч</span></div>
      </div>

      <div class="card a-tmp split">
        <div class="half tap" data-act="more" data-id="${wEnt}">
          <span class="ct">${ic("mdi:tree-outline")}<span class="eyebrow">На улице</span></span>
          <div class="big">${temp(out.t)}</div>
          <div class="muted">${out.wind === null ? "&nbsp;" : `ветер ${Math.round(out.wind)} м/с`}</div>
        </div>
        <div class="vsep"></div>
        <div class="half tap" data-act="more" data-id="${E.inTemp}">
          <span class="ct">${ic("mdi:home-thermometer-outline")}<span class="eyebrow">В доме</span></span>
          <div class="big">${temp(inT)}</div>
          <div class="muted">мин. зона ${temp(minZ)}</div>
        </div>
      </div>

      <div class="card a-sens">
        ${this.head("mdi:shield-check-outline", "Датчики")}
        <div class="list">
          <div class="row tap" data-act="more" data-id="${E.doors}"><span>${ic("mdi:door", dc.open ? "warn" : "")}Двери</span><span class="val ${dc.open ? "warn" : ""}">${dc.open ? `открыто · ${dc.open}` : `закрыты · ${dc.total}`}</span></div>
          <div class="row tap" data-act="more" data-id="${E.leak}"><span>${ic("mdi:water-alert", this.on(E.leak) ? "bad" : "")}Протечка</span><span class="val ${this.on(E.leak) ? "bad" : ""}">${this.on(E.leak) ? "ПРОТЕЧКА" : "сухо"} · ${(this.a(E.leak, "entity_id") || []).length || 1}</span></div>
          <div class="row tap" data-act="more" data-id="${E.smoke}"><span>${ic("mdi:smoke-detector-variant", this.on(E.smoke) ? "bad" : "")}Дым и CO</span><span class="val ${this.on(E.smoke) ? "bad" : ""}">${this.on(E.smoke) ? "ТРЕВОГА" : "норма"} · ${(this.a(E.smoke, "entity_id") || []).length || 1}</span></div>
        </div>
      </div>

      <div class="card a-clim" id="sec-climate">
        ${this.head("mdi:thermometer", "Климат", esc(climMeta))}
        <div class="rooms">${climateCards}</div>
        ${this.climateChart()}
        <div class="cf"><span class="legend">${CLIMATE.map((c) => `<span><i style="background:${c.color}"></i>${c.name}</span>`).join("")}</span><span>24 часа</span></div>
      </div>

      <div class="card a-light" id="sec-light">
        ${this.head("mdi:lightbulb-group-outline", "Свет", `включено ${lightsOn} из ${lightIds.length}`)}
        <div class="lgroups">
          ${LIGHTS.map((g) => `<div class="lg"><span class="sub">${g.group}</span><div class="chips n4">${g.items.map(([n, id, i]) => this.chip(n, id, i)).join("")}</div></div>`).join("")}
        </div>
      </div>

      ${summer ? this.poolCard() : this.heatingCard()}

      <div class="card a-load" id="sec-loads">
        ${this.head("mdi:flash-outline", "Нагрузки и автоматы", `суммарно ${p === null ? "—" : nf(p / 1000, 2)} кВт`)}
        <div class="loads">
          ${loadTile("Общий 63 А", "mdi:meter-electric-outline", W(mainP), `${v(mainV, 0)} В${mainA !== null ? ` · ${nf(mainA, 1)} А` : ""}`, E.mainSw, this.on(E.mainSw))}
          ${loadTile("Обогрев", "mdi:radiator", W(heatP), `${v(this.n(E.heatVolt), 0)} В`, E.heatSw, this.on(E.heatSw))}
          ${loadTile("Плита 380", "mdi:stove", plitaOn ? "Вкл" : "Выкл", "резерв нагрева", E.plita, plitaOn)}
          ${loadTile("Септик", "mdi:pipe-valve", septP === null ? (septOn ? "Вкл" : "Выкл") : W(septP), septOn ? "обогрев" : "простой", E.septik, septOn)}
        </div>
        <div class="chips n3 grow-end">${LOADS.map(([n, id, i]) => this.chip(n, id, i, { act: id.startsWith("vacuum.") ? "more" : "toggle" })).join("")}</div>
      </div>

      ${summer ? this.wateringCard() : this.heatersCard()}

      <div class="card a-cam" id="sec-cams">
        ${this.head("mdi:cctv", "Камеры", esc(camMeta))}
        <div class="cams">${CAMERAS.map(([n, id]) => {
          const pic = this.a(id, "entity_picture");
          const src = pic ? this._hass.hassUrl(pic) : "";
          return `<div class="cam tap" data-act="more" data-id="${id}"><div class="shot">${src ? `<img src="${esc(src)}" loading="lazy" alt="">` : ""}</div><span>${n}</span></div>`;
        }).join("")}</div>
      </div>

      <div class="card a-sys" id="sec-system">
        ${this.head("mdi:server-outline", "Система", esc(host))}
        <div class="list sys">
          <div class="row tap" data-act="more" data-id="${E.cpu}"><span>${ic("mdi:cpu-64-bit")}Процессор</span><span class="val">${v(this.n(E.cpu), 0, " %")} · ${v(this.n(E.cpuTemp), 0, " °C")}</span></div>
          <div class="row tap" data-act="more" data-id="${E.mem}"><span>${ic("mdi:memory")}Память · диск</span><span class="val">${v(this.n(E.mem), 0, " %")} · ${v(this.n(E.disk), 0, " %")}</span></div>
          <div class="row tap" data-act="more" data-id="${E.backupOk}"><span>${ic("mdi:cloud-upload-outline")}Бэкап</span><span class="val ${bk.cls}">${bk.text}</span></div>
          <div class="row"><span>${ic("mdi:battery-70")}Батареи</span><span class="val ${bat.cls}">${bat.text}</span></div>
        </div>
      </div>
    </section>
  </main>
</div>`;
  }

  _bind() {
    this.shadowRoot.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this._action(el.dataset.act, el.dataset.id);
      });
    });
  }

  async _call(domain, service, data) {
    try {
      await this._hass.callService(domain, service, data);
    } catch (e) {
      console.warn("dacha-pro-card", e);
      if (data && typeof data.entity_id === "string") this._more(data.entity_id);
    }
  }

  _more(entityId) {
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  _setTemp(id, dir) {
    const o = this.st(id);
    if (!o) return;
    const step = Math.max(0.5, o.attributes.target_temp_step || 0.5);
    const cur = o.attributes.temperature ?? o.attributes.current_temperature ?? 20;
    const min = o.attributes.min_temp ?? 5, max = o.attributes.max_temp ?? 30;
    const next = Math.min(max, Math.max(min, Math.round((cur + dir * step) / step) * step));
    this._call("climate", "set_temperature", { entity_id: id, temperature: next });
  }

  _action(act, id) {
    switch (act) {
      case "more": return this._more(id);
      case "toggle": {
        const st = this.s(id);
        if (BAD.includes(st)) return this._more(id);
        const dom = id.split(".")[0];
        if (dom === "cover") return this._call("cover", "toggle", { entity_id: id });
        if (dom === "automation") return this._call("automation", st === "on" ? "turn_off" : "turn_on", { entity_id: id });
        return this._call("homeassistant", "toggle", { entity_id: id });
      }
      case "tup": return this._setTemp(id, 1);
      case "tdown": return this._setTemp(id, -1);
      case "preset": {
        for (const c of CLIMATE) {
          const modes = this.a(c.climate, "preset_modes") || [];
          const mode = modes.includes(id) ? id : id === "comfort" && modes.includes("home") ? "home" : null;
          if (mode) this._call("climate", "set_preset_mode", { entity_id: c.climate, preset_mode: mode });
        }
        return;
      }
      case "arm": return this._call("alarm_control_panel", "alarm_arm_away", { entity_id: E.alarm });
      case "disarm": return this._call("alarm_control_panel", "alarm_disarm", { entity_id: E.alarm });
      case "season": return this._call("input_boolean", id === "on" ? "turn_on" : "turn_off", { entity_id: E.season });
      case "stopwater": return this._call("switch", "turn_off", { entity_id: WATERING.map((w) => w[1]) });
      case "theme": {
        this._theme = (this._theme || "dark") === "dark" ? "light" : "dark";
        try { localStorage.setItem("dacha-pro-theme", this._theme); } catch (e) { /* storage недоступен */ }
        return this._render(true);
      }
      case "nav": {
        this._nav = id;
        if (id === "cams" && this._config.cameras_path) {
          history.pushState(null, "", this._config.cameras_path);
          window.dispatchEvent(new CustomEvent("location-changed"));
          return;
        }
        const target = {
          overview: null, light: "sec-light", climate: "sec-climate", pool: "sec-pool", water: "sec-water",
          cams: "sec-cams", energy: "sec-loads", system: "sec-system",
        }[id];
        this._render(true);
        const el = target && this.shadowRoot.getElementById(target);
        if (el) {
          if (this._fit.mobile) el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("flash");
          setTimeout(() => el.classList.remove("flash"), 1400);
        }
        return;
      }
    }
  }
}

const STYLES = `
:host { display:block; }
.root {
  --bg:#121315; --rail:#16171a; --card:#18191c; --card2:#1d1e22; --line:#2a2b30; --line2:#232428;
  --text:#f3f3f5; --muted:#9b9ca3; --faint:#6d6e75; --blue:#8ab9ec; --blue-bg:#1f2c3d; --blue-text:#a4cbf3;
  --orange:#e6a24a; --grey:#a9aab0; --red:#ef6b63; --warn:#e6a24a; --grid:#25262a; --spark-fill:rgba(138,185,236,.14);
  --primary-btn:#8ab9ec; --primary-btn-text:#0f1a26; --icon:#8b8c93;
  font-family: Inter, -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
  font-size:13px; color:var(--text); background:var(--bg);
  display:grid; grid-template-columns:64px minmax(0,1fr); box-sizing:border-box;
  -webkit-font-smoothing:antialiased; font-feature-settings:"tnum" 1, "cv11" 1;
}
.root.theme-light {
  --bg:#f2f2f0; --rail:#e9e8e5; --card:#ffffff; --card2:#f7f7f5; --line:#e1e0dc; --line2:#ecebe7;
  --text:#18191c; --muted:#6b6c72; --faint:#a3a4a9; --blue:#3b82c9; --blue-bg:#e2edf9; --blue-text:#245f9e;
  --orange:#d48a2a; --grey:#8d8e94; --grid:#ecebe7; --spark-fill:rgba(59,130,201,.12); --primary-btn:#3b82c9; --primary-btn-text:#fff; --icon:#85868c;
}
.root.fit { overflow:hidden; }
.root.mobile { min-height:calc(100vh - var(--header-height, 56px)); }
*, *::before, *::after { box-sizing:border-box; }
button { font:inherit; color:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; }
.tap { cursor:pointer; }
.i { --mdc-icon-size:16px; width:16px; height:16px; color:var(--icon); flex:none; display:inline-flex; }
.i.hot { color:var(--orange); } .i.warn { color:var(--warn); } .i.bad { color:var(--red); }
.eyebrow { font-size:10px; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
.muted { color:var(--muted); font-size:12px; }
.warn { color:var(--warn); } .bad { color:var(--red); }

/* rail */
.rail { background:var(--rail); border-right:1px solid var(--line2); display:flex; flex-direction:column; align-items:center; padding:12px 6px 10px; gap:4px; min-height:0; }
.logo { width:36px; height:36px; border-radius:11px; background:var(--blue-bg); color:var(--blue-text); display:flex; align-items:center; justify-content:center; font-weight:600; font-size:17px; margin-bottom:10px; }
nav { display:flex; flex-direction:column; gap:3px; width:100%; }
.nav { display:flex; flex-direction:column; align-items:center; gap:3px; border:0; background:none; border-radius:10px; padding:7px 2px 6px; font-size:10px; color:var(--muted); width:100%; }
.nav .i { --mdc-icon-size:20px; width:20px; height:20px; }
.nav:hover { background:var(--card2); }
.nav.active { background:var(--blue-bg); color:var(--blue-text); font-weight:500; }
.nav.active .i { color:var(--blue); }
.upd { margin-top:auto; font-size:10px; color:var(--faint); }

/* main */
.main { padding:12px 14px 14px; min-width:0; min-height:0; display:flex; flex-direction:column; gap:10px; }
.top { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
.title { font-size:22px; font-weight:600; letter-spacing:-.02em; margin:3px 0 0; line-height:1.15; }
.title.lvl-bad { color:var(--red); } .title.lvl-warn { color:var(--warn); }
.pills { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.pill { display:inline-flex; align-items:center; gap:7px; height:34px; padding:0 12px; border:1px solid var(--line); border-radius:10px; background:var(--card); font-size:13px; font-weight:500; white-space:nowrap; }
.pill .i { color:var(--blue); }
.pill.warn .i { color:var(--warn); }
.pill.icon { width:34px; justify-content:center; padding:0; }
.pill.icon .i { color:var(--muted); }
.seg { display:inline-flex; gap:2px; padding:3px; border:1px solid var(--line); border-radius:10px; background:var(--card); }
.seg button { display:inline-flex; align-items:center; gap:6px; border:0; background:none; border-radius:7px; height:26px; padding:0 10px; font-size:12.5px; color:var(--muted); }
.seg button .i { color:inherit; }
.seg button.sel { background:var(--primary-btn); color:var(--primary-btn-text); font-weight:500; }
.seg.mini button { height:22px; padding:0 7px; font-size:11px; gap:4px; }
.seg.mini .i { --mdc-icon-size:13px; width:13px; height:13px; }

/* сетка: 12 колонок, 4 ряда, на планшете всё помещается в экран */
.grid { flex:1; min-height:0; display:grid; gap:10px;
  grid-template-columns:repeat(12, minmax(0,1fr));
  grid-template-rows:minmax(0,0.67fr) minmax(0,0.95fr) minmax(0,1fr) minmax(0,0.8fr);
  grid-template-areas:
    "sec sec sec pow pow pow tmp tmp tmp sns sns sns"
    "clm clm clm clm clm clm lgt lgt lgt lgt lgt lgt"
    "heat heat heat heat lod lod lod lod lod sid sid sid"
    "cam cam cam cam cam cam cam sys sys sys sys sys"; }
.a-sec { grid-area:sec; } .a-pow { grid-area:pow; } .a-tmp { grid-area:tmp; } .a-sens { grid-area:sns; }
.a-clim { grid-area:clm; } .a-light { grid-area:lgt; } .a-heat { grid-area:heat; } .a-load { grid-area:lod; }
.a-side { grid-area:sid; } .a-cam { grid-area:cam; } .a-sys { grid-area:sys; }

.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:11px 13px 12px; min-width:0; min-height:0; overflow:hidden; display:flex; flex-direction:column; transition:box-shadow .3s, border-color .3s; }
.card.flash { border-color:var(--blue); box-shadow:0 0 0 3px var(--blue-bg); }
.grow-end { margin-top:auto; }
.ch { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:7px; min-height:18px; flex:none; }
.ct { display:inline-flex; align-items:center; gap:7px; white-space:nowrap; }
.ct .i { --mdc-icon-size:15px; width:15px; height:15px; color:var(--blue); }
.meta { color:var(--muted); font-size:11.5px; text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
.meta b { font-weight:500; }
.h2 { font-size:17px; font-weight:600; letter-spacing:-.01em; }
.big { font-size:30px; font-weight:300; letter-spacing:-.02em; line-height:1.1; white-space:nowrap; }
.big small { font-size:12px; font-weight:400; color:var(--muted); letter-spacing:0; margin-left:5px; }
.big2 { font-size:22px; font-weight:300; letter-spacing:-.01em; margin:3px 0 1px; }
.cf { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-top:6px; font-size:11.5px; color:var(--muted); }

.btns { display:grid; grid-template-columns:1fr 1fr; gap:8px; padding-top:8px; }
.btn { display:inline-flex; align-items:center; justify-content:center; gap:7px; height:34px; border-radius:9px; border:1px solid var(--line); background:var(--card2); font-size:13px; font-weight:500; }
.btn.primary { background:var(--primary-btn); color:var(--primary-btn-text); border-color:transparent; }
.btn.primary .i { color:inherit; }

.pow { display:flex; align-items:flex-end; gap:12px; flex:1; min-height:0; }
.spark { flex:1; min-width:0; height:100%; max-height:46px; display:block; }
.pool-top { display:flex; align-items:center; gap:12px; flex:1; min-height:0; }
.spark-pool { max-height:52px; }
.chart { width:100%; flex:1; min-height:30px; display:block; margin-top:8px; }
.chart-empty { display:flex; align-items:center; justify-content:center; color:var(--faint); font-size:12px; }

.split { flex-direction:row; gap:12px; }
.split .half { flex:1; min-width:0; display:flex; flex-direction:column; }
.split .big { margin-top:8px; }
.split .muted { margin-top:2px; }
.vsep { width:1px; background:var(--line); }

.list { display:flex; flex-direction:column; }
.row { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:4px 0; border-bottom:1px solid var(--line2); font-size:13px; min-height:25px; }
.row > span:first-child { display:inline-flex; align-items:center; gap:8px; }
.row:last-child { border-bottom:0; }
.row .val { color:var(--muted); font-size:12px; text-align:right; white-space:nowrap; }
.row .val.warn { color:var(--warn); } .row .val.bad { color:var(--red); }
.sys { flex:1; justify-content:space-between; }

.rooms { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:8px; }
.room { border:1px solid var(--line); border-radius:11px; padding:8px 11px; }
.room-h { display:flex; justify-content:space-between; align-items:baseline; gap:6px; }
.room-n { font-size:13px; font-weight:600; display:inline-flex; align-items:center; gap:6px; }
.dotc { width:6px; height:6px; border-radius:50%; display:inline-block; }
.room .muted { font-size:11px; }
.hot { color:var(--orange) !important; }
.legend { display:flex; gap:14px; }
.legend span { display:inline-flex; align-items:center; gap:6px; }
.legend i { width:6px; height:6px; border-radius:50%; display:inline-block; }

.track { position:relative; height:5px; border-radius:3px; background:var(--line); margin-top:8px; overflow:hidden; flex:none; }
.track i { position:absolute; top:0; bottom:0; background:var(--blue); border-radius:3px; }

.lgroups { flex:1; display:flex; flex-direction:column; justify-content:space-between; gap:6px; min-height:0; }
.lg { display:grid; grid-template-columns:52px minmax(0,1fr); align-items:center; gap:8px; }
.sub { color:var(--muted); font-size:11.5px; }
.chips { display:grid; gap:7px; }
.chips.n2 { grid-template-columns:repeat(2, minmax(0,1fr)); }
.chips.n3 { grid-template-columns:repeat(3, minmax(0,1fr)); }
.chips.n4 { grid-template-columns:repeat(4, minmax(0,1fr)); }
.chip { display:flex; align-items:center; gap:8px; height:34px; padding:0 10px; border-radius:9px; border:1px solid var(--line); background:var(--card); font-size:13px; font-weight:500; text-align:left; min-width:0; transition:background .15s, border-color .15s; }
.chip .lbl { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.chip:hover { border-color:var(--faint); }
.chip.on { background:var(--blue-bg); border-color:transparent; color:var(--blue-text); }
.chip.on .i { color:var(--blue); }
.chip.na { opacity:.45; }

.loads { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:7px; margin-bottom:8px; }
.load { border:1px solid var(--line); border-radius:10px; padding:6px 9px; min-width:0; }
.load.on { border-color:var(--blue-bg); }
.load-h { display:flex; align-items:center; gap:6px; font-size:12px; font-weight:600; white-space:nowrap; }
.load.on .load-h .i { color:var(--blue); }
.load-v { font-size:17px; font-weight:300; margin:3px 0 0; white-space:nowrap; }
.load .muted { font-size:10.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* отопление */
.thead { display:grid; grid-template-columns:minmax(0,1fr) 62px 118px; gap:8px; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); padding:0 2px 4px; }
.thead span:nth-child(n+2) { text-align:center; }
.trows { flex:1; display:flex; flex-direction:column; justify-content:space-around; min-height:0; }
.trow { display:grid; grid-template-columns:minmax(0,1fr) 62px 118px; gap:8px; align-items:center; padding:4px 2px; border-bottom:1px solid var(--line2); }
.trow:last-child { border-bottom:0; }
.tname { display:inline-flex; align-items:center; gap:8px; font-weight:500; white-space:nowrap; }
.tcur { font-size:17px; font-weight:300; text-align:center; }
.tset { display:grid; grid-template-columns:32px 1fr 32px; align-items:center; gap:4px; }
.tval { text-align:center; font-size:15px; font-weight:500; color:var(--blue-text); }
.rb { width:32px; height:30px; border-radius:8px; border:1px solid var(--line); background:var(--card2); display:flex; align-items:center; justify-content:center; padding:0; }
.rb .i { color:var(--text); }
.rb:active { background:var(--blue-bg); }

.cams { flex:1; min-height:0; display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:8px; }
.cam { display:flex; flex-direction:column; min-height:0; }
.cam span { color:var(--muted); font-size:11.5px; margin-top:4px; }
.shot { flex:1; min-height:0; border:1px solid var(--line); border-radius:8px; background:var(--card2); overflow:hidden; }
.shot img { width:100%; height:100%; object-fit:cover; display:block; }

/* телефон: обычная прокрутка в одну колонку */
.root.mobile { grid-template-columns:minmax(0,1fr); grid-template-rows:auto 1fr; }
.mobile .rail { flex-direction:row; padding:8px; gap:6px; position:sticky; top:var(--header-height, 56px); z-index:2; overflow-x:auto; border-right:0; border-bottom:1px solid var(--line2); }
.mobile .logo { margin:0; flex:none; }
.mobile nav { flex-direction:row; width:auto; }
.mobile .nav { width:58px; flex:none; }
.mobile .upd { display:none; }
.mobile .main { padding:12px; }
.mobile .grid { display:flex; flex-direction:column; }
.mobile .card { overflow:visible; }
.mobile .chart { height:110px; flex:none; }
.mobile .spark { height:46px; }
.mobile .rooms { grid-template-columns:1fr 1fr 1fr; }
.mobile .loads { grid-template-columns:repeat(2, minmax(0,1fr)); }
.mobile .cams { grid-template-columns:repeat(3, minmax(0,1fr)); }
.mobile .shot { aspect-ratio:16/10; flex:none; }
.mobile .lg { grid-template-columns:1fr; gap:4px; }
`;

if (!customElements.get("dacha-pro-card")) customElements.define("dacha-pro-card", DachaProCard);
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "dacha-pro-card")) {
  window.customCards.push({ type: "dacha-pro-card", name: "Дача PRO", description: "Дашборд дачи одной карточкой" });
}
