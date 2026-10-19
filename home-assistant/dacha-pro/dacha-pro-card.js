/* Дача PRO — дашборд для настенного планшета (custom:dacha-pro-card). v3.0.1 */
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
  heatEta: "sensor.otoplenie_vremia_do_progreva",
  heatZonePower: "sensor.otoplenie_moshchnost_zhiloi_zony",
  heatDuty: "automation.otoplenie_dezhurnyi_rezhim_stupeni",
  frostThr: "input_number.porog_zamorozki",
  warmUp: "automation.nagrev_doma",
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
  { name: "Комната", climate: "climate.temperatura_komnata", temp: "sensor.0xa4c138c3897b0e8d_temperature", heater: "switch.0xa4c138d117a0a7ae", power: "sensor.0xa4c138d117a0a7ae_power", color: "var(--c1)" },
  { name: "Кухня", climate: "climate.temperatura_kukhnia", temp: "sensor.0xa4c1387166d89ee9_temperature", heater: "switch.0xa4c138477e1d1b01", power: "sensor.0xa4c138477e1d1b01_power", color: "var(--c2)" },
  { name: "Тамбур", climate: "climate.temperatura_tambur", temp: "sensor.0xa4c13856cdfde690_temperature", heater: "switch.obogrev_tambur_z2", power: "sensor.obogrev_tambur_z2_power", color: "var(--c3)" },
];
const HEATERS = [
  ["Комната", "switch.0xa4c138d117a0a7ae"],
  ["Кухня", "switch.0xa4c138477e1d1b01"],
  ["Лестница", "switch.0xa4c1388cfa5f06ae"],
  ["Тамбур", "switch.obogrev_tambur_z2"],
];
const PRESETS = [["away", "Дежурный", "mdi:shield-home-outline"], ["home", "Дома", "mdi:home-outline"], ["comfort", "Комфорт", "mdi:sofa-outline"]];

const LIGHTS = [
  { group: "Улица", items: [["Улица", "switch.svet_ulitsa_z2", "mdi:coach-lamp"], ["Баня", "switch.svet_bania_z2", "mdi:outdoor-lamp"], ["Терраса", "switch.svet_terrasa_z2", "mdi:ceiling-light"]] },
  { group: "1 этаж", items: [["Туалет", "switch.0xa4c1382800b07340", "mdi:toilet"], ["Комната 1", "switch.0xa4c1387e50957968_left", "mdi:ceiling-light-outline"], ["Комната 2", "switch.0xa4c1387e50957968_right", "mdi:ceiling-light-outline"], ["Спальня", "switch.0xa4c138459a6af661", "mdi:bed-outline"]] },
  { group: "2 этаж", items: [["Л1", "switch.0xa4c138a71f7d780b_l1", "mdi:lightbulb-outline"], ["Л2", "switch.0xa4c138a71f7d780b_l2", "mdi:lightbulb-outline"], ["Л3", "switch.0xa4c138a71f7d780b_l3", "mdi:lightbulb-outline"], ["Л4", "switch.0xa4c138a71f7d780b_l4", "mdi:lightbulb-outline"]] },
];
const LIGHT_IDS = LIGHTS.flatMap((g) => g.items.map((i) => i[1]));

const LOADS = [
  ["Вода", "switch.0xa4c13841d4a7bb3a", "mdi:water-pump", ""],
  ["Вытяжка", "switch.0xa4c138150cd653bd", "mdi:fan", ""],
  ["Бойлер", "switch.obogrev_lestnitsa", "mdi:water-boiler", "heat"],
  ["Тёплый пол", "switch.0xa4c13859b38594c2", "mdi:heating-coil", "heat"],
  ["Штора", "cover.0x7cc6b6fffec1a5dd", "mdi:curtains", ""],
  ["Пылесос", "vacuum.robot_pylesos_dacha_robot_pylesos_dacha", "mdi:robot-vacuum", ""],
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

// Сетка рассчитана на эти размеры и целиком масштабируется под экран (без прокрутки)
const BASE_PW = 800, BASE_PH = 1230; // планшет вертикально
const BASE_W = 1280, BASE_H = 760;   // планшет горизонтально / монитор
const MOBILE_W = 600;
const IDLE_HOME_MS = 120000;         // без касаний 2 минуты — вернуться на «Дом»

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
    this._pending = new Map();
    this._tab = "home";
    this._theme = null;
    this._fit = { mobile: false, style: "" };
    this._lastTouch = Date.now();
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
      l.href = "https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap";
      document.head.appendChild(l);
    }
    // часы, снимки камер и возврат на «Дом» после простоя
    this._clock = setInterval(() => {
      if (this._tab !== "home" && !this._pad && Date.now() - this._lastTouch > (this._config.idle_home_ms || IDLE_HOME_MS)) this._tab = "home";
      this._camTick = Math.floor(Date.now() / 15000);
      this._render(true);
    }, 15000);
    this._histTimer = setInterval(() => this._loadHistory(), 5 * 60000);
    this._onResize = () => this._measure();
    window.addEventListener("resize", this._onResize);
    this._ro = new ResizeObserver(() => this._measure());
    this._ro.observe(this);
    this._onTouch = () => { this._lastTouch = Date.now(); };
    this.addEventListener("pointerdown", this._onTouch, true);
    if (this._hass) this._loadHistory();
    requestAnimationFrame(() => this._measure());
  }

  disconnectedCallback() {
    clearInterval(this._clock);
    clearInterval(this._histTimer);
    window.removeEventListener("resize", this._onResize);
    this.removeEventListener("pointerdown", this._onTouch, true);
    if (this._ro) this._ro.disconnect();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._loadHistory();
    this._render();
  }

  /* Подгонка под экран: страница всегда занимает ровно видимую область без прокрутки */
  _measure() {
    const w = this.clientWidth;
    if (!w) return;
    const top = this.getBoundingClientRect().top + (window.scrollY || 0);
    const h = Math.max(320, window.innerHeight - Math.max(0, top));
    let fit;
    if (w < MOBILE_W || this._config.fit === false) {
      fit = { mobile: w < MOBILE_W, style: "" };
    } else {
      // раскладка, в которой экран используется лучше (крупнее масштаб)
      const portrait = Math.min(w / BASE_PW, h / BASE_PH) > Math.min(w / BASE_W, h / BASE_H);
      const bw = portrait ? BASE_PW : BASE_W, bh = portrait ? BASE_PH : BASE_H;
      const s = Math.max(0.5, Math.min(w / bw, h / bh, this._config.max_scale || 1.6));
      const useZoom = CSS.supports("zoom", "1");
      const size = `width:${(w / s).toFixed(1)}px;height:${(h / s).toFixed(1)}px;`;
      fit = {
        mobile: false,
        portrait,
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
  tmp(x) { return x === null || x === undefined ? "—" : `${sgn(x, 1)}°`; }

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
      for (const id of ids) out[id] = (res[id] || []).map((p) => ({ t: (p.lu ?? p.lc) * 1000, s: p.s }));
      this._hist = out;
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

  doorCount() {
    const members = this.a(E.doors, "entity_id") || [];
    return { total: members.length, open: members.filter((m) => this.on(m)).length };
  }

  batteries() {
    const skip = /myups|24117|mi_pad|robot_pylesos/;
    const vals = Object.values(this._hass.states).filter((o) =>
      o.entity_id.startsWith("sensor.") && o.entity_id.endsWith("_battery") && !skip.test(o.entity_id) &&
      o.attributes.unit_of_measurement === "%" && !BAD.includes(o.state)).map((o) => parseFloat(o.state)).filter(Number.isFinite);
    if (!vals.length) return { text: "—", low: 0 };
    const low = vals.filter((v) => v < 20).length;
    const min = Math.min(...vals);
    return low ? { text: `${low} разряжено · мин ${Math.round(min)} %`, low } : { text: `все выше ${Math.floor(min / 10) * 10} %`, low: 0 };
  }

  backup() {
    const v = this.s(E.backupOk);
    if (BAD.includes(v)) return { text: "нет данных", bad: true };
    const d = new Date(v), now = new Date();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400e3);
    const when = diff === 0 ? "сегодня" : diff === 1 ? "вчера" : d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
    const err = this.s(E.backupState) === "error";
    return { text: `${err ? "ошибка · " : ""}${when} ${hm(d)}`, bad: err || diff > 2 };
  }

  motion(camId) {
    const key = camId.split(".")[1];
    return this.on(`binary_sensor.${key}_motion`) || this.on(`binary_sensor.${key}_all_occupancy`);
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

  status() {
    if (this.on(E.leak)) return { text: "Протечка — вода перекрыта", lvl: "bad", icon: "mdi:water-alert" };
    if (this.on(E.smoke)) return { text: "Дым или угарный газ", lvl: "bad", icon: "mdi:smoke-detector-variant-alert" };
    if (this.s(E.alarm) === "triggered") return { text: "Сработала охрана", lvl: "bad", icon: "mdi:shield-alert-outline" };
    const dc = this.doorCount();
    if (dc.open) return { text: dc.open === 1 ? "Открыта дверь" : `Открыто дверей: ${dc.open}`, lvl: "warn", icon: "mdi:door-open" };
    if (this.s(E.upsStatus) && !String(this.s(E.upsStatus)).startsWith("OL")) return { text: "Нет сети · работает ИБП", lvl: "warn", icon: "mdi:power-plug-off-outline" };
    return { text: "Всё спокойно", lvl: "ok", icon: "mdi:check-circle-outline" };
  }

  /* Нажатая кнопка мигает, пока устройство не ответит сменой состояния (не дольше 10 с) */
  markPending(id) {
    if (!id) return;
    this._pending.set(id, { state: this.s(id), t: Date.now() });
    clearTimeout(this._pendTimer);
    this._pendTimer = setTimeout(() => { this._pending.clear(); this._render(true); }, 10000);
    this._render(true);
  }

  isPending(id) {
    const p = this._pending.get(id);
    if (!p) return false;
    if (this.s(id) !== p.state || Date.now() - p.t > 10000) { this._pending.delete(id); return false; }
    return true;
  }

  /* ---------- графика ---------- */
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

  spark(vals, { fill = true, color = "var(--accent)", cls = "spark" } = {}) {
    const v = vals.filter((x) => x !== null);
    if (v.length < 2) return `<div class="${cls} empty">нет данных</div>`;
    const w = 600, h = 120;
    let min = Math.min(...v), max = Math.max(...v);
    if (max - min < 1e-6) { min -= 1; max += 1; }
    const d = this.path(vals, w, h, min, max, 4);
    const area = fill ? `<path d="${d} L${w},${h} L0,${h} Z" fill="var(--spark)"/>` : "";
    return `<svg class="${cls}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${area}<path d="${d}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>`;
  }

  climateChart() {
    const series = CLIMATE.map((c) => this.series(c.temp, 24));
    const all = series.flat().filter((x) => x !== null);
    const w = 600, h = 160;
    if (all.length < 2) return `<div class="chart empty">загрузка истории…</div>`;
    const min = Math.floor(Math.min(...all) - 1), max = Math.ceil(Math.max(...all) + 1);
    const grid = [0.25, 0.5, 0.75].map((f) => `<line x1="0" x2="${w}" y1="${h * f}" y2="${h * f}" stroke="var(--line)" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join("");
    const lines = series.map((s, i) => `<path d="${this.path(s, w, h, min, max, 8)}" fill="none" stroke="${CLIMATE[i].color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`).join("");
    return `<div class="chart-wrap"><svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${grid}${lines}</svg>
      <span class="ax ax-t">${max}°</span><span class="ax ax-b">${min}°</span></div>`;
  }

  /* ---------- строительные блоки ---------- */
  // Плитка-переключатель: крупная, с иконкой, названием и состоянием
  tile(name, id, icon, opts = {}) {
    const st = this.s(id);
    const active = opts.active ?? ["on", "open", "opening", "cleaning", "heat"].includes(st);
    const off = BAD.includes(st);
    const tone = opts.tone || "acc";
    const sub = opts.sub ?? (off ? "нет связи" : active ? "включено" : "выключено");
    const cls = ["tile", active ? `on t-${tone}` : "", off ? "na" : "", this.isPending(id) ? "pending" : "", opts.cls || ""].join(" ");
    return `<button class="${cls}" data-act="${opts.act || "toggle"}" data-id="${id}">
      <span class="tile-i">${ic(icon)}</span>
      <span class="tile-t"><span class="tile-n">${esc(name)}</span><span class="tile-s">${sub}</span></span>
    </button>`;
  }

  section(title, meta = "", cls = "") {
    return `<div class="sec ${cls}"><span>${title}</span>${meta ? `<span class="sec-m">${meta}</span>` : ""}</div>`;
  }

  camImg(id) {
    const pic = this.a(id, "entity_picture");
    if (!pic) return "";
    const url = this._hass.hassUrl(pic) + (pic.includes("?") ? "&" : "?") + "t=" + (this._camTick || 0);
    return `<img src="${esc(url)}" alt="" loading="lazy">`;
  }

  /* ---------- вкладки ---------- */
  tabs() {
    const summer = this.on(E.season);
    const t = [
      ["home", "Дом", "mdi:home-variant-outline"],
      ["light", "Свет", "mdi:lightbulb-outline"],
      ["climate", "Климат", "mdi:thermometer"],
    ];
    if (summer) t.push(["pool", "Бассейн", "mdi:pool"]);
    t.push(["energy", "Энергия", "mdi:lightning-bolt-outline"], ["cams", "Камеры", "mdi:cctv"]);
    return t;
  }

  pageHome() {
    const al = this.s(E.alarm);
    const armed = al && al.startsWith("armed");
    const alText = { disarmed: "Снято с охраны", armed_away: "На охране", armed_home: "Охрана · дома", armed_night: "Охрана · ночь", arming: "Постановка…", pending: "Ожидание…", triggered: "Тревога!" }[al] || "Нет связи";
    const dc = this.doorCount();
    const pend = this.isPending(E.alarm) ? "pending" : "";
    const summer = this.on(E.season);
    const lightsOn = LIGHT_IDS.filter((id) => this.on(id)).length;
    const preset = this.presetNow();
    const p = this.n(E.power);
    const ups = this.n(E.ups);
    const upsOk = String(this.s(E.upsStatus) || "OL").startsWith("OL");
    const bat = this.batteries();
    const lp = this.lastPerson();

    const rooms = CLIMATE.map((c) => {
      const cur = this.a(c.climate, "current_temperature") ?? this.n(c.temp);
      const tgt = this.a(c.climate, "temperature");
      const heating = this.on(c.heater);
      return `<button class="room" data-act="tab" data-id="climate">
        <span class="room-n">${c.name}${heating ? ic("mdi:fire", "hot") : ""}</span>
        <span class="room-t">${this.tmp(cur)}</span>
        <span class="room-s">${tgt != null ? `цель ${nf(tgt, 0)}°` : ""}${heating ? " · греет" : ""}</span>
      </button>`;
    }).join("");

    const stat = (icon, label, value, lvl, act, id) =>
      `<button class="stat ${lvl}" data-act="${act}" data-id="${id}">${ic(icon)}<span class="stat-l">${label}</span><span class="stat-v">${value}</span></button>`;

    // сначала камеры с движением
    const cams = [...CAMERAS].sort((x, y) => Number(this.motion(y[1])) - Number(this.motion(x[1])));

    return `<div class="page home">
      <div class="card sec-card ${armed ? "armed" : al === "disarmed" ? "disarmed" : ""} a-sec">
        <div class="sec-top">
          <span class="sec-ic">${ic(armed ? "mdi:shield-lock" : "mdi:shield-off-outline")}</span>
          <span class="sec-txt"><span class="sec-state">${alText}</span><span class="sec-sub">${dc.open ? `открыто дверей: ${dc.open}` : `все ${dc.total} двери закрыты`}</span></span>
        </div>
        <div class="sec-btns">
          <button class="big-btn ${al === "disarmed" ? "ok-on" : ""} ${pend}" data-act="disarm">${ic("mdi:shield-off-outline")}Снять</button>
          <button class="big-btn ${armed ? "bad-on" : ""} ${pend}" data-act="arm">${ic("mdi:shield-lock-outline")}Поставить</button>
        </div>
      </div>

      <div class="rooms a-rooms">${rooms}</div>

      <div class="quick a-quick">
        <button class="q ${this.isPending(E.warmUp) ? "pending" : ""}" data-act="warmup">${ic("mdi:fire", "hot")}<span>Прогрев</span><small>к приезду</small></button>
        <button class="q ${preset === "away" ? "q-on" : ""}" data-act="preset" data-id="away">${ic("mdi:shield-home-outline")}<span>Дежурный</span><small>${preset === "away" ? "включён" : "уезжаю"}</small></button>
        <button class="q ${lightsOn ? "q-light" : ""}" data-act="alloff">${ic("mdi:lightbulb-off-outline")}<span>Свет</span><small>${lightsOn ? `выключить ${lightsOn}` : "всё выключено"}</small></button>
        <button class="q" data-act="season" data-id="${summer ? "off" : "on"}">${ic(summer ? "mdi:white-balance-sunny" : "mdi:snowflake")}<span>${summer ? "Лето" : "Зима"}</span><small>сменить сезон</small></button>
      </div>

      <div class="stats a-stats">
        ${stat("mdi:door", "Двери", dc.open ? `открыто ${dc.open}` : "закрыты", dc.open ? "warn" : "", "more", E.doors)}
        ${stat("mdi:water-alert", "Протечка", this.on(E.leak) ? "ПРОТЕЧКА" : "сухо", this.on(E.leak) ? "bad" : "", "more", E.leak)}
        ${stat("mdi:smoke-detector-variant", "Дым и CO", this.on(E.smoke) ? "ТРЕВОГА" : "норма", this.on(E.smoke) ? "bad" : "", "more", E.smoke)}
        ${stat("mdi:lightning-bolt-outline", "Сеть", p === null ? "—" : `${Math.round(p).toLocaleString("ru-RU")} Вт`, "", "tab", "energy")}
        ${stat("mdi:battery-charging-high", "ИБП", ups === null ? "—" : `${Math.round(ups)} %${upsOk ? "" : " · от батареи"}`, upsOk ? "" : "warn", "more", E.ups)}
        ${stat("mdi:battery-alert-variant-outline", "Датчики", bat.low ? `${bat.low} разряжено` : "в порядке", bat.low ? "warn" : "", "tab", "energy")}
      </div>

      <div class="card cams-mini a-cams">
        <div class="head">${ic("mdi:cctv")}<span>Камеры</span><span class="head-m">${lp ? `человек ${CAM_WHERE[lp.key]} · ${lp.active ? "сейчас" : hm(lp.t)}` : "людей не было"}</span></div>
        <div class="cm-row">${cams.map(([n, id]) => `<button class="shot ${this.motion(id) ? "motion" : ""}" data-act="more" data-id="${id}">${this.camImg(id)}<span class="shot-n">${n}</span></button>`).join("")}</div>
      </div>
    </div>`;
  }

  pageLight() {
    const lightsOn = LIGHT_IDS.filter((id) => this.on(id)).length;
    return `<div class="page light">
      <div class="lgrps">${LIGHTS.map((g) => `<div class="lgrp">${this.section(g.group, `${g.items.filter((i) => this.on(i[1])).length} из ${g.items.length}`)}
        <div class="tiles c${g.items.length === 3 ? 3 : 2}">${g.items.map(([n, id, i]) => this.tile(n, id, i, { tone: "light" })).join("")}</div></div>`).join("")}</div>
      <button class="wide-btn ${lightsOn ? "" : "dim"}" data-act="alloff">${ic("mdi:lightbulb-off-outline")}${lightsOn ? `Выключить весь свет · горит ${lightsOn}` : "Весь свет выключен"}</button>
    </div>`;
  }

  pageClimate() {
    const preset = this.presetNow();
    const eta = this.n(E.heatEta);
    const zp = this.n(E.heatZonePower);
    const thr = this.n(E.frostThr);
    const tgt0 = this.a(CLIMATE[0].climate, "temperature");
    const frost = !this.on(E.heatDuty) ? "выключена"
      : thr !== null && tgt0 != null && tgt0 <= thr ? `следит · порог ${sgn(thr, 0)}°` : "ждёт режима «Дежурный»";
    const out = this.outside();

    const rows = CLIMATE.map((c) => {
      const cur = this.a(c.climate, "current_temperature") ?? this.n(c.temp);
      const tgt = this.a(c.climate, "temperature");
      const heating = this.on(c.heater);
      const pw = this.n(c.power);
      const pend = this.isPending(c.climate) ? "pending" : "";
      return `<div class="trow">
        <button class="tr-name" data-act="more" data-id="${c.climate}"><i class="dot" style="background:${c.color}"></i><span>${c.name}</span>
          <small class="${heating ? "hot" : ""}">${heating ? `греет${pw ? ` · ${nf(pw / 1000, 1)} кВт` : ""}` : "не греет"}</small></button>
        <span class="tr-cur">${this.tmp(cur)}</span>
        <span class="tr-set ${pend}">
          <button class="rb" data-act="tdown" data-id="${c.climate}">${ic("mdi:minus")}</button>
          <span class="tr-tgt"><small>цель</small>${tgt == null ? "—" : nf(tgt, 1) + "°"}</span>
          <button class="rb" data-act="tup" data-id="${c.climate}">${ic("mdi:plus")}</button>
        </span>
      </div>`;
    }).join("");

    return `<div class="page climate">
      <div class="modes a-modes">
        ${PRESETS.map(([k, t, i]) => `<button class="mode ${preset === k ? "sel" : ""}" data-act="preset" data-id="${k}">${ic(i)}<span>${t}</span></button>`).join("")}
        <button class="mode warm ${this.isPending(E.warmUp) ? "pending" : ""}" data-act="warmup">${ic("mdi:fire")}<span>Прогрев</span></button>
      </div>
      <div class="card a-rows">${rows}</div>
      <div class="a-heaters">
        ${this.section("Обогреватели", zp ? `${nf(zp, 1)} кВт` : "")}
        <div class="tiles c4">${HEATERS.map(([n, id]) => this.tile(n, id, "mdi:radiator", { tone: "heat", sub: this.on(id) ? "греет" : "выключен" })).join("")}</div>
      </div>
      <div class="card info a-info">
        <button class="irow" data-act="more" data-id="${E.heatEta}">${ic("mdi:timer-sand")}<span>До прогрева</span><b>${eta ? "~" + dur(eta * 60) : "—"}</b></button>
        <button class="irow" data-act="toggle" data-id="${E.heatDuty}">${ic("mdi:snowflake-alert")}<span>Антизаморозка</span><b class="${this.on(E.heatDuty) ? "" : "warn"}">${frost}</b></button>
        <button class="irow" data-act="more" data-id="${this.weatherEntity()}">${ic(WEATHER_ICON[out.cond] || "mdi:weather-partly-cloudy")}<span>На улице</span><b>${this.tmp(out.t)}${out.wind != null ? ` · ветер ${Math.round(out.wind)} м/с` : ""}</b></button>
      </div>
      <div class="card a-chart">
        <div class="head">${ic("mdi:chart-bell-curve-cumulative")}<span>За сутки</span><span class="legend">${CLIMATE.map((c) => `<span><i style="background:${c.color}"></i>${c.name}</span>`).join("")}</span></div>
        ${this.climateChart()}
      </div>
    </div>`;
  }

  pagePool() {
    const pool = this.n(E.poolTemp);
    const fw = this.filterWindows();
    const flow = this.on(E.poolFlow);
    return `<div class="page pool">
      <div class="card pool-card a-pool">
        <div class="head">${ic("mdi:pool")}<span>Бассейн</span><span class="head-m">${this.on(E.poolSmart) ? "фильтрация по расписанию" : esc(this.s(E.poolStatus) || "")}</span></div>
        <div class="pool-main">
          <button class="pool-t" data-act="more" data-id="${E.poolTemp}">${pool === null ? "—" : nf(pool, 1) + "°"}<small>вода</small></button>
          ${this.spark(this.series(E.poolTemp, 24), { fill: false })}
        </div>
        <div class="track">${fw.wins.map(([a, b]) => `<i style="left:${(a * 100).toFixed(2)}%;width:${Math.max(0.6, (b - a) * 100).toFixed(2)}%"></i>`).join("")}</div>
        <div class="track-l"><span>фильтрация за сутки</span><span>${fw.total ? dur(fw.total) : "0 мин"} · поток ${flow ? "есть" : "<b class='warn'>нет</b>"}</span></div>
      </div>
      <div class="tiles c3 a-ptiles">
        ${this.tile("Фильтр", E.poolFilter, "mdi:air-filter")}
        ${this.tile("Нагрев", E.poolHeat, "mdi:fire", { tone: "heat" })}
        ${this.tile("Умный фильтр", E.poolSmart, "mdi:robot-outline")}
      </div>
      <div class="a-water">
        ${this.section("Полив", `бочка ${this.tmp(this.n(E.barrelTemp))} · теплица ${this.n(E.soil) === null ? "—" : Math.round(this.n(E.soil)) + " %"}`)}
        <div class="tiles c4">
          ${WATERING.map(([n, id, i]) => this.tile(n, id, i)).join("")}
          <button class="tile" data-act="stopwater"><span class="tile-i">${ic("mdi:stop-circle-outline")}</span><span class="tile-t"><span class="tile-n">Стоп</span><span class="tile-s">всё выключить</span></span></button>
        </div>
        ${this.tile("Автополив", E.autoWater, "mdi:calendar-clock", { cls: "tile-wide", sub: this.on(E.autoWater) ? "по расписанию" : "выключен" })}
      </div>
    </div>`;
  }

  pageEnergy() {
    const p = this.n(E.power);
    const kwh = this.energyDay();
    const W = (x) => (x === null ? "—" : `${Math.round(x).toLocaleString("ru-RU")} Вт`);
    const mainV = this.n(E.mainVolt), mainA = this.n(E.mainCurrent);
    const bk = this.backup();
    const bat = this.batteries();
    const osv = this.s(E.os);
    const v = (x, suf) => (x === null ? "—" : Math.round(x) + suf);
    const brk = (name, icon, val, sub, id, onState) => `<button class="brk ${onState ? "on" : ""}" data-act="more" data-id="${id}">
      <span class="brk-h">${ic(icon)}${name}<i class="led"></i></span><span class="brk-v">${val}</span><span class="brk-s">${sub}</span></button>`;
    return `<div class="page energy">
      <div class="card power a-power" data-act="more" data-id="${E.power}">
        <div class="head">${ic("mdi:lightning-bolt-outline")}<span>Мощность сети</span><span class="head-m">сутки ${kwh === null ? "—" : nf(kwh, 1)} кВт·ч</span></div>
        <div class="pw-main"><span class="pw-v">${p === null ? "—" : Math.round(p).toLocaleString("ru-RU")}<small>Вт</small></span>
          <span class="pw-s">${mainV === null ? "" : `${Math.round(mainV)} В`}${mainA !== null ? ` · ${nf(mainA, 1)} А` : ""}</span></div>
        ${this.spark(this.series(E.power, 12, 10 * 60e3))}
      </div>
      <div class="brks a-brk">
        ${brk("Общий 63 А", "mdi:meter-electric-outline", W(this.n(E.mainPower)), `${v(mainV, " В")}`, E.mainSw, this.on(E.mainSw))}
        ${brk("Обогрев", "mdi:radiator", W(this.n(E.heatPower)), `${v(this.n(E.heatVolt), " В")}`, E.heatSw, this.on(E.heatSw))}
        ${brk("Плита 380", "mdi:stove", this.on(E.plita) ? "Вкл" : "Выкл", "резерв нагрева", E.plita, this.on(E.plita))}
        ${brk("Септик", "mdi:pipe-valve", this.n(E.septikPower) === null ? (this.on(E.septik) ? "Вкл" : "Выкл") : W(this.n(E.septikPower)), this.on(E.septik) ? "обогрев" : "простой", E.septik, this.on(E.septik))}
      </div>
      <div class="a-loads">
        ${this.section("Устройства")}
        <div class="tiles c3">${LOADS.map(([n, id, i, tone]) => this.tile(n, id, i, { tone: tone || "acc", act: id.startsWith("vacuum.") ? "more" : "toggle", sub: id.startsWith("cover.") ? ({ open: "открыта", closed: "закрыта", opening: "открывается", closing: "закрывается" }[this.s(id)] || "—") : undefined })).join("")}</div>
      </div>
      <div class="card info a-sys">
        <button class="irow" data-act="more" data-id="${E.cpu}">${ic("mdi:cpu-64-bit")}<span>Процессор</span><b>${v(this.n(E.cpu), " %")} · ${v(this.n(E.cpuTemp), " °C")}</b></button>
        <button class="irow" data-act="more" data-id="${E.mem}">${ic("mdi:memory")}<span>Память · диск</span><b>${v(this.n(E.mem), " %")} · ${v(this.n(E.disk), " %")}</b></button>
        <button class="irow" data-act="more" data-id="${E.backupOk}">${ic("mdi:cloud-upload-outline")}<span>Резервная копия</span><b class="${bk.bad ? "warn" : ""}">${bk.text}</b></button>
        <div class="irow">${ic("mdi:battery-70")}<span>Батареи датчиков</span><b class="${bat.low ? "warn" : ""}">${bat.text}</b></div>
        ${osv && !BAD.includes(osv) ? `<div class="irow">${ic("mdi:home-assistant")}<span>Система</span><b>HAOS ${esc(osv)}</b></div>` : ""}
      </div>
    </div>`;
  }

  pageCams() {
    const lp = this.lastPerson();
    return `<div class="page cams">
      ${this.section("Камеры", lp ? `человек ${CAM_WHERE[lp.key]} · ${lp.active ? "сейчас" : hm(lp.t)}` : "людей не было")}
      <div class="cam-grid">${CAMERAS.map(([n, id]) => `<button class="shot ${this.motion(id) ? "motion" : ""}" data-act="more" data-id="${id}">${this.camImg(id)}<span class="shot-n">${this.motion(id) ? ic("mdi:motion-sensor") : ""}${n}</span></button>`).join("")}</div>
    </div>`;
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

  _html() {
    const now = new Date();
    const theme = this._theme || "dark";
    const status = this.status();
    const out = this.outside();
    const inT = this.n(E.inTemp);
    const tabs = this.tabs();
    if (!tabs.find((t) => t[0] === this._tab)) this._tab = "home";
    const dateStr = now.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
    const page = { home: () => this.pageHome(), light: () => this.pageLight(), climate: () => this.pageClimate(), pool: () => this.pagePool(), energy: () => this.pageEnergy(), cams: () => this.pageCams() }[this._tab]();

    return `<div class="root theme-${theme} ${this._fit.mobile ? "mobile" : "fit"} ${this._fit.portrait ? "portrait" : "landscape"}" style="${this._fit.style}">
  <header class="hdr">
    <div class="clock"><span class="time">${hm(now)}</span><span class="date">${esc(this._config.title || "Дача")} · ${esc(dateStr)}</span></div>
    <div class="hdr-r">
      <span class="status ${status.lvl}">${ic(status.icon)}${status.text}</span>
      <button class="temps" data-act="more" data-id="${this.weatherEntity()}">
        <span>${ic(WEATHER_ICON[out.cond] || "mdi:weather-partly-cloudy")}${this.tmp(out.t)}</span>
        <span>${ic("mdi:home-thermometer-outline")}${this.tmp(inT)}</span>
      </button>
      <button class="ibtn" data-act="theme" title="Тема">${ic(theme === "dark" ? "mdi:weather-sunny" : "mdi:weather-night")}</button>
    </div>
  </header>
  <main class="main">${page}</main>
  <nav class="tabs">${tabs.map(([k, t, i]) => `<button class="tab ${this._tab === k ? "sel" : ""}" data-act="tab" data-id="${k}">${ic(i)}<span>${t}</span></button>`).join("")}</nav>
  ${this.padHtml()}
</div>`;
  }

  padHtml() {
    if (!this._pad) return "";
    const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "back", "0", "ok"];
    const label = { back: ic("mdi:backspace-outline"), ok: ic("mdi:check") };
    return `<div class="pad-bg" data-act="pad" data-id="close"><div class="pad" data-act="noop">
      <div class="pad-h">${ic("mdi:shield-off-outline")}<span>Снять с охраны</span><button class="pad-x" data-act="pad" data-id="close">${ic("mdi:close")}</button></div>
      <div class="pad-code ${this._pad.err ? "bad" : ""}">${this._pad.err || (this._pad.code ? "•".repeat(this._pad.code.length) : "введите код")}</div>
      <div class="pad-keys">${keys.map((k) => `<button class="pk ${k === "ok" ? "pk-ok" : ""}" data-act="pad" data-id="${k}">${label[k] || k}</button>`).join("")}</div>
    </div></div>`;
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

  async _disarmWithCode() {
    const code = this._pad.code;
    if (!code) return;
    try {
      await this._hass.callService("alarm_control_panel", "alarm_disarm", { entity_id: E.alarm, code });
      this._pad = null;
      this.markPending(E.alarm);
    } catch (e) {
      this._pad = { code: "", err: "Неверный код" };
      this._render(true);
    }
  }

  _setTemp(id, dir) {
    const o = this.st(id);
    if (!o) return;
    const step = Math.max(0.5, o.attributes.target_temp_step || 0.5);
    const cur = o.attributes.temperature ?? o.attributes.current_temperature ?? 20;
    const min = o.attributes.min_temp ?? 5, max = o.attributes.max_temp ?? 30;
    const next = Math.min(max, Math.max(min, Math.round((cur + dir * step) / step) * step));
    this.markPending(id);
    this._call("climate", "set_temperature", { entity_id: id, temperature: next });
  }

  _action(act, id) {
    switch (act) {
      case "noop": return;
      case "tab": this._tab = id; return this._render(true);
      case "more": return this._more(id);
      case "toggle": {
        const st = this.s(id);
        if (BAD.includes(st)) return this._more(id);
        this.markPending(id);
        const dom = id.split(".")[0];
        if (dom === "cover") return this._call("cover", "toggle", { entity_id: id });
        if (dom === "automation") return this._call("automation", st === "on" ? "turn_off" : "turn_on", { entity_id: id });
        return this._call("homeassistant", "toggle", { entity_id: id });
      }
      case "alloff": {
        const onIds = LIGHT_IDS.filter((x) => this.on(x));
        if (!onIds.length) return;
        onIds.forEach((x) => this.markPending(x));
        return this._call("switch", "turn_off", { entity_id: onIds });
      }
      case "warmup": {
        // «Нагрев дома»: 23° комната/кухня, 15° тамбур, лестница и бойлер — все ступени сразу
        this.markPending(E.warmUp);
        HEATERS.forEach((h) => this.markPending(h[1]));
        return this._call("automation", "trigger", { entity_id: E.warmUp, skip_condition: true });
      }
      case "tup": return this._setTemp(id, 1);
      case "tdown": return this._setTemp(id, -1);
      case "preset": {
        for (const c of CLIMATE) {
          const modes = this.a(c.climate, "preset_modes") || [];
          const mode = modes.includes(id) ? id : id === "comfort" && modes.includes("home") ? "home" : null;
          if (mode) { this.markPending(c.climate); this._call("climate", "set_preset_mode", { entity_id: c.climate, preset_mode: mode }); }
        }
        return;
      }
      case "arm":
        if (String(this.s(E.alarm)).startsWith("armed")) return;
        this.markPending(E.alarm);
        return this._call("alarm_control_panel", "alarm_arm_away", { entity_id: E.alarm });
      case "disarm": {
        if (this.s(E.alarm) === "disarmed") return;
        if (this.a(E.alarm, "code_format")) { this._pad = { code: "", err: "" }; return this._render(true); }
        this.markPending(E.alarm);
        return this._call("alarm_control_panel", "alarm_disarm", { entity_id: E.alarm });
      }
      case "pad": {
        if (!this._pad) return;
        if (id === "close") { this._pad = null; return this._render(true); }
        if (id === "back") this._pad.code = this._pad.code.slice(0, -1);
        else if (id === "ok") return this._disarmWithCode();
        else if (this._pad.code.length < 8) this._pad.code += id;
        this._pad.err = "";
        return this._render(true);
      }
      case "season": return this._call("input_boolean", id === "on" ? "turn_on" : "turn_off", { entity_id: E.season });
      case "stopwater": WATERING.forEach((w) => this.markPending(w[1])); return this._call("switch", "turn_off", { entity_id: WATERING.map((w) => w[1]) });
      case "theme": {
        this._theme = (this._theme || "dark") === "dark" ? "light" : "dark";
        try { localStorage.setItem("dacha-pro-theme", this._theme); } catch (e) { /* storage недоступен */ }
        return this._render(true);
      }
    }
  }
}

const STYLES = `
:host { display:block; }
.root {
  --bg:#0e0e10; --surface:#161618; --surface2:#1d1d20; --line:rgba(255,255,255,.07); --line2:rgba(255,255,255,.12);
  --text:#f3f1ec; --muted:#9a968f; --faint:#64615c;
  --accent:#d8c3a0; --accent-bg:rgba(216,195,160,.13); --accent-text:#ead9bb;
  --light:#f2c95e; --light-bg:rgba(242,201,94,.15); --heat:#ef8a7c; --heat-bg:rgba(239,138,124,.15);
  --green:#7fcf9c; --green-bg:rgba(127,207,156,.15); --red:#ef6f63; --red-bg:rgba(239,111,99,.17); --warn:#e9a84f;
  --c1:#9fc2e6; --c2:#e6b26a; --c3:#a8a49c; --spark:rgba(216,195,160,.12); --motion:#ffd60a;
  font-family: Inter, -apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
  font-size:16px; color:var(--text); background:var(--bg); position:relative;
  display:flex; flex-direction:column; box-sizing:border-box;
  -webkit-font-smoothing:antialiased; font-feature-settings:"tnum" 1, "cv11" 1;
}
.root.theme-light {
  --bg:#f3f1ec; --surface:#ffffff; --surface2:#f8f6f2; --line:rgba(0,0,0,.07); --line2:rgba(0,0,0,.12);
  --text:#1c1b19; --muted:#77736c; --faint:#a9a59e;
  --accent:#8f7349; --accent-bg:rgba(143,115,73,.12); --accent-text:#6f5733;
  --light:#a87a00; --light-bg:#fbefc9; --heat:#c34a3d; --heat-bg:#fbe2de; --green:#23885a; --green-bg:#daf0e3; --red:#cf4237; --red-bg:#fbe0dd; --warn:#b5761f;
  --c1:#4f86bf; --c2:#c98a2b; --c3:#8a867f; --spark:rgba(143,115,73,.1);
}
.root.fit { overflow:hidden; }
.root.mobile { min-height:calc(100vh - var(--header-height, 56px)); }
*, *::before, *::after { box-sizing:border-box; }
button { font:inherit; color:inherit; cursor:pointer; border:0; background:none; padding:0; text-align:left; -webkit-tap-highlight-color:transparent; }
.i { --mdc-icon-size:22px; width:22px; height:22px; flex:none; display:inline-flex; color:var(--muted); }
.hot { color:var(--heat) !important; } .warn { color:var(--warn) !important; } .bad { color:var(--red) !important; }

/* шапка */
.hdr { display:flex; justify-content:space-between; align-items:center; gap:20px; padding:22px 28px 14px; flex:none; }
.clock { display:flex; flex-direction:column; min-width:0; }
.time { font-size:58px; font-weight:200; letter-spacing:-.03em; line-height:1; }
.date { font-size:15px; color:var(--muted); margin-top:6px; text-transform:lowercase; white-space:nowrap; }
.date::first-letter { text-transform:uppercase; }
.hdr-r { display:flex; align-items:center; gap:12px; flex-wrap:wrap; justify-content:flex-end; }
.status { display:inline-flex; align-items:center; gap:10px; height:48px; padding:0 18px; border-radius:24px; background:var(--surface); border:1px solid var(--line); font-size:17px; font-weight:500; white-space:nowrap; }
.status .i { color:var(--green); }
.status.warn { color:var(--warn); background:rgba(233,168,79,.1); border-color:transparent; } .status.warn .i { color:var(--warn); }
.status.bad { color:var(--red); background:var(--red-bg); border-color:transparent; animation:alarm 1.4s ease-in-out infinite; } .status.bad .i { color:var(--red); }
@keyframes alarm { 50% { opacity:.6; } }
.temps { display:inline-flex; gap:16px; height:48px; padding:0 18px; border-radius:24px; background:var(--surface); border:1px solid var(--line); align-items:center; font-size:17px; font-weight:500; }
.temps span { display:inline-flex; align-items:center; gap:7px; }
.ibtn { width:48px; height:48px; border-radius:24px; background:var(--surface); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; }

/* содержимое */
.main { flex:1; min-height:0; padding:6px 28px 14px; display:flex; flex-direction:column; }
.page { flex:1; min-height:0; display:grid; gap:16px; }
.card { background:var(--surface); border:1px solid var(--line); border-radius:24px; padding:20px 22px; min-width:0; min-height:0; overflow:hidden; }
.head { display:flex; align-items:center; gap:10px; font-size:15px; font-weight:500; color:var(--muted); margin-bottom:12px; }
.head .i { --mdc-icon-size:20px; width:20px; height:20px; color:var(--accent); }
.head-m { margin-left:auto; font-weight:400; font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sec { display:flex; align-items:baseline; justify-content:space-between; font-size:15px; font-weight:500; color:var(--muted); margin:2px 4px 10px; letter-spacing:.01em; }
.sec-m { font-weight:400; font-size:14px; }

/* плитки */
.tiles { display:grid; gap:12px; }
.tiles.c2 { grid-template-columns:repeat(2, minmax(0,1fr)); }
.tiles.c3 { grid-template-columns:repeat(3, minmax(0,1fr)); }
.tiles.c4 { grid-template-columns:repeat(4, minmax(0,1fr)); }
.tile { display:flex; flex-direction:column; justify-content:space-between; gap:10px; min-height:104px; padding:16px 18px; border-radius:20px; background:var(--surface); border:1px solid var(--line); transition:background .2s, border-color .2s; min-width:0; }
.tile-i { width:42px; height:42px; border-radius:21px; background:var(--surface2); display:flex; align-items:center; justify-content:center; }
.tile-i .i { --mdc-icon-size:24px; width:24px; height:24px; }
.tile-t { display:flex; flex-direction:column; gap:2px; min-width:0; }
.tile-n { font-size:18px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tile-s { font-size:14px; color:var(--muted); }
.tile.on { border-color:transparent; }
.tile.on.t-acc { background:var(--accent-bg); } .tile.on.t-acc .tile-i { background:var(--accent); } .tile.on.t-acc .tile-i .i { color:#1a1712; } .tile.on.t-acc .tile-s { color:var(--accent-text); }
.tile.on.t-light { background:var(--light-bg); } .tile.on.t-light .tile-i { background:var(--light); } .tile.on.t-light .tile-i .i { color:#2a2108; } .tile.on.t-light .tile-s { color:var(--light); }
.tile.on.t-heat { background:var(--heat-bg); } .tile.on.t-heat .tile-i { background:var(--heat); } .tile.on.t-heat .tile-i .i { color:#2b0f0b; } .tile.on.t-heat .tile-s { color:var(--heat); }
.tile.na { opacity:.4; }
.tile:active, .q:active, .room:active, .stat:active, .mode:active, .rb:active, .big-btn:active { transform:scale(.98); }
.pending { animation:pend 1s ease-in-out infinite; border-color:var(--accent) !important; }
@keyframes pend { 50% { box-shadow:0 0 0 4px var(--accent-bg); } }
.wide-btn { display:flex; align-items:center; justify-content:center; gap:12px; height:76px; border-radius:20px; background:var(--surface); border:1px solid var(--line); font-size:18px; font-weight:500; }
.wide-btn.dim { color:var(--muted); }
.tile-wide { flex-direction:row; align-items:center; justify-content:flex-start; min-height:76px; margin-top:12px; width:100%; }

/* ===== Дом ===== */
.home { grid-template-columns:repeat(6, minmax(0,1fr)); grid-template-rows:auto auto auto auto minmax(0,1fr);
  grid-template-areas:"sec sec sec sec sec sec" "rooms rooms rooms rooms rooms rooms" "quick quick quick quick quick quick" "stats stats stats stats stats stats" "cams cams cams cams cams cams"; }
.a-sec { grid-area:sec; } .a-rooms { grid-area:rooms; } .a-quick { grid-area:quick; } .a-stats { grid-area:stats; } .a-cams { grid-area:cams; }
.sec-card { display:flex; align-items:center; gap:24px; padding:22px 24px; }
.sec-top { display:flex; align-items:center; gap:18px; flex:1; min-width:0; }
.sec-ic { width:64px; height:64px; border-radius:32px; background:var(--surface2); display:flex; align-items:center; justify-content:center; flex:none; }
.sec-ic .i { --mdc-icon-size:32px; width:32px; height:32px; }
.sec-card.armed .sec-ic { background:var(--red-bg); } .sec-card.armed .sec-ic .i { color:var(--red); }
.sec-card.disarmed .sec-ic { background:var(--green-bg); } .sec-card.disarmed .sec-ic .i { color:var(--green); }
.sec-txt { display:flex; flex-direction:column; gap:4px; min-width:0; }
.sec-state { font-size:28px; font-weight:500; letter-spacing:-.01em; white-space:nowrap; }
.sec-card.armed .sec-state { color:var(--red); } .sec-card.disarmed .sec-state { color:var(--green); }
.sec-sub { font-size:15px; color:var(--muted); }
.sec-btns { display:grid; grid-template-columns:1fr 1fr; gap:10px; flex:none; width:330px; }
.big-btn { display:flex; align-items:center; justify-content:center; gap:10px; height:64px; border-radius:18px; background:var(--surface2); border:1px solid var(--line); font-size:18px; font-weight:500; }
.big-btn.ok-on { background:var(--green-bg); color:var(--green); border-color:transparent; } .big-btn.ok-on .i { color:var(--green); }
.big-btn.bad-on { background:var(--red-bg); color:var(--red); border-color:transparent; } .big-btn.bad-on .i { color:var(--red); }

.rooms { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:16px; }
.room { display:flex; flex-direction:column; gap:6px; padding:20px 22px; border-radius:24px; background:var(--surface); border:1px solid var(--line); }
.room-n { display:flex; align-items:center; justify-content:space-between; font-size:16px; color:var(--muted); font-weight:500; }
.room-n .i { --mdc-icon-size:20px; width:20px; height:20px; }
.room-t { font-size:52px; font-weight:200; letter-spacing:-.03em; line-height:1.05; }
.room-s { font-size:14px; color:var(--muted); }

.quick { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; }
.q { display:flex; flex-direction:column; align-items:flex-start; gap:4px; padding:16px 18px; border-radius:20px; background:var(--surface); border:1px solid var(--line); min-height:110px; }
.q .i { --mdc-icon-size:26px; width:26px; height:26px; color:var(--accent); margin-bottom:auto; }
.q span { font-size:18px; font-weight:500; margin-top:8px; }
.q small { font-size:13px; color:var(--muted); }
.q.q-on { background:var(--accent-bg); border-color:transparent; } .q.q-on small { color:var(--accent-text); }
.q.q-light { background:var(--light-bg); border-color:transparent; } .q.q-light .i { color:var(--light); } .q.q-light small { color:var(--light); }

.stats { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; }
.stat { display:grid; grid-template-columns:auto 1fr; grid-template-rows:auto auto; column-gap:14px; align-items:center; padding:14px 18px; border-radius:18px; background:var(--surface); border:1px solid var(--line); }
.stat .i { grid-row:1 / 3; --mdc-icon-size:24px; width:24px; height:24px; }
.stat-l { font-size:14px; color:var(--muted); }
.stat-v { font-size:17px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.stat.warn { border-color:rgba(233,168,79,.35); } .stat.warn .i, .stat.warn .stat-v { color:var(--warn); }
.stat.bad { background:var(--red-bg); border-color:transparent; } .stat.bad .i, .stat.bad .stat-v { color:var(--red); }

.cams-mini { display:flex; flex-direction:column; padding:18px; }
.cm-row { flex:1; min-height:0; display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); grid-template-rows:repeat(2, minmax(0,1fr)); gap:12px; }
.cm-row .shot:nth-child(n+5) { display:none; }
/* узкий высокий блок камер: 2×3 вместо вытянутых 2×2 */
.fit .cams-mini { container-type:size; }
@container (max-aspect-ratio: 1/1) {
  .cm-row { grid-template-rows:repeat(3, minmax(0,1fr)); }
  .cm-row .shot:nth-child(n+5) { display:block; }
}
.shot { position:relative; border-radius:16px; overflow:hidden; background:var(--surface2); border:2px solid transparent; min-height:0; }
.shot img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
.shot-n { position:absolute; left:10px; bottom:10px; display:inline-flex; align-items:center; gap:6px; padding:5px 11px; border-radius:12px; background:rgba(0,0,0,.55); color:#fff; font-size:14px; font-weight:500; backdrop-filter:blur(6px); }
.shot-n .i { --mdc-icon-size:16px; width:16px; height:16px; color:var(--motion); }
.shot.motion { border-color:var(--motion); box-shadow:0 0 14px rgba(255,214,10,.35); }

/* ===== Свет ===== */
.light { grid-template-rows:minmax(0,1fr) auto; }
.lgrps { display:flex; flex-direction:column; gap:22px; min-height:0; }
.light .tile { min-height:142px; }
.light .tile-i { width:48px; height:48px; border-radius:24px; }

/* ===== Климат ===== */
.climate { grid-template-rows:auto auto auto auto minmax(0,1fr); }
.modes { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; padding:6px; border-radius:22px; background:var(--surface); border:1px solid var(--line); }
.mode { display:flex; align-items:center; justify-content:center; gap:10px; height:60px; border-radius:16px; font-size:17px; font-weight:500; color:var(--muted); }
.mode .i { color:inherit; }
.mode.sel { background:var(--accent); color:#1a1712; }
.mode.warm { color:var(--heat); }
.a-rows { padding:6px 22px; }
.trow { display:grid; grid-template-columns:minmax(0,1fr) 120px 230px; align-items:center; gap:14px; padding:14px 0; border-bottom:1px solid var(--line); }
.trow:last-child { border-bottom:0; }
.tr-name { display:grid; grid-template-columns:auto 1fr; column-gap:10px; align-items:center; }
.tr-name span { font-size:19px; font-weight:500; }
.tr-name small { grid-column:2; font-size:14px; color:var(--muted); }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
.tr-cur { font-size:40px; font-weight:200; letter-spacing:-.02em; text-align:right; }
.tr-set { display:grid; grid-template-columns:60px 1fr 60px; align-items:center; gap:8px; border-radius:18px; }
.rb { width:60px; height:60px; border-radius:30px; background:var(--surface2); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; }
.rb .i { color:var(--text); --mdc-icon-size:26px; width:26px; height:26px; }
.tr-tgt { display:flex; flex-direction:column; align-items:center; font-size:24px; font-weight:500; color:var(--accent-text); }
.tr-tgt small { font-size:12px; color:var(--muted); font-weight:400; }
.info { padding:6px 22px; }
.irow { display:flex; align-items:center; gap:14px; width:100%; padding:15px 0; border-bottom:1px solid var(--line); font-size:17px; }
.irow:last-child { border-bottom:0; }
.irow .i { color:var(--accent); }
.irow b { margin-left:auto; font-weight:500; color:var(--muted); text-align:right; }
.a-chart { display:flex; flex-direction:column; }
.legend { margin-left:auto; display:flex; gap:16px; font-size:14px; font-weight:400; }
.legend span { display:inline-flex; align-items:center; gap:6px; }
.legend i { width:8px; height:8px; border-radius:50%; }
.chart-wrap { position:relative; flex:1; min-height:60px; }
.chart { position:absolute; inset:0; width:100%; height:100%; }
.ax { position:absolute; left:0; font-size:12px; color:var(--faint); }
.ax-t { top:0; } .ax-b { bottom:0; }
.empty { display:flex; align-items:center; justify-content:center; color:var(--faint); font-size:14px; }

/* ===== Бассейн ===== */
.pool { grid-template-rows:minmax(0,1fr) auto auto; }
.pool-card { display:flex; flex-direction:column; }
.pool-main { flex:1; min-height:0; display:flex; align-items:center; gap:24px; }
.pool-t { font-size:96px; font-weight:200; letter-spacing:-.04em; line-height:1; white-space:nowrap; }
.pool-t small { font-size:18px; color:var(--muted); margin-left:8px; letter-spacing:0; }
.pool-main .spark { flex:1; height:120px; }
.track { position:relative; height:8px; border-radius:4px; background:var(--surface2); margin-top:14px; overflow:hidden; }
.track i { position:absolute; top:0; bottom:0; background:var(--accent); border-radius:4px; }
.track-l { display:flex; justify-content:space-between; font-size:14px; color:var(--muted); margin-top:8px; }

/* ===== Энергия ===== */
.energy { grid-template-rows:minmax(0,1fr) auto auto auto; }
.power { display:flex; flex-direction:column; cursor:pointer; }
.pw-main { display:flex; align-items:baseline; gap:18px; }
.pw-v { font-size:84px; font-weight:200; letter-spacing:-.04em; line-height:1; }
.pw-v small { font-size:20px; color:var(--muted); margin-left:8px; letter-spacing:0; }
.pw-s { font-size:16px; color:var(--muted); }
.power .spark { flex:1; min-height:60px; width:100%; margin-top:12px; }
.brks { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; }
.brk { display:flex; flex-direction:column; gap:6px; padding:16px 18px; border-radius:20px; background:var(--surface); border:1px solid var(--line); }
.brk-h { display:flex; align-items:center; gap:8px; font-size:15px; color:var(--muted); font-weight:500; white-space:nowrap; }
.brk-h .i { --mdc-icon-size:20px; width:20px; height:20px; }
.led { width:8px; height:8px; border-radius:50%; background:var(--faint); margin-left:auto; }
.brk.on .led { background:var(--green); box-shadow:0 0 8px var(--green); }
.brk-v { font-size:28px; font-weight:300; white-space:nowrap; }
.brk-s { font-size:13px; color:var(--muted); }

/* ===== Камеры ===== */
.cams { grid-template-rows:auto minmax(0,1fr); gap:0; }
.cam-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); grid-auto-rows:minmax(0,1fr); gap:14px; min-height:0; }

/* панель вкладок */
.tabs { flex:none; display:flex; gap:6px; margin:0 28px 22px; padding:8px; border-radius:30px; background:var(--surface); border:1px solid var(--line); }
.tab { flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; padding:10px 0 8px; border-radius:22px; font-size:14px; font-weight:500; color:var(--muted); }
.tab .i { --mdc-icon-size:26px; width:26px; height:26px; color:inherit; }
.tab.sel { background:var(--accent-bg); color:var(--accent-text); }

/* код охраны */
.pad-bg { position:absolute; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; z-index:5; backdrop-filter:blur(4px); }
.pad { width:380px; background:var(--surface); border:1px solid var(--line2); border-radius:28px; padding:22px; box-shadow:0 20px 60px rgba(0,0,0,.45); }
.pad-h { display:flex; align-items:center; gap:10px; font-weight:500; font-size:19px; }
.pad-h .i { color:var(--green); }
.pad-x { margin-left:auto; padding:6px; display:flex; }
.pad-code { height:64px; margin:18px 0; border-radius:18px; background:var(--surface2); display:flex; align-items:center; justify-content:center; font-size:30px; letter-spacing:.35em; }
.pad-code.bad { color:var(--red); font-size:17px; letter-spacing:0; }
.pad-keys { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.pk { height:72px; border-radius:20px; background:var(--surface2); border:1px solid var(--line); font-size:28px; font-weight:300; display:flex; align-items:center; justify-content:center; }
.pk .i { --mdc-icon-size:28px; width:28px; height:28px; color:var(--text); }
.pk:active { background:var(--accent-bg); }
.pk-ok { background:var(--green-bg); border-color:transparent; } .pk-ok .i { color:var(--green); }

/* ===== горизонтально: две колонки ===== */
.landscape .home { grid-template-columns:repeat(12, minmax(0,1fr)); grid-template-rows:auto auto minmax(0,1fr);
  grid-template-areas:"sec sec sec sec sec sec sec rooms rooms rooms rooms rooms" "quick quick quick quick quick quick quick cams cams cams cams cams" "stats stats stats stats stats stats stats cams cams cams cams cams"; }
.landscape .rooms { grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; }
.landscape .room-t { font-size:42px; }
.landscape .stats { grid-template-columns:repeat(3, minmax(0,1fr)); align-content:start; }
.landscape .sec-btns { width:280px; }
.landscape .lgrps { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:16px; align-content:start; }
.landscape .light .tiles { grid-template-columns:repeat(2, minmax(0,1fr)); }
.landscape .light .tile { min-height:104px; }
.landscape .climate { grid-template-columns:minmax(0,1.2fr) minmax(0,1fr); grid-template-rows:auto auto minmax(0,1fr);
  grid-template-areas:"modes modes" "rows heaters" "chart info"; }
.landscape .a-modes { grid-area:modes; } .landscape .a-rows { grid-area:rows; } .landscape .a-heaters { grid-area:heaters; }
.landscape .a-chart { grid-area:chart; } .landscape .a-info { grid-area:info; overflow:auto; }
.landscape .a-heaters .tiles { grid-template-columns:repeat(2, minmax(0,1fr)); }
.landscape .a-heaters .tile { min-height:92px; }
.landscape .trow { padding:10px 0; }
.landscape .energy { grid-template-columns:minmax(0,1fr) minmax(0,1fr); grid-template-rows:minmax(0,1fr) auto auto;
  grid-template-areas:"power sys" "brk brk" "loads loads"; }
.landscape .a-power { grid-area:power; } .landscape .a-sys { grid-area:sys; } .landscape .a-brk { grid-area:brk; } .landscape .a-loads { grid-area:loads; }
.landscape .a-loads .tiles { grid-template-columns:repeat(6, minmax(0,1fr)); }
.landscape .pool { grid-template-columns:minmax(0,1fr) minmax(0,1fr); grid-template-rows:minmax(0,1fr) auto; grid-template-areas:"pool water" "ptiles water"; }
.landscape .a-pool { grid-area:pool; } .landscape .a-ptiles { grid-area:ptiles; } .landscape .a-water { grid-area:water; }
.landscape .a-water .tiles { grid-template-columns:repeat(2, minmax(0,1fr)); }
.landscape .cam-grid { grid-template-columns:repeat(3, minmax(0,1fr)); }
.landscape .tabs { margin:0 28px 16px; }
.landscape .time { font-size:48px; }

/* телефон: прокрутка в одну колонку */
.mobile .hdr { flex-wrap:wrap; padding:14px 16px; }
.mobile .main { padding:6px 16px 12px; }
.mobile .home, .mobile .climate, .mobile .energy, .mobile .pool { display:flex; flex-direction:column; }
.mobile .sec-card { flex-direction:column; align-items:stretch; }
.mobile .sec-btns { width:auto; }
.mobile .quick, .mobile .tiles.c4 { grid-template-columns:repeat(2, minmax(0,1fr)); }
.mobile .stats { grid-template-columns:repeat(2, minmax(0,1fr)); }
.mobile .cm-row, .mobile .cam-grid { grid-template-columns:1fr; grid-template-rows:none; grid-auto-rows:200px; }
.mobile .cams-mini { min-height:260px; container-type:normal; }
.mobile .cm-row .shot:nth-child(n+4) { display:none; }
.mobile .room-t { font-size:30px; }
.mobile .room { padding:14px; }
.mobile .trow { grid-template-columns:1fr auto; }
.mobile .tr-set { grid-column:1 / -1; }
.mobile .brks { grid-template-columns:repeat(2, minmax(0,1fr)); }
.mobile .tabs { position:sticky; bottom:8px; margin:0 12px 8px; overflow-x:auto; }
.mobile .chart-wrap { height:160px; }
`;

if (!customElements.get("dacha-pro-card")) customElements.define("dacha-pro-card", DachaProCard);
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "dacha-pro-card")) {
  window.customCards.push({ type: "dacha-pro-card", name: "Дача PRO", description: "Дашборд дачи для настенного планшета" });
}
