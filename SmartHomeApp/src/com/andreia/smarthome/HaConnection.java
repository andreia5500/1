package com.andreia.smarthome;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;

/**
 * One authenticated Home Assistant WebSocket session: loads states and the
 * registries, streams state changes and calls services. Callbacks arrive on a
 * background thread.
 */
public final class HaConnection implements WebSocketClient.Listener {

    public interface Callback {
        void onConnected();

        void onStates(JSONArray states);

        /** newState is null when the entity was removed. */
        void onStateChanged(String entityId, JSONObject newState);

        /** Any part may be null if the user is not allowed to read it. */
        void onRegistry(JSONObject entities, JSONArray devices, JSONArray areas);

        /** authFailed: the access token was rejected, refresh it before reconnecting. */
        void onDisconnected(String reason, boolean authFailed);
    }

    public interface ResultHandler {
        void onResult(boolean success, String error);
    }

    /** For commands whose answer carries data; result is null on failure. */
    public interface DataHandler {
        void onData(Object result);
    }

    private static final long PING_INTERVAL_MS = 25000;

    private final String baseUrl;
    private final Callback callback;
    private final Map<Integer, ResultHandler> pending = new HashMap<Integer, ResultHandler>();
    private final Map<Integer, DataHandler> pendingData = new HashMap<Integer, DataHandler>();

    private WebSocketClient ws;
    private String accessToken;
    private int nextId = 1;
    private volatile boolean authenticated;
    private volatile boolean authFailed;
    private volatile boolean stopped;
    private Thread pinger;

    private int idStates, idEntityRegistry, idDeviceRegistry, idAreaRegistry;
    private JSONObject entityRegistry;
    private JSONArray deviceRegistry, areaRegistry;
    private int registryAnswers;

    public HaConnection(String baseUrl, Callback callback) {
        this.baseUrl = baseUrl;
        this.callback = callback;
    }

    public static URI websocketUri(String baseUrl) {
        String ws = baseUrl.startsWith("https://")
                ? "wss://" + baseUrl.substring(8)
                : "ws://" + baseUrl.substring(baseUrl.indexOf("://") + 3);
        return URI.create(ws + "/api/websocket");
    }

    /** Connects and authenticates. Blocking network I/O; call off the UI thread. */
    public void start(String token) throws IOException {
        accessToken = token;
        ws = new WebSocketClient(websocketUri(baseUrl), this);
        ws.connect();
    }

    public void stop() {
        stopped = true;
        if (pinger != null) {
            pinger.interrupt();
        }
        if (ws != null) {
            ws.close();
        }
    }

    public boolean isAuthenticated() {
        return authenticated && !stopped;
    }

    public void callService(String domain, String service, String entityId, JSONObject data,
                            ResultHandler handler) {
        try {
            JSONObject msg = new JSONObject();
            msg.put("type", "call_service");
            msg.put("domain", domain);
            msg.put("service", service);
            if (data != null && data.length() > 0) {
                msg.put("service_data", data);
            }
            if (entityId != null) {
                msg.put("target", new JSONObject().put("entity_id", entityId));
            }
            send(msg, handler);
        } catch (JSONException e) {
            handler.onResult(false, e.getMessage());
        }
    }

    /** Sends any command (e.g. history, get_config) and hands back its "result". */
    public void request(JSONObject msg, DataHandler handler) {
        int id;
        synchronized (this) {
            id = nextId++;
            pendingData.put(id, handler);
        }
        try {
            msg.put("id", id);
            ws.send(msg.toString());
        } catch (Exception e) {
            synchronized (this) {
                pendingData.remove(id);
            }
            handler.onData(null);
        }
    }

    private synchronized int send(JSONObject msg, ResultHandler handler) {
        int id = nextId++;
        try {
            msg.put("id", id);
            if (handler != null) {
                pending.put(id, handler);
            }
            ws.send(msg.toString());
        } catch (Exception e) {
            pending.remove(id);
            if (handler != null) {
                handler.onResult(false, "Нет связи с домом");
            }
        }
        return id;
    }

    private int command(String type) {
        try {
            return send(new JSONObject().put("type", type), null);
        } catch (JSONException e) {
            throw new AssertionError(e);
        }
    }

    @Override
    public void onText(String text) {
        try {
            JSONObject msg = new JSONObject(text);
            String type = msg.optString("type");
            if ("auth_required".equals(type)) {
                ws.send(new JSONObject().put("type", "auth").put("access_token", accessToken).toString());
            } else if ("auth_ok".equals(type)) {
                authenticated = true;
                onAuthenticated();
            } else if ("auth_invalid".equals(type)) {
                authFailed = true;
                ws.close();
            } else if ("event".equals(type)) {
                JSONObject data = msg.getJSONObject("event").optJSONObject("data");
                if (data != null) {
                    callback.onStateChanged(data.getString("entity_id"), data.optJSONObject("new_state"));
                }
            } else if ("result".equals(type)) {
                onResult(msg);
            }
            // "pong" needs no handling: any incoming data keeps the read timeout happy.
        } catch (JSONException e) {
            // Ignore malformed messages.
        } catch (IOException e) {
            ws.close();
        }
    }

    private void onAuthenticated() throws JSONException {
        // Subscribe before reading the states so no change falls in between.
        send(new JSONObject().put("type", "subscribe_events").put("event_type", "state_changed"), null);
        idStates = command("get_states");
        idEntityRegistry = command("config/entity_registry/list_for_display");
        idDeviceRegistry = command("config/device_registry/list");
        idAreaRegistry = command("config/area_registry/list");
        callback.onConnected();

        pinger = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    while (!stopped) {
                        Thread.sleep(PING_INTERVAL_MS);
                        command("ping");
                    }
                } catch (InterruptedException ignored) {
                    // Stopped.
                }
            }
        }, "ha-ping");
        pinger.setDaemon(true);
        pinger.start();
    }

    private void onResult(JSONObject msg) {
        int id = msg.optInt("id");
        boolean success = msg.optBoolean("success");
        if (id == idStates) {
            JSONArray states = msg.optJSONArray("result");
            if (states != null) {
                callback.onStates(states);
            }
            return;
        }
        if (id == idEntityRegistry || id == idDeviceRegistry || id == idAreaRegistry) {
            if (success) {
                if (id == idEntityRegistry) entityRegistry = msg.optJSONObject("result");
                if (id == idDeviceRegistry) deviceRegistry = msg.optJSONArray("result");
                if (id == idAreaRegistry) areaRegistry = msg.optJSONArray("result");
            }
            if (++registryAnswers == 3) {
                callback.onRegistry(entityRegistry, deviceRegistry, areaRegistry);
            }
            return;
        }
        ResultHandler handler;
        DataHandler dataHandler;
        synchronized (this) {
            handler = pending.remove(id);
            dataHandler = pendingData.remove(id);
        }
        if (dataHandler != null) {
            dataHandler.onData(success ? msg.opt("result") : null);
            return;
        }
        if (handler != null) {
            String error = null;
            if (!success) {
                JSONObject err = msg.optJSONObject("error");
                error = err != null ? err.optString("message", "Ошибка") : "Ошибка";
            }
            handler.onResult(success, error);
        }
    }

    @Override
    public void onClosed(String reason) {
        authenticated = false;
        if (pinger != null) {
            pinger.interrupt();
        }
        Map<Integer, ResultHandler> failed;
        Map<Integer, DataHandler> failedData;
        synchronized (this) {
            failed = new HashMap<Integer, ResultHandler>(pending);
            failedData = new HashMap<Integer, DataHandler>(pendingData);
            pending.clear();
            pendingData.clear();
        }
        for (DataHandler h : failedData.values()) {
            h.onData(null);
        }
        for (ResultHandler h : failed.values()) {
            h.onResult(false, "Связь прервалась");
        }
        if (!stopped) {
            callback.onDisconnected(reason, authFailed);
        }
    }
}
