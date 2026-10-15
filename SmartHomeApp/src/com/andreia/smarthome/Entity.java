package com.andreia.smarthome;

import org.json.JSONArray;
import org.json.JSONObject;

/** One Home Assistant entity: its current state plus what the registry knows about it. */
public final class Entity {

    public enum Kind { TOGGLE, LIGHT, CLIMATE, COVER, ACTION, ALARM, MEDIA, VACUUM, LOCK, CAMERA, VALUE }

    public final String id;
    public final String domain;
    public String state;
    public JSONObject attributes;
    /** When the state last changed, epoch ms (0 if unknown). */
    public long lastChanged;

    // From the entity/device/area registries (may stay empty).
    public String area;
    public String category; // "config", "diagnostic" or null
    public boolean hidden;

    public Entity(String id, String state, JSONObject attributes) {
        this.id = id;
        this.domain = id.substring(0, id.indexOf('.'));
        this.state = state;
        this.attributes = attributes != null ? attributes : new JSONObject();
    }

    public static Entity fromState(JSONObject s) {
        Entity e = new Entity(s.optString("entity_id"), s.optString("state"), s.optJSONObject("attributes"));
        e.lastChanged = parseTime(s.optString("last_changed", ""));
        return e;
    }

    public void update(JSONObject s) {
        state = s.optString("state");
        JSONObject a = s.optJSONObject("attributes");
        attributes = a != null ? a : new JSONObject();
        long t = parseTime(s.optString("last_changed", ""));
        if (t > 0) {
            lastChanged = t;
        }
    }

    /** Parses HA timestamps like "2026-10-15T07:58:18.265959+00:00"; 0 on failure. */
    public static long parseTime(String iso) {
        if (iso == null || iso.length() < 19) {
            return 0;
        }
        try {
            java.util.Calendar c = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"));
            c.clear();
            c.set(Integer.parseInt(iso.substring(0, 4)), Integer.parseInt(iso.substring(5, 7)) - 1,
                    Integer.parseInt(iso.substring(8, 10)), Integer.parseInt(iso.substring(11, 13)),
                    Integer.parseInt(iso.substring(14, 16)), Integer.parseInt(iso.substring(17, 19)));
            long ms = c.getTimeInMillis();
            int tz = Math.max(iso.lastIndexOf('+'), iso.lastIndexOf('-'));
            if (tz > 18 && iso.length() >= tz + 6) {
                int sign = iso.charAt(tz) == '-' ? -1 : 1;
                int offMin = Integer.parseInt(iso.substring(tz + 1, tz + 3)) * 60
                        + Integer.parseInt(iso.substring(tz + 4, tz + 6));
                ms -= sign * offMin * 60000L;
            }
            return ms;
        } catch (RuntimeException e) {
            return 0;
        }
    }

    public String name() {
        String n = attributes.optString("friendly_name", "").trim();
        return n.isEmpty() ? id : n;
    }

    public boolean available() {
        return !"unavailable".equals(state) && !"unknown".equals(state);
    }

    public boolean isOn() {
        switch (domain) {
            case "lock":
                return "locked".equals(state);
            case "cover":
                return !"closed".equals(state);
            default:
                return "on".equals(state) || "open".equals(state) || "home".equals(state)
                        || "playing".equals(state);
        }
    }

    public String deviceClass() {
        return attributes.optString("device_class", "");
    }

    public int features() {
        return attributes.optInt("supported_features", 0);
    }

    /** True for user-facing entities: not hidden, not a config/diagnostic setting. */
    public boolean primary() {
        return !hidden && category == null;
    }

    public Kind kind() {
        switch (domain) {
            case "light":
                return Kind.LIGHT;
            case "switch":
            case "fan":
            case "input_boolean":
            case "automation":
            case "siren":
            case "humidifier":
                return Kind.TOGGLE;
            case "climate":
            case "water_heater":
                return Kind.CLIMATE;
            case "cover":
                return Kind.COVER;
            case "scene":
            case "script":
            case "button":
            case "input_button":
                return Kind.ACTION;
            case "alarm_control_panel":
                return Kind.ALARM;
            case "media_player":
                return Kind.MEDIA;
            case "vacuum":
                return Kind.VACUUM;
            case "lock":
                return Kind.LOCK;
            case "camera":
                return Kind.CAMERA;
            default:
                return Kind.VALUE;
        }
    }

    public boolean controllable() {
        Kind k = kind();
        return k != Kind.VALUE && k != Kind.CAMERA;
    }

    /** Light supports brightness (anything other than plain on/off). */
    public boolean dimmable() {
        JSONArray modes = attributes.optJSONArray("supported_color_modes");
        if (modes == null) {
            return attributes.has("brightness");
        }
        for (int i = 0; i < modes.length(); i++) {
            String m = modes.optString(i);
            if (!"onoff".equals(m)) {
                return true;
            }
        }
        return false;
    }
}
