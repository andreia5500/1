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
        return new Entity(s.optString("entity_id"), s.optString("state"), s.optJSONObject("attributes"));
    }

    public void update(JSONObject s) {
        state = s.optString("state");
        JSONObject a = s.optJSONObject("attributes");
        attributes = a != null ? a : new JSONObject();
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
