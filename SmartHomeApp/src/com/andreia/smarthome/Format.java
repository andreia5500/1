package com.andreia.smarthome;

import org.json.JSONObject;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Russian texts and icons for entity states. */
public final class Format {

    private static final Map<String, String> STATES = new HashMap<String, String>();
    private static final Map<String, String> WEATHER = new HashMap<String, String>();

    static {
        String[] s = {
                "on", "Вкл", "off", "Выкл", "unavailable", "Недоступно", "unknown", "—",
                "open", "Открыто", "closed", "Закрыто", "opening", "Открывается", "closing", "Закрывается",
                "locked", "Заперто", "unlocked", "Открыто", "locking", "Запирается", "unlocking", "Отпирается",
                "jammed", "Заклинило",
                "heat", "Обогрев", "cool", "Охлаждение", "heat_cool", "Авто", "auto", "Авто",
                "dry", "Осушение", "fan_only", "Вентиляция",
                "heating", "греет", "cooling", "охлаждает", "idle", "Ожидание", "preheating", "прогрев",
                "drying", "сушит", "fan", "вентилятор",
                "disarmed", "Снято с охраны", "armed_away", "Под охраной", "armed_home", "Охрана (дома)",
                "armed_night", "Охрана (ночь)", "armed_vacation", "Охрана (отпуск)",
                "armed_custom_bypass", "Охрана (выборочно)", "arming", "Постановка…", "pending", "Задержка…",
                "disarming", "Снятие…", "triggered", "ТРЕВОГА",
                "playing", "Играет", "paused", "Пауза", "standby", "Ожидание", "buffering", "Загрузка",
                "home", "Дома", "not_home", "Не дома",
                "cleaning", "Уборка", "docked", "На базе", "returning", "Едет на базу", "error", "Ошибка",
                "above_horizon", "Над горизонтом", "below_horizon", "За горизонтом",
                "recording", "Запись", "streaming", "Трансляция",
        };
        for (int i = 0; i < s.length; i += 2) {
            STATES.put(s[i], s[i + 1]);
        }
        String[] w = {
                "clear-night", "Ясно", "cloudy", "Облачно", "exceptional", "Аномально", "fog", "Туман",
                "hail", "Град", "lightning", "Гроза", "lightning-rainy", "Гроза с дождём",
                "partlycloudy", "Переменная облачность", "pouring", "Ливень", "rainy", "Дождь",
                "snowy", "Снег", "snowy-rainy", "Снег с дождём", "sunny", "Ясно", "windy", "Ветрено",
                "windy-variant", "Ветрено",
        };
        for (int i = 0; i < w.length; i += 2) {
            WEATHER.put(w[i], w[i + 1]);
        }
    }

    private Format() {
    }

    public static String state(String state) {
        String t = STATES.get(state);
        return t != null ? t : state;
    }

    /** Text for the state of any entity, including binary sensors with a device class. */
    public static String stateOf(Entity e) {
        if (!e.available()) {
            return state(e.state);
        }
        switch (e.domain) {
            case "binary_sensor":
                return binary(e.deviceClass(), "on".equals(e.state));
            case "weather":
                String w = WEATHER.get(e.state);
                return w != null ? w : e.state;
            case "sensor":
            case "number":
            case "input_number":
                return value(e);
            case "input_datetime":
            case "timestamp":
                return e.state.replace('T', ' ');
            default:
                return state(e.state);
        }
    }

    static String binary(String deviceClass, boolean on) {
        switch (deviceClass) {
            case "door":
            case "garage_door":
            case "window":
            case "opening":
                return on ? "Открыто" : "Закрыто";
            case "motion":
            case "occupancy":
            case "presence":
                return on ? "Обнаружено" : "Нет";
            case "moisture":
                return on ? "Протечка!" : "Сухо";
            case "smoke":
            case "gas":
            case "carbon_monoxide":
                return on ? "ТРЕВОГА" : "Норма";
            case "battery":
                return on ? "Разряжена" : "Норма";
            case "connectivity":
                return on ? "На связи" : "Нет связи";
            case "plug":
            case "power":
                return on ? "Есть" : "Нет";
            case "lock":
                return on ? "Открыто" : "Заперто";
            case "problem":
                return on ? "Проблема" : "Норма";
            case "running":
                return on ? "Работает" : "Остановлено";
            case "update":
                return on ? "Есть обновление" : "Актуально";
            default:
                return on ? "Вкл" : "Выкл";
        }
    }

    /** Sensor value with its unit; numbers get a decimal comma and at most 2 decimals. */
    public static String value(Entity e) {
        String unit = e.attributes.optString("unit_of_measurement", "");
        String v = number(e.state);
        if ("timestamp".equals(e.deviceClass())) {
            v = e.state.length() >= 16 ? e.state.substring(0, 16).replace('T', ' ') : e.state;
        } else if (v == null) {
            v = state(e.state);
        }
        if (unit.isEmpty()) {
            return v;
        }
        return unit.startsWith("°") || unit.equals("%") ? v + unit : v + " " + unit;
    }

    /** "21.50" -> "21,5"; returns null for non-numbers. */
    public static String number(String s) {
        if (s == null || s.isEmpty()) {
            return null;
        }
        try {
            double d = Double.parseDouble(s);
            if (Double.isNaN(d) || Double.isInfinite(d)) {
                return null;
            }
            return number(d);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public static String number(double d) {
        String t;
        if (Math.abs(d) >= 1000) {
            t = String.format(Locale.US, "%.0f", d);
        } else {
            t = String.format(Locale.US, "%.2f", d);
            t = t.replaceAll("0+$", "").replaceAll("\\.$", "");
        }
        if (t.equals("-0")) {
            t = "0";
        }
        return t.replace('.', ',').replace('-', '−');
    }

    /** Subtitle for thermostats: "Сейчас 12,4° · Обогрев · греет". */
    public static String climate(Entity e) {
        StringBuilder sb = new StringBuilder();
        JSONObject a = e.attributes;
        if (a.has("current_temperature") && !a.isNull("current_temperature")) {
            sb.append("Сейчас ").append(number(a.optDouble("current_temperature"))).append("°");
        }
        if (sb.length() > 0) sb.append(" · ");
        sb.append(state(e.state));
        String action = a.optString("hvac_action", "");
        if (!action.isEmpty() && !"off".equals(action) && !"idle".equals(action)) {
            sb.append(" · ").append(state(action));
        }
        String preset = a.optString("preset_mode", "");
        if (!preset.isEmpty() && !"none".equals(preset)) {
            sb.append(" · ").append(preset(preset));
        }
        return sb.toString();
    }

    public static String preset(String p) {
        switch (p) {
            case "away": return "Не дома";
            case "comfort": return "Комфорт";
            case "home": return "Дома";
            case "sleep": return "Сон";
            case "eco": return "Эко";
            case "boost": return "Турбо";
            case "auto": return "Авто";
            case "manual": return "Ручной";
            case "none": return "Без пресета";
            default: return p;
        }
    }

    public static String icon(Entity e) {
        String dc = e.deviceClass();
        switch (e.domain) {
            case "light": return "💡";
            case "switch": return dc.equals("outlet") ? "🔌" : "⏻";
            case "fan": return "🌀";
            case "input_boolean": return "☑";
            case "automation": return "🤖";
            case "climate": return "🌡";
            case "water_heater": return "♨";
            case "cover": return dc.equals("garage") || dc.equals("gate") ? "🚪" : "▤";
            case "scene": return "🎬";
            case "script": return "📜";
            case "button":
            case "input_button": return "🔘";
            case "alarm_control_panel": return "🛡";
            case "media_player": return "🎵";
            case "vacuum": return "🧹";
            case "lock": return "🔒";
            case "camera": return "📷";
            case "weather": return "⛅";
            case "person":
            case "device_tracker": return "👤";
            case "sun": return "☀";
            case "binary_sensor":
                switch (dc) {
                    case "door": case "garage_door": case "opening": return "🚪";
                    case "window": return "🪟";
                    case "motion": case "occupancy": case "presence": return "🚶";
                    case "moisture": return "💧";
                    case "smoke": case "gas": case "carbon_monoxide": return "🔥";
                    case "connectivity": return "📶";
                    default: return "◉";
                }
            case "sensor":
                switch (dc) {
                    case "temperature": return "🌡";
                    case "humidity": case "moisture": return "💧";
                    case "power": case "energy": case "current": case "voltage": return "⚡";
                    case "battery": return "🔋";
                    case "illuminance": return "☀";
                    case "pressure": return "⏲";
                    case "signal_strength": return "📶";
                    default: return "📈";
                }
            default:
                return "•";
        }
    }
}
