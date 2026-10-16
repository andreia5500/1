/* Дача PRO — дашборд одной карточкой (custom:dacha-pro-card). v1.0.1 */
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

const LIGHTS = [
  { group: "Улица", items: [["Улица", "switch.svet_ulitsa_z2"], ["Баня", "switch.svet_bania_z2"], ["Терраса", "switch.svet_terrasa_z2"]] },
  { group: "1 этаж", items: [["Туал.", "switch.0xa4c1382800b07340"], ["Комн. 1", "switch.0xa4c1387e50957968_left"], ["Комн. 2", "switch.0xa4c1387e50957968_right"], ["Спальня", "switch.0xa4c138459a6af661"]] },
  { group: "2 этаж", items: [["Л1", "switch.0xa4c138a71f7d780b_l1"], ["Л2", "switch.0xa4c138a71f7d780b_l2"], ["Л3", "switch.0xa4c138a71f7d780b_l3"], ["Л4", "switch.0xa4c138a71f7d780b_l4"]] },
];

const LOADS = [
  ["Вода", "switch.0xa4c13841d4a7bb3a"],
  ["Вытяжка", "switch.0xa4c138150cd653bd"],
  ["Бойлер", "switch.obogrev_lestnitsa"],
  ["Пол туал.", "switch.0xa4c13859b38594c2"],
  ["Штора", "cover.0x7cc6b6fffec1a5dd"],
  ["Пылесос", "vacuum.robot_pylesos_dacha_robot_pylesos_dacha"],
];

const WATERING = [["Газон", "switch.0xa4c138850a555bb4_l1"], ["Клубника", "switch.0xa4c138850a555bb4_l2"], ["Бочка", "switch.0xa4c138850a555bb4_l3"]];

const CAMERAS = [
  ["Ворота", "camera.auto_door", "auto_door"],
  ["Вход", "camera.front_door", "front_door"],
  ["Баня", "camera.banya", "banya"],
  ["Терраса", "camera.terrasa", "terrasa"],
  ["Бассейн", "camera.bassein", "bassein"],
  ["Дом", "camera.dom3", "dom3"],
];
const CAM_WHERE = { auto_door: "у ворот", front_door: "у входа", banya: "у бани", terrasa: "на террасе", bassein: "у бассейна", dom3: "у дома", ulica: "на улице" };

const NAV = [
  ["overview", "Обзор"], ["light", "Свет"], ["climate", "Климат"], ["pool", "Бассейн"],
  ["water", "Полив"], ["cams", "Камеры"], ["energy", "Энергия"], ["system", "Система"],
];

const BAD = ["unknown", "unavailable", "", undefined, null];
const nf = (v, d = 1) => Number(v).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(Math.abs(v), d);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const hm = (d) => d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
const dur = (min) => {
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return h ? `${h} ч ${m} мин` : `${m} мин`;
};

class DachaProCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hist = {};
    this._nav = "overview";
    this._theme = null;
    this._sig = "";
    try { this._theme = localStorage.getItem("dacha-pro-theme"); } catch (e) { /* storage недоступен */ }
  }

  setConfig(config) { this._config = config || {}; }
  getCardSize() { return 20; }
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
    if (this._hass) this._loadHistory();
  }

  disconnectedCallback() {
    clearInterval(this._clock);
    clearInterval(this._histTimer);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._loadHistory();
    this._render();
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

  outside() {
    const t = this.n(E.outTemp);
    for (const w of E.weather) {
      const o = this.st(w);
      if (o && !BAD.includes(o.state)) {
        const wind = o.attributes.wind_speed;
        const unit = o.attributes.wind_speed_unit || "km/h";
        const ms = wind == null ? null : unit === "m/s" ? wind : wind / 3.6;
        return { t: t ?? o.attributes.temperature, wind: ms };
      }
    }
    return { t, wind: null };
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

  spark(vals, { h = 40, fill = true, color = "var(--blue)" } = {}) {
    const v = vals.filter((x) => x !== null);
    if (v.length < 2) return `<div class="spark-empty" style="height:${h}px"></div>`;
    const w = 300;
    let min = Math.min(...v), max = Math.max(...v);
    if (max - min < 1e-6) { min -= 1; max += 1; }
    const d = this.path(vals, w, h, min, max);
    const area = fill ? `<path d="${d} L${w},${h} L0,${h} Z" fill="var(--spark-fill)"/>` : "";
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="height:${h}px">${area}<path d="${d}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>`;
  }

  climateChart() {
    const series = CLIMATE.map((c) => this.series(c.temp, 24));
    const all = series.flat().filter((x) => x !== null);
    const w = 600, h = 130;
    if (all.length < 2) return `<div class="chart-empty">загрузка истории…</div>`;
    let min = Math.floor(Math.min(...all) - 1), max = Math.ceil(Math.max(...all) + 1);
    const grid = [0.25, 0.5, 0.75, 1].map((f) => `<line x1="0" x2="${w}" y1="${(h * f).toFixed(1)}" y2="${(h * f).toFixed(1)}" stroke="var(--grid)" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join("");
    const lines = series.map((s, i) => `<path d="${this.path(s, w, h, min, max, 6)}" fill="none" stroke="${CLIMATE[i].color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`).join("");
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${grid}${lines}</svg>`;
  }

  /* ---------- блоки ---------- */
  chip(name, id, opts = {}) {
    const st = this.s(id);
    const active = opts.active ?? (["on", "open", "opening", "cleaning", "heat"].includes(st));
    const off = BAD.includes(st);
    return `<button class="chip ${active ? "on" : ""} ${off ? "na" : ""} ${opts.cls || ""}" data-act="${opts.act || "toggle"}" data-id="${id}" title="${esc(name)}"><span class="dot"></span><span class="lbl">${esc(name)}</span></button>`;
  }

  row(label, value, cls = "") {
    return `<div class="row"><span>${esc(label)}</span><span class="val ${cls}">${value}</span></div>`;
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
    this.shadowRoot.innerHTML = `<style>${CSS}</style>${html}`;
    this._bind();
  }

  _html() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
    const theme = this._theme || "dark";
    const status = this.status();
    const out = this.outside();
    const ups = this.n(E.ups), upsV = this.n(E.upsVolt), fps = this.n(E.fps);
    const upsOk = String(this.s(E.upsStatus) || "OL").startsWith("OL");

    /* охрана */
    const al = this.s(E.alarm);
    const alText = { disarmed: "Снято с охраны", armed_away: "На охране", armed_home: "Охрана · дома", armed_night: "Охрана · ночь", arming: "Постановка…", pending: "Ожидание…", triggered: "Тревога!" }[al] || "Нет связи";
    const dc = this.doorCount();
    const doorsText = dc.open ? `Открыто дверей: ${dc.open}` : "Все двери закрыты";
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
      `Ступень ${stage} из ${STAGES.length}`,
      rate !== null ? `≈${nf(rate, 2)} °C/ч` : null,
      maxTarget !== null ? `до ${sgn(maxTarget, 0)}°${eta ? ` ~${dur(eta * 60)}` : ""}` : null,
    ].filter(Boolean).join(" · ");

    /* бассейн */
    const pool = this.n(E.poolTemp);
    const fw = this.filterWindows();
    const smartOn = this.on(E.poolSmart);
    const poolMeta = smartOn ? "фильтрация по расписанию" : (this.s(E.poolStatus) || "ручной режим");

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
    const summer = this.on(E.season);

    const v = (x, d = 1, suf = "") => (x === null ? "—" : nf(x, d) + suf);
    const temp = (x) => (x === null ? "—" : `${sgn(x, 1)}°`);

    const climateCards = CLIMATE.map((c) => {
      const cur = this.a(c.climate, "current_temperature") ?? this.n(c.temp);
      const tgt = this.a(c.climate, "temperature");
      const heating = this.on(c.heater);
      const pw = this.n(c.power);
      const sub = heating ? `обогрев ${pw !== null && pw > 0 ? nf(pw / 1000, 1) + " кВт" : "вкл"}` : "обогрев выкл";
      return `<div class="room tap" data-act="more" data-id="${c.climate}">
        <div class="room-h"><span class="room-n">${c.name}</span><span class="muted">${tgt != null ? `цель ${Math.round(tgt)}°` : ""}</span></div>
        <div class="big2">${temp(cur)}</div>
        <div class="muted ${heating ? "hot" : ""}">${sub}</div>
      </div>`;
    }).join("");

    const loadTile = (title, value, sub, id, onState) => `
      <div class="load tap" data-act="more" data-id="${id}">
        <div class="load-h"><span>${title}</span><span class="dot ${onState ? "dot-on" : ""}"></span></div>
        <div class="load-v">${value}</div>
        <div class="muted">${sub}</div>
      </div>`;
    const septP = this.n(E.septikPower);
    const septOn = this.on(E.septik);
    const plitaOn = this.on(E.plita);
    const heatP = this.n(E.heatPower), mainP = this.n(E.mainPower);

    return `
<div class="root theme-${theme}">
  <aside class="side">
    <div class="brand"><div class="eyebrow">Home Assistant</div><div class="brand-n">${esc(this._config.title || "Дача")}</div></div>
    <nav>${NAV.map(([k, t]) => `<button class="nav ${this._nav === k ? "active" : ""}" data-act="nav" data-id="${k}"><span class="dot"></span>${t}</button>`).join("")}</nav>
    <div class="side-foot">
      <div class="season">
        <div class="eyebrow">Режим сезона</div>
        <div class="seg">
          <button class="${summer ? "sel" : ""}" data-act="season" data-id="on">Лето</button>
          <button class="${summer ? "" : "sel"}" data-act="season" data-id="off">Зима</button>
        </div>
      </div>
      <div class="updated">Обновлено ${hm(this._histAt || now)} · локально</div>
    </div>
  </aside>

  <main class="main">
    <header class="top">
      <div>
        <div class="eyebrow">${esc(dateStr)} · ${hm(now)}</div>
        <h1 class="title lvl-${status.lvl}">${status.text}</h1>
      </div>
      <div class="pills">
        <span class="pill tap" data-act="more" data-id="${E.weather.find((w) => this.st(w) && !BAD.includes(this.s(w))) || E.outTemp}"><span class="dot"></span>Погода ${temp(out.t)}</span>
        <span class="pill tap ${upsOk ? "" : "warn"}" data-act="more" data-id="${E.ups}"><span class="dot"></span>ИБП ${ups === null ? "—" : Math.round(ups) + "%"}${upsV !== null ? ` · ${Math.round(upsV)} В` : ""}</span>
        <span class="pill tap" data-act="more" data-id="${E.fps}"><span class="dot"></span>Frigate ${v(fps, 1)} fps</span>
        <button class="pill icon" data-act="theme" title="Тема">${theme === "dark" ? SUN : MOON}</button>
      </div>
    </header>

    <section class="grid">
      <div class="card c3" id="sec-security">
        <div class="ch"><span class="eyebrow">Охрана</span><span class="muted">${dc.total} зон</span></div>
        <div class="h2 ${al === "triggered" ? "bad" : ""}">${alText}</div>
        <div class="muted">${doorsText}</div>
        <div class="btns">
          <button class="btn ${armed ? "primary" : ""}" data-act="disarm">Я дома</button>
          <button class="btn ${armed ? "" : "primary"}" data-act="arm">Ухожу</button>
        </div>
      </div>

      <div class="card c3 tap" id="sec-energy" data-act="more" data-id="${E.power}">
        <div class="ch"><span class="eyebrow">Мощность сети</span><span class="muted">сейчас</span></div>
        <div class="big">${p === null ? "—" : Math.round(p).toLocaleString("ru-RU")} <small>Вт</small></div>
        ${this.spark(this.series(E.power, 12, 10 * 60e3), { h: 34 })}
        <div class="cf muted"><span>Общий 63 А · ${v(mainV, 0)} В</span><span>сутки ${kwh === null ? "—" : nf(kwh, 1)} кВт·ч</span></div>
      </div>

      <div class="card c3 split">
        <div class="half tap" data-act="more" data-id="${E.weather.find((w) => this.st(w) && !BAD.includes(this.s(w))) || E.outTemp}">
          <span class="eyebrow">На улице</span>
          <div class="big">${temp(out.t)}</div>
          <div class="muted">${out.wind === null ? "&nbsp;" : `ветер ${Math.round(out.wind)} м/с`}</div>
        </div>
        <div class="vsep"></div>
        <div class="half tap" data-act="more" data-id="${E.inTemp}">
          <span class="eyebrow">В доме</span>
          <div class="big">${temp(inT)}</div>
          <div class="muted">мин. зона ${temp(minZ)}</div>
        </div>
      </div>

      <div class="card c3">
        <div class="ch"><span class="eyebrow">Датчики безопасности</span></div>
        <div class="list">
          <div class="row tap" data-act="more" data-id="${E.doors}"><span><i class="bul ${dc.open ? "warn" : ""}"></i>Двери</span><span class="val ${dc.open ? "warn" : ""}">${dc.open ? `Открыто · ${dc.open}` : `Закрыты · ${dc.total}`}</span></div>
          <div class="row tap" data-act="more" data-id="${E.leak}"><span><i class="bul ${this.on(E.leak) ? "bad" : ""}"></i>Протечка</span><span class="val ${this.on(E.leak) ? "bad" : ""}">${this.on(E.leak) ? "ПРОТЕЧКА" : "Сухо"} · ${(this.a(E.leak, "entity_id") || []).length || 1}</span></div>
          <div class="row tap" data-act="more" data-id="${E.smoke}"><span><i class="bul ${this.on(E.smoke) ? "bad" : ""}"></i>Дым и CO</span><span class="val ${this.on(E.smoke) ? "bad" : ""}">${this.on(E.smoke) ? "ТРЕВОГА" : "Норма"} · ${(this.a(E.smoke, "entity_id") || []).length || 1}</span></div>
        </div>
      </div>

      <div class="card c8" id="sec-climate">
        <div class="ch"><span class="eyebrow">Климат и отопление</span><span class="muted">${esc(climMeta)}</span></div>
        <div class="rooms">${climateCards}</div>
        ${this.climateChart()}
        <div class="cf"><span class="legend">${CLIMATE.map((c) => `<span><i style="background:${c.color}"></i>${c.name}</span>`).join("")}</span><span class="muted">последние 24 часа</span></div>
      </div>

      <div class="card c4 ${summer ? "" : "dim"}" id="sec-pool">
        <div class="ch"><span class="eyebrow">Бассейн</span><span class="muted">${esc(poolMeta)}</span></div>
        <div class="big tap" data-act="more" data-id="${E.poolTemp}">${pool === null ? "—" : nf(pool, 1) + "°"} <small>вода</small></div>
        ${this.spark(this.series(E.poolTemp, 24), { h: 56, fill: false })}
        <div class="track">${fw.wins.map(([a, b]) => `<i style="left:${(a * 100).toFixed(2)}%;width:${Math.max(0.6, (b - a) * 100).toFixed(2)}%"></i>`).join("")}</div>
        <div class="cf muted"><span>окна фильтрации за сутки</span><span>${fw.total ? dur(fw.total) : "0 мин"}</span></div>
        <div class="two">
          ${this.chip("Фильтр", E.poolFilter, { cls: "wide" })}
          ${this.chip("Нагрев", E.poolHeat, { cls: "wide" })}
        </div>
        <div class="list">
          ${this.row("Поток воды", this.on(E.poolFlow) ? "есть" : "нет", this.on(E.poolFlow) ? "" : "warn")}
          <div class="row tap" data-act="toggle" data-id="${E.poolSmart}"><span>Умный фильтр</span><span class="val">${smartOn ? "включён" : "выключен"}</span></div>
        </div>
      </div>

      <div class="card c5" id="sec-light">
        <div class="ch"><span class="eyebrow">Свет</span><span class="muted">включено ${lightsOn} из ${lightIds.length}</span></div>
        ${LIGHTS.map((g) => `<div class="sub">${g.group}</div><div class="chips n${g.items.length}">${g.items.map(([n, id]) => this.chip(n, id)).join("")}</div>`).join("")}
      </div>

      <div class="card c7" id="sec-loads">
        <div class="ch"><span class="eyebrow">Нагрузки и автоматы</span><span class="muted">суммарно ${p === null ? "—" : nf(p / 1000, 2)} кВт</span></div>
        <div class="loads">
          ${loadTile("Общий 63 А", mainP === null ? "—" : `${Math.round(mainP).toLocaleString("ru-RU")} Вт`, `${v(mainV, 0)} В${mainA !== null ? ` · ${nf(mainA, 1)} А` : ""}`, E.mainSw, this.on(E.mainSw))}
          ${loadTile("Обогрев", heatP === null ? "—" : `${Math.round(heatP).toLocaleString("ru-RU")} Вт`, `${v(this.n(E.heatVolt), 0)} В`, E.heatSw, this.on(E.heatSw))}
          ${loadTile("Плита 380", plitaOn ? "Вкл" : "Выкл", "резерв нагрева", E.plita, plitaOn)}
          ${loadTile("Септик", septP === null ? (septOn ? "Вкл" : "Выкл") : `${Math.round(septP)} Вт`, septOn ? "обогрев" : "простой", E.septik, septOn)}
        </div>
        <div class="chips n6">${LOADS.map(([n, id]) => this.chip(n, id, { act: id.startsWith("vacuum.") ? "more" : "toggle" })).join("")}</div>
      </div>

      <div class="card c3 ${summer ? "" : "dim"}" id="sec-water">
        <div class="ch"><span class="eyebrow">Полив</span><span class="muted">бочка ${temp(this.n(E.barrelTemp))}</span></div>
        <div class="chips n2">
          ${WATERING.map(([n, id]) => this.chip(n, id)).join("")}
          <button class="chip" data-act="stopwater"><span class="dot"></span><span class="lbl">Стоп</span></button>
        </div>
        <div class="list">
          <div class="row tap" data-act="more" data-id="${E.soil}"><span>Теплица, влажность</span><span class="val">${v(this.n(E.soil), 0, " %")}</span></div>
          <div class="row tap" data-act="toggle" data-id="${E.autoWater}"><span>Автополив</span><span class="val">${this.on(E.autoWater) ? "по расписанию" : "выключен"}</span></div>
        </div>
      </div>

      <div class="card c5" id="sec-cams">
        <div class="ch"><span class="eyebrow">Камеры</span><span class="muted">${esc(camMeta)}</span></div>
        <div class="cams">${CAMERAS.map(([n, id]) => {
          const pic = this.a(id, "entity_picture");
          const src = pic ? this._hass.hassUrl(pic) : "";
          return `<div class="cam tap" data-act="more" data-id="${id}"><div class="shot">${src ? `<img src="${esc(src)}" loading="lazy" alt="">` : ""}</div><span>${n}</span></div>`;
        }).join("")}</div>
      </div>

      <div class="card c4" id="sec-system">
        <div class="ch"><span class="eyebrow">Система</span><span class="muted">${esc(host)}</span></div>
        <div class="list big-rows">
          <div class="row tap" data-act="more" data-id="${E.cpu}"><span>Процессор</span><span class="val">${v(this.n(E.cpu), 0, " %")} · ${v(this.n(E.cpuTemp), 0, " °C")}</span></div>
          <div class="row tap" data-act="more" data-id="${E.mem}"><span>Память · диск</span><span class="val">${v(this.n(E.mem), 0, " %")} · ${v(this.n(E.disk), 0, " %")}</span></div>
          <div class="row tap" data-act="more" data-id="${E.backupOk}"><span>Бэкап</span><span class="val ${bk.cls}">${bk.text}</span></div>
          <div class="row"><span>Батареи датчиков</span><span class="val ${bat.cls}">${bat.text}</span></div>
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
        this._action(el.dataset.act, el.dataset.id, el);
      });
    });
  }

  async _call(domain, service, data) {
    try {
      await this._hass.callService(domain, service, data);
    } catch (e) {
      console.warn("dacha-pro-card", e);
      if (data && data.entity_id) this._more(data.entity_id);
    }
  }

  _more(entityId) {
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  _action(act, id, el) {
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
        const target = {
          overview: null, light: "sec-light", climate: "sec-climate", pool: "sec-pool", water: "sec-water",
          cams: "sec-cams", energy: "sec-loads", system: "sec-system",
        }[id];
        this._render(true);
        const el2 = target && this.shadowRoot.getElementById(target);
        if (el2) {
          el2.scrollIntoView({ behavior: "smooth", block: "center" });
          el2.classList.add("flash");
          setTimeout(() => el2.classList.remove("flash"), 1200);
        } else {
          this.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        if (id === "cams" && this._config.cameras_path) {
          history.pushState(null, "", this._config.cameras_path);
          window.dispatchEvent(new CustomEvent("location-changed"));
        }
        return;
      }
    }
  }
}

const SUN = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`;
const MOON = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>`;

const CSS = `
:host { display:block; }
.root {
  --bg:#121315; --side:#16171a; --card:#18191c; --card2:#1d1e22; --line:#2a2b30; --line2:#25262a;
  --text:#f3f3f5; --muted:#9b9ca3; --faint:#6d6e75; --blue:#8ab9ec; --blue-strong:#7fb3ea; --blue-bg:#1f2c3d; --blue-text:#9cc6f2;
  --orange:#e6a24a; --grey:#a9aab0; --red:#ef6b63; --warn:#e6a24a; --grid:#26272b; --spark-fill:rgba(138,185,236,.14);
  --primary-btn:#8ab9ec; --primary-btn-text:#0f1a26;
  font-family: Inter, -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
  color:var(--text); background:var(--bg);
  display:grid; grid-template-columns:268px 1fr; min-height:calc(100vh - var(--header-height, 56px)); box-sizing:border-box;
  -webkit-font-smoothing:antialiased; font-feature-settings:"tnum" 1, "cv11" 1;
}
.root.theme-light {
  --bg:#f3f3f1; --side:#ecebe8; --card:#ffffff; --card2:#fafaf8; --line:#e2e1dd; --line2:#ebeae6;
  --text:#18191c; --muted:#6b6c72; --faint:#9a9ba0; --blue:#3b82c9; --blue-strong:#3b82c9; --blue-bg:#e3eefa; --blue-text:#2463a6;
  --orange:#d48a2a; --grey:#8d8e94; --grid:#ecebe7; --spark-fill:rgba(59,130,201,.12); --primary-btn:#3b82c9; --primary-btn-text:#fff;
}
*, *::before, *::after { box-sizing:border-box; }
button { font:inherit; color:inherit; cursor:pointer; }
.eyebrow { font-size:12px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.muted { color:var(--muted); font-size:14px; }
.tap { cursor:pointer; }

/* sidebar */
.side { background:var(--side); border-right:1px solid var(--line2); padding:28px 20px 20px; display:flex; flex-direction:column; position:sticky; top:var(--header-height, 56px); height:calc(100vh - var(--header-height, 56px)); }
.brand-n { font-size:28px; font-weight:600; margin-top:6px; letter-spacing:-.01em; }
nav { display:flex; flex-direction:column; gap:6px; margin-top:34px; }
.nav { display:flex; align-items:center; gap:14px; text-align:left; background:none; border:0; border-radius:12px; padding:14px 18px; font-size:17px; color:var(--text); opacity:.92; }
.nav .dot { width:6px; height:6px; border-radius:50%; background:var(--faint); }
.nav:hover { background:var(--card2); }
.nav.active { background:var(--blue-bg); color:var(--blue-text); font-weight:500; opacity:1; }
.nav.active .dot { background:var(--blue); }
.side-foot { margin-top:auto; }
.season { border:1px solid var(--line); border-radius:14px; padding:16px 16px 14px; background:var(--card); }
.seg { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:14px; }
.seg button { border:0; background:none; border-radius:10px; padding:11px 0; font-size:16px; color:var(--muted); }
.seg button.sel { background:var(--primary-btn); color:var(--primary-btn-text); font-weight:500; }
.updated { color:var(--muted); font-size:14px; margin-top:16px; padding-left:8px; }

/* main */
.main { padding:28px 34px 34px; min-width:0; }
.top { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; margin-bottom:22px; flex-wrap:wrap; }
.title { font-size:36px; font-weight:600; letter-spacing:-.02em; margin:8px 0 0; line-height:1.15; }
.title.lvl-bad { color:var(--red); } .title.lvl-warn { color:var(--warn); }
.pills { display:flex; gap:12px; flex-wrap:wrap; }
.pill { display:inline-flex; align-items:center; gap:10px; height:52px; padding:0 18px; border:1px solid var(--line); border-radius:12px; background:var(--card); font-size:17px; font-weight:500; white-space:nowrap; }
.pill .dot { width:7px; height:7px; border-radius:50%; background:var(--blue); }
.pill.warn .dot { background:var(--warn); }
.pill.icon { width:52px; justify-content:center; padding:0; color:var(--text); }

.grid { display:grid; grid-template-columns:repeat(12, minmax(0,1fr)); gap:20px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:22px 22px 20px; min-width:0; transition:box-shadow .3s, border-color .3s; }
.card.flash { border-color:var(--blue); box-shadow:0 0 0 3px var(--blue-bg); }
.card.dim > *:not(.ch) { opacity:.55; }
.c3 { grid-column:span 3; } .c4 { grid-column:span 4; } .c5 { grid-column:span 5; } .c7 { grid-column:span 7; } .c8 { grid-column:span 8; }
.ch { display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin-bottom:14px; }
.ch .muted { text-align:right; font-size:15px; }
.h2 { font-size:24px; font-weight:600; letter-spacing:-.01em; margin-top:4px; }
.h2.bad, .val.bad { color:var(--red); }
.val.warn { color:var(--warn); }
.big { font-size:46px; font-weight:300; letter-spacing:-.02em; line-height:1.1; white-space:nowrap; }
.big small { font-size:15px; font-weight:400; color:var(--muted); letter-spacing:0; }
.big2 { font-size:36px; font-weight:300; letter-spacing:-.01em; margin:8px 0 6px; }
.cf { display:flex; justify-content:space-between; gap:10px; align-items:center; margin-top:10px; font-size:15px; }

.btns { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:20px; }
.btn { height:50px; border-radius:10px; border:1px solid var(--line); background:var(--card2); font-size:16px; font-weight:500; }
.btn.primary { background:var(--primary-btn); color:var(--primary-btn-text); border-color:transparent; }

.spark { width:100%; display:block; margin-top:10px; }
.spark-empty { margin-top:10px; }
.chart { width:100%; height:130px; display:block; margin-top:34px; }
.chart-empty { height:130px; margin-top:34px; display:flex; align-items:center; justify-content:center; color:var(--faint); font-size:14px; }

.split { display:flex; gap:20px; }
.split .half { flex:1; min-width:0; }
.split .big { margin-top:12px; font-size:44px; }
.split .muted { margin-top:6px; }
.vsep { width:1px; background:var(--line); margin:4px 0 4px; }

.list { display:flex; flex-direction:column; }
.row { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:13px 0; border-bottom:1px solid var(--line2); font-size:17px; }
.row:last-child { border-bottom:0; }
.row .val { color:var(--muted); font-size:15px; text-align:right; }
.bul { display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--faint); margin-right:14px; vertical-align:middle; }
.bul.warn { background:var(--warn); } .bul.bad { background:var(--red); }
.big-rows .row { padding:14px 0; }

.rooms { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px; }
.room { border:1px solid var(--line); border-radius:14px; padding:16px 18px; background:var(--card); }
.room-h { display:flex; justify-content:space-between; align-items:baseline; }
.room-n { font-size:17px; font-weight:600; }
.hot { color:var(--text); opacity:.85; }
.legend { display:flex; gap:22px; color:var(--muted); }
.legend span { display:inline-flex; align-items:center; gap:8px; }
.legend i { width:7px; height:7px; border-radius:50%; display:inline-block; }

.track { position:relative; height:6px; border-radius:3px; background:var(--line); margin-top:16px; overflow:hidden; }
.track i { position:absolute; top:0; bottom:0; background:var(--blue); border-radius:3px; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:18px 0 8px; }

.sub { color:var(--muted); font-size:16px; margin:14px 0 10px; }
.ch + .sub { margin-top:0; }
.chips { display:grid; gap:10px; }
.chips.n2 { grid-template-columns:repeat(2, minmax(0,1fr)); }
.chips.n3 { grid-template-columns:repeat(3, minmax(0,1fr)); }
.chips.n4 { grid-template-columns:repeat(4, minmax(0,1fr)); }
.chips.n6 { grid-template-columns:repeat(6, minmax(0,1fr)); }
.chip { display:flex; align-items:center; gap:12px; height:56px; padding:0 16px; border-radius:12px; border:1px solid var(--line); background:var(--card); font-size:17px; font-weight:500; text-align:left; min-width:0; transition:background .15s, border-color .15s; }
.chip .lbl { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.chip .dot { width:6px; height:6px; border-radius:50%; background:var(--faint); flex:none; }
.chip:hover { border-color:var(--faint); }
.chip.on { background:var(--blue-bg); border-color:transparent; color:var(--blue-text); }
.chip.on .dot { background:var(--blue); }
.chip.na { opacity:.45; }
.chip.wide { justify-content:space-between; flex-direction:row-reverse; }
.chip.wide .lbl { margin-right:auto; }

.loads { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; margin-bottom:14px; }
.load { border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
.load-h { display:flex; justify-content:space-between; align-items:center; font-size:17px; font-weight:600; }
.load-h .dot { width:7px; height:7px; border-radius:50%; background:var(--faint); }
.load-h .dot-on { background:var(--blue); }
.load-v { font-size:30px; font-weight:300; margin:6px 0 2px; white-space:nowrap; }

.cams { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:10px; }
.cam span { display:block; color:var(--muted); font-size:15px; margin-top:10px; }
.shot { aspect-ratio:4/3; border:1px solid var(--line); border-radius:10px; background:var(--card2); overflow:hidden; }
.shot img { width:100%; height:100%; object-fit:cover; display:block; }

/* адаптив */
@media (max-width: 1500px) {
  .c3 { grid-column:span 6; } .c4, .c5, .c7, .c8 { grid-column:span 12; }
  #sec-pool, #sec-system { grid-column:span 6; } #sec-water { grid-column:span 6; }
  #sec-cams { grid-column:span 12; }
}
@media (max-width: 1100px) {
  .root { grid-template-columns:minmax(0,1fr); }
  .side, .main { min-width:0; }
  .side { position:static; height:auto; flex-direction:row; flex-wrap:wrap; align-items:center; gap:12px; padding:16px; border-right:0; border-bottom:1px solid var(--line2); }
  nav { flex-direction:row; flex-wrap:nowrap; overflow-x:auto; margin:0; width:100%; min-width:0; order:3; scrollbar-width:none; }
  .nav { padding:10px 14px; font-size:15px; white-space:nowrap; }
  .side-foot { margin:0 0 0 auto; display:flex; align-items:center; gap:12px; }
  .season { padding:6px; } .season .eyebrow { display:none; } .seg { margin:0; } .seg button { padding:8px 14px; font-size:15px; }
  .updated { display:none; }
  .main { padding:18px 16px 24px; }
}
@media (max-width: 760px) {
  .grid { gap:14px; }
  .c3, .c4, .c5, .c7, .c8, #sec-pool, #sec-system, #sec-water { grid-column:span 12; }
  .title { font-size:28px; }
  .pill { height:42px; font-size:15px; padding:0 12px; } .pill.icon { width:42px; }
  .rooms { grid-template-columns:1fr; }
  .chips.n4, .chips.n6 { grid-template-columns:repeat(2, minmax(0,1fr)); }
  .loads { grid-template-columns:repeat(2, minmax(0,1fr)); }
  .cams { grid-template-columns:repeat(3, minmax(0,1fr)); }
  .chip { height:50px; font-size:15px; padding:0 12px; gap:10px; }
  .big { font-size:40px; }
  .ch { flex-wrap:wrap; } .ch .muted { text-align:left; }
  .main { padding:16px; }
}
`;

if (!customElements.get("dacha-pro-card")) customElements.define("dacha-pro-card", DachaProCard);
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "dacha-pro-card")) {
  window.customCards.push({ type: "dacha-pro-card", name: "Дача PRO", description: "Дашборд дачи одной карточкой" });
}
