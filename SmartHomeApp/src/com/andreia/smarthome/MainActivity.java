package com.andreia.smarthome;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Handler;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public class MainActivity extends Activity implements EntityAdapter.Controller, CameraLoader.Listener {

    private enum Tab {
        MAIN("Главное"), CONTROL("Управление"), SENSORS("Датчики"), CAMERAS("Камеры"), ALL("Все");

        final String title;

        Tab(String title) {
            this.title = title;
        }
    }

    private static final String[] MAIN_DOMAINS = {
            "alarm_control_panel", "person", "climate", "water_heater", "cover", "light", "lock",
            "fan", "input_boolean", "vacuum", "media_player", "scene", "script",
    };
    private static final String[] CONTROL_DOMAINS = {
            "alarm_control_panel", "climate", "water_heater", "light", "switch", "fan", "cover", "lock",
            "input_boolean", "vacuum", "media_player", "humidifier", "siren", "scene", "script",
            "button", "input_button",
    };
    private static final Map<String, String> DOMAIN_TITLES = new HashMap<String, String>();

    static {
        String[] t = {
                "alarm_control_panel", "Охрана", "person", "Люди", "climate", "Климат",
                "water_heater", "Водонагреватели", "cover", "Шторы и ворота", "light", "Свет",
                "lock", "Замки", "fan", "Вентиляторы", "input_boolean", "Переключатели",
                "vacuum", "Пылесосы", "media_player", "Медиа", "scene", "Сцены", "script", "Скрипты",
                "switch", "Выключатели и розетки", "humidifier", "Увлажнители", "siren", "Сирены",
                "button", "Кнопки", "input_button", "Кнопки", "automation", "Автоматизации",
                "sensor", "Датчики", "binary_sensor", "Состояния", "camera", "Камеры",
                "weather", "Погода", "device_tracker", "Трекеры", "update", "Обновления",
        };
        for (int i = 0; i < t.length; i += 2) {
            DOMAIN_TITLES.put(t[i], t[i + 1]);
        }
    }

    private static final Comparator<Entity> BY_NAME = new Comparator<Entity>() {
        @Override
        public int compare(Entity a, Entity b) {
            return a.name().compareToIgnoreCase(b.name());
        }
    };

    private final Handler ui = new Handler();
    private final Map<String, Entity> entities = new HashMap<String, Entity>();
    private final Map<String, Runnable> pendingTemperature = new HashMap<String, Runnable>();
    private Set<String> shownIds = new HashSet<String>();

    // Registry info, applied to entities as they arrive.
    private final Map<String, String> areaOf = new HashMap<String, String>();
    private final Map<String, String> categoryOf = new HashMap<String, String>();
    private final Set<String> hiddenIds = new HashSet<String>();

    private HaSession session;
    private HaConnection connection;
    private CameraLoader cameras;
    private EntityAdapter adapter;
    private TextView status, weather, empty;
    private EditText search;
    private LinearLayout tabBar;
    private Tab tab = Tab.MAIN;
    private boolean started;
    private boolean haveLiveData;
    private boolean rebuildPending;
    private long retryDelayMs = 2000;
    private int pendingStates = -1;

    private String fullscreenCamera;
    private ImageView fullscreenImage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        session = HaSession.get(this);
        if (!session.loggedIn()) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }
        setContentView(R.layout.activity_main);
        status = (TextView) findViewById(R.id.status);
        weather = (TextView) findViewById(R.id.weather);
        empty = (TextView) findViewById(R.id.empty);
        search = (EditText) findViewById(R.id.search);
        tabBar = (LinearLayout) findViewById(R.id.tabs);
        ListView list = (ListView) findViewById(R.id.list);
        list.setDivider(new android.graphics.drawable.ColorDrawable(0));
        list.setDividerHeight(Math.round(8 * getResources().getDisplayMetrics().density));
        adapter = new EntityAdapter(this, this);
        list.setAdapter(adapter);
        cameras = new CameraLoader(session, this);

        if (savedInstanceState != null) {
            tab = Tab.valueOf(savedInstanceState.getString("tab", Tab.MAIN.name()));
        }
        buildTabs();
        search.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                rebuild();
            }
        });
        findViewById(R.id.menu).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showMainMenu(v);
            }
        });
        setStatus("Подключение…", R.color.text_dim);
        loadCache();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putString("tab", tab.name());
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (session == null || !session.loggedIn()) {
            return;
        }
        started = true;
        connect();
        ui.postDelayed(cameraTicker, 10000);
    }

    @Override
    protected void onStop() {
        super.onStop();
        started = false;
        ui.removeCallbacksAndMessages(null);
        rebuildPending = false;
        flushTemperatures();
        if (connection != null) {
            connection.stop();
            connection = null;
        }
        if (haveLiveData) {
            saveCache();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (cameras != null) {
            cameras.shutdown();
        }
    }

    // ---- connection --------------------------------------------------------

    private final Runnable reconnect = new Runnable() {
        @Override
        public void run() {
            connect();
        }
    };

    private void connect() {
        if (!started || connection != null) {
            return;
        }
        ConnCallback callback = new ConnCallback();
        final HaConnection conn = new HaConnection(session.baseUrl(), callback);
        callback.owner = conn;
        connection = conn;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    conn.start(session.validAccessToken());
                } catch (final HaAuth.AuthException e) {
                    ui.post(new Runnable() {
                        @Override
                        public void run() {
                            if (connection != conn) return;
                            connection = null;
                            if (e.rejected) {
                                Toast.makeText(MainActivity.this, "Сессия истекла, войдите снова",
                                        Toast.LENGTH_LONG).show();
                                logout();
                            } else {
                                disconnected(e.getMessage());
                            }
                        }
                    });
                } catch (final Exception e) {
                    ui.post(new Runnable() {
                        @Override
                        public void run() {
                            if (connection != conn) return;
                            connection = null;
                            disconnected(e.getMessage());
                        }
                    });
                }
            }
        }, "ha-connect").start();
    }

    private void disconnected(String reason) {
        setStatus("Нет связи", R.color.error);
        if (started) {
            ui.removeCallbacks(reconnect);
            ui.postDelayed(reconnect, retryDelayMs);
            retryDelayMs = Math.min(retryDelayMs * 2, 30000);
        }
        if (entities.isEmpty()) {
            empty.setText("Нет связи с домом.\n" + (reason != null ? reason : "") + "\nПовторяю…");
        }
    }

    /** Receives connection events on the socket thread and moves them to the UI thread. */
    private final class ConnCallback implements HaConnection.Callback {
        volatile HaConnection owner;

        private HaConnection self() {
            return owner;
        }

        private void post(final HaConnection expected, final Runnable r) {
            ui.post(new Runnable() {
                @Override
                public void run() {
                    if (connection != null && connection == expected) {
                        r.run();
                    }
                }
            });
        }

        @Override
        public void onConnected() {
            final HaConnection c = self();
            post(c, new Runnable() {
                @Override
                public void run() {
                    retryDelayMs = 2000;
                    setStatus("● Онлайн", R.color.ok);
                }
            });
        }

        @Override
        public void onStates(JSONArray states) {
            // Parse here, off the UI thread.
            final List<Entity> parsed = new ArrayList<Entity>(states.length());
            for (int i = 0; i < states.length(); i++) {
                JSONObject s = states.optJSONObject(i);
                if (s != null) {
                    parsed.add(Entity.fromState(s));
                }
            }
            post(self(), new Runnable() {
                @Override
                public void run() {
                    entities.clear();
                    for (Entity e : parsed) {
                        enrich(e);
                        entities.put(e.id, e);
                    }
                    haveLiveData = true;
                    rebuildNow();
                }
            });
        }

        @Override
        public void onStateChanged(final String entityId, final JSONObject newState) {
            post(self(), new Runnable() {
                @Override
                public void run() {
                    stateChanged(entityId, newState);
                }
            });
        }

        @Override
        public void onRegistry(final JSONObject reg, final JSONArray devices, final JSONArray areas) {
            post(self(), new Runnable() {
                @Override
                public void run() {
                    applyRegistry(reg, devices, areas);
                }
            });
        }

        @Override
        public void onDisconnected(final String reason, final boolean authFailed) {
            final HaConnection c = self();
            post(c, new Runnable() {
                @Override
                public void run() {
                    connection = null;
                    if (authFailed) {
                        session.invalidateAccessToken();
                    }
                    disconnected(reason);
                }
            });
        }
    }

    private void stateChanged(String id, JSONObject newState) {
        Entity e = entities.get(id);
        if (newState == null) {
            if (e != null) {
                entities.remove(id);
                scheduleRebuild();
            }
            return;
        }
        if (e == null) {
            e = Entity.fromState(newState);
            enrich(e);
            entities.put(id, e);
            scheduleRebuild();
            return;
        }
        if (pendingTemperature.containsKey(id)) {
            return; // the user is still adjusting it; keep the local value
        }
        e.update(newState);
        if (shownIds.contains(id) || "weather".equals(e.domain)) {
            scheduleRebuild();
        }
    }

    private void applyRegistry(JSONObject reg, JSONArray devices, JSONArray areas) {
        Map<String, String> areaNames = new HashMap<String, String>();
        if (areas != null) {
            for (int i = 0; i < areas.length(); i++) {
                JSONObject a = areas.optJSONObject(i);
                if (a != null) areaNames.put(a.optString("area_id"), a.optString("name"));
            }
        }
        Map<String, String> deviceArea = new HashMap<String, String>();
        if (devices != null) {
            for (int i = 0; i < devices.length(); i++) {
                JSONObject d = devices.optJSONObject(i);
                if (d != null && !d.isNull("area_id")) deviceArea.put(d.optString("id"), d.optString("area_id"));
            }
        }
        if (reg == null) {
            return;
        }
        JSONObject categories = reg.optJSONObject("entity_categories");
        JSONArray list = reg.optJSONArray("entities");
        if (list == null) {
            return;
        }
        areaOf.clear();
        categoryOf.clear();
        hiddenIds.clear();
        for (int i = 0; i < list.length(); i++) {
            JSONObject r = list.optJSONObject(i);
            if (r == null) continue;
            String id = r.optString("ei");
            String areaId = r.has("ai") ? r.optString("ai") : deviceArea.get(r.optString("di"));
            if (areaId != null && areaNames.containsKey(areaId)) {
                areaOf.put(id, areaNames.get(areaId));
            }
            if (r.has("ec") && categories != null) {
                categoryOf.put(id, categories.optString(String.valueOf(r.optInt("ec")), "config"));
            }
            if (r.optBoolean("hb")) {
                hiddenIds.add(id);
            }
        }
        for (Entity e : entities.values()) {
            enrich(e);
        }
        rebuildNow();
    }

    private void enrich(Entity e) {
        e.area = areaOf.get(e.id);
        e.category = categoryOf.get(e.id);
        e.hidden = hiddenIds.contains(e.id);
    }

    // ---- fast start: last known states ---------------------------------------

    private File cacheFile() {
        return new File(getCacheDir(), "states.json");
    }

    /** Saves the user-facing entities so the next start shows them instantly. */
    private void saveCache() {
        final JSONArray out = new JSONArray();
        List<String> favorites = session.favorites();
        for (Entity e : entities.values()) {
            if (!e.primary() && !favorites.contains(e.id)) continue;
            try {
                JSONObject o = new JSONObject();
                o.put("i", e.id).put("s", e.state).put("a", e.attributes);
                if (e.area != null) o.put("r", e.area);
                out.put(o);
            } catch (JSONException ignored) {
                // Skip this one.
            }
        }
        final File file = cacheFile();
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    FileOutputStream fos = new FileOutputStream(file);
                    fos.write(out.toString().getBytes("UTF-8"));
                    fos.close();
                } catch (Exception ignored) {
                    // A missing cache only makes the next start slower.
                }
            }
        }).start();
    }

    private void loadCache() {
        final File file = cacheFile();
        if (!file.exists()) {
            empty.setText("Загрузка дома…");
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                final List<Entity> list = new ArrayList<Entity>();
                try {
                    JSONArray a = new JSONArray(HaAuth.readAll(new FileInputStream(file)));
                    for (int i = 0; i < a.length(); i++) {
                        JSONObject o = a.getJSONObject(i);
                        Entity e = new Entity(o.getString("i"), o.optString("s"), o.optJSONObject("a"));
                        e.area = o.has("r") ? o.optString("r") : null;
                        list.add(e);
                    }
                } catch (Exception ignored) {
                    // Corrupt cache: wait for live data.
                }
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        if (haveLiveData) return;
                        for (Entity e : list) {
                            entities.put(e.id, e);
                        }
                        rebuildNow();
                    }
                });
            }
        }).start();
    }

    // ---- list contents -------------------------------------------------------

    private void buildTabs() {
        tabBar.removeAllViews();
        float d = getResources().getDisplayMetrics().density;
        for (final Tab t : Tab.values()) {
            TextView chip = new TextView(this);
            chip.setText(t.title);
            chip.setTextSize(15);
            chip.setGravity(Gravity.CENTER);
            chip.setPadding(Math.round(16 * d), 0, Math.round(16 * d), 0);
            chip.setBackgroundResource(t == tab ? R.drawable.chip_active : R.drawable.chip);
            chip.setTextColor(getResources().getColor(t == tab ? android.R.color.white : R.color.text));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, Math.round(38 * d));
            lp.setMarginEnd(Math.round(8 * d));
            chip.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (tab != t) {
                        tab = t;
                        buildTabs();
                        rebuildNow();
                    }
                }
            });
            tabBar.addView(chip, lp);
        }
        search.setVisibility(tab == Tab.ALL ? View.VISIBLE : View.GONE);
    }

    private final Runnable rebuildTask = new Runnable() {
        @Override
        public void run() {
            rebuildPending = false;
            rebuild();
        }
    };

    /** Coalesces bursts of state changes into one list update. */
    private void scheduleRebuild() {
        if (!rebuildPending) {
            rebuildPending = true;
            ui.postDelayed(rebuildTask, 300);
        }
    }

    private void rebuildNow() {
        ui.removeCallbacks(rebuildTask);
        rebuildPending = false;
        rebuild();
    }

    private void rebuild() {
        List<Object> items = new ArrayList<Object>();
        switch (tab) {
            case MAIN:
                buildMain(items);
                break;
            case CONTROL:
                addGrouped(items, CONTROL_DOMAINS, true);
                break;
            case SENSORS:
                buildSensors(items);
                break;
            case CAMERAS:
                for (Entity e : sorted(entities.values())) {
                    if ("camera".equals(e.domain) && e.primary() && e.available()) items.add(e);
                }
                break;
            case ALL:
                buildAll(items);
                break;
        }
        Set<String> ids = new HashSet<String>();
        for (Object o : items) {
            if (o instanceof Entity) ids.add(((Entity) o).id);
        }
        shownIds = ids;
        adapter.setItems(items);
        updateWeather();
        if (items.isEmpty()) {
            empty.setVisibility(View.VISIBLE);
            if (!entities.isEmpty()) {
                empty.setText(tab == Tab.ALL ? "Ничего не найдено" : "Здесь пока пусто");
            }
        } else {
            empty.setVisibility(View.GONE);
        }
    }

    private void buildMain(List<Object> items) {
        List<String> favorites = session.favorites();
        boolean any = false;
        for (String id : favorites) {
            Entity e = entities.get(id);
            if (e != null) {
                if (!any) items.add("Избранное");
                items.add(e);
                any = true;
            }
        }
        if (!any && !entities.isEmpty()) {
            items.add("Удерживайте любой элемент, чтобы закрепить его здесь");
            addGrouped(items, MAIN_DOMAINS, false);
        }
    }

    private void addGrouped(List<Object> items, String[] domains, boolean primaryOnly) {
        Map<String, List<Entity>> byDomain = new LinkedHashMap<String, List<Entity>>();
        for (String d : domains) {
            byDomain.put(d, new ArrayList<Entity>());
        }
        for (Entity e : entities.values()) {
            List<Entity> l = byDomain.get(e.domain);
            if (l != null && e.primary()) {
                l.add(e);
            }
        }
        for (Map.Entry<String, List<Entity>> en : byDomain.entrySet()) {
            List<Entity> l = en.getValue();
            if (l.isEmpty()) continue;
            Collections.sort(l, BY_NAME);
            items.add(title(en.getKey()));
            items.addAll(l);
        }
    }

    private void buildSensors(List<Object> items) {
        Map<String, List<Entity>> groups = new LinkedHashMap<String, List<Entity>>();
        String[] order = {"Безопасность", "Двери и окна", "Движение", "Температура", "Влажность",
                "Электричество", "Батареи", "Состояния", "Прочее"};
        for (String g : order) {
            groups.put(g, new ArrayList<Entity>());
        }
        for (Entity e : entities.values()) {
            if (!e.primary() || !("sensor".equals(e.domain) || "binary_sensor".equals(e.domain))) continue;
            groups.get(sensorGroup(e)).add(e);
        }
        for (Map.Entry<String, List<Entity>> en : groups.entrySet()) {
            if (en.getValue().isEmpty()) continue;
            Collections.sort(en.getValue(), BY_NAME);
            items.add(en.getKey());
            items.addAll(en.getValue());
        }
    }

    private static String sensorGroup(Entity e) {
        String dc = e.deviceClass();
        if ("binary_sensor".equals(e.domain)) {
            switch (dc) {
                case "smoke": case "gas": case "moisture": case "carbon_monoxide": case "safety": case "tamper":
                    return "Безопасность";
                case "door": case "window": case "garage_door": case "opening": case "lock":
                    return "Двери и окна";
                case "motion": case "occupancy": case "presence":
                    return "Движение";
                default:
                    return "Состояния";
            }
        }
        switch (dc) {
            case "temperature": return "Температура";
            case "humidity": case "moisture": return "Влажность";
            case "power": case "energy": case "voltage": case "current": case "frequency": case "power_factor":
                return "Электричество";
            case "battery": return "Батареи";
            default: return "Прочее";
        }
    }

    private void buildAll(List<Object> items) {
        String q = search.getText().toString().trim().toLowerCase(Locale.getDefault());
        Map<String, List<Entity>> byDomain = new HashMap<String, List<Entity>>();
        for (Entity e : entities.values()) {
            if (!q.isEmpty() && !e.name().toLowerCase(Locale.getDefault()).contains(q) && !e.id.contains(q)) {
                continue;
            }
            List<Entity> l = byDomain.get(e.domain);
            if (l == null) {
                l = new ArrayList<Entity>();
                byDomain.put(e.domain, l);
            }
            l.add(e);
        }
        List<String> domains = new ArrayList<String>(byDomain.keySet());
        Collections.sort(domains, new Comparator<String>() {
            @Override
            public int compare(String a, String b) {
                return title(a).compareToIgnoreCase(title(b));
            }
        });
        for (String d : domains) {
            List<Entity> l = byDomain.get(d);
            Collections.sort(l, BY_NAME);
            items.add(title(d) + " · " + l.size());
            items.addAll(l);
        }
    }

    private static String title(String domain) {
        String t = DOMAIN_TITLES.get(domain);
        return t != null ? t : domain;
    }

    private static List<Entity> sorted(java.util.Collection<Entity> c) {
        List<Entity> l = new ArrayList<Entity>(c);
        Collections.sort(l, BY_NAME);
        return l;
    }

    private void updateWeather() {
        Entity best = null;
        for (Entity e : entities.values()) {
            if ("weather".equals(e.domain) && e.available()
                    && (best == null || e.id.contains("yandex"))) {
                best = e;
            }
        }
        if (best == null) {
            weather.setVisibility(View.GONE);
            return;
        }
        String t = Format.number(best.attributes.optString("temperature"));
        weather.setText((t != null ? t + "° · " : "") + Format.stateOf(best));
        weather.setVisibility(View.VISIBLE);
    }

    private void setStatus(String text, int color) {
        status.setText(text);
        status.setTextColor(getResources().getColor(color));
    }

    // ---- controls (EntityAdapter.Controller) --------------------------------

    @Override
    public void call(String domain, String service, Entity e, JSONObject data) {
        HaConnection c = connection;
        if (c == null || !c.isAuthenticated()) {
            Toast.makeText(this, "Нет связи с домом", Toast.LENGTH_SHORT).show();
            rebuild(); // put switches back
            return;
        }
        final String name = e != null ? e.name() : service;
        c.callService(domain, service, e != null ? e.id : null, data, new HaConnection.ResultHandler() {
            @Override
            public void onResult(final boolean success, final String error) {
                if (success) return;
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(MainActivity.this, name + ": " + error, Toast.LENGTH_LONG).show();
                        rebuild();
                    }
                });
            }
        });
    }

    @Override
    public void toggle(Entity e, boolean on) {
        if ("lock".equals(e.domain)) {
            call("lock", on ? "lock" : "unlock", e, null);
        } else {
            call(e.domain, on ? "turn_on" : "turn_off", e, null);
        }
    }

    @Override
    public void stepTemperature(final Entity e, int direction) {
        double current = e.attributes.optDouble("temperature", Double.NaN);
        if (Double.isNaN(current)) return;
        double step = e.attributes.optDouble("target_temp_step", Double.NaN);
        if (Double.isNaN(step) || step < 0.5) step = 0.5;
        double min = e.attributes.optDouble("min_temp", 5);
        double max = e.attributes.optDouble("max_temp", 35);
        double next = Math.round((current + direction * step) / step) * step;
        next = Math.max(min, Math.min(max, next));
        try {
            e.attributes.put("temperature", next);
        } catch (JSONException ignored) {
            return;
        }
        adapter.notifyDataSetChanged();
        // Send once the user stops tapping.
        Runnable old = pendingTemperature.remove(e.id);
        if (old != null) ui.removeCallbacks(old);
        final double value = next;
        Runnable send = new Runnable() {
            @Override
            public void run() {
                pendingTemperature.remove(e.id);
                sendTemperature(e, value);
            }
        };
        pendingTemperature.put(e.id, send);
        ui.postDelayed(send, 700);
    }

    private void sendTemperature(Entity e, double value) {
        try {
            call(e.domain, "set_temperature", e, new JSONObject().put("temperature", value));
        } catch (JSONException ignored) {
            // Cannot happen with a plain number.
        }
    }

    private void flushTemperatures() {
        for (Map.Entry<String, Runnable> en : new HashMap<String, Runnable>(pendingTemperature).entrySet()) {
            ui.removeCallbacks(en.getValue());
            en.getValue().run();
        }
    }

    @Override
    public Bitmap cameraImage(Entity e, int width) {
        cameras.request(e.id, Math.min(width, 960), false);
        return cameras.cached(e.id);
    }

    @Override
    public void onCameraImage(String entityId) {
        if (entityId.equals(fullscreenCamera) && fullscreenImage != null) {
            fullscreenImage.setImageBitmap(cameras.cached(entityId));
        } else if (tab == Tab.CAMERAS) {
            adapter.notifyDataSetChanged();
        }
    }

    private final Runnable cameraTicker = new Runnable() {
        @Override
        public void run() {
            if (tab == Tab.CAMERAS && fullscreenCamera == null) {
                adapter.notifyDataSetChanged(); // rebinding requests fresh snapshots
            }
            ui.postDelayed(this, 10000);
        }
    };

    @Override
    public void openDetails(Entity e) {
        switch (e.kind()) {
            case LIGHT:
                if (e.dimmable() && e.available()) {
                    brightnessDialog(e);
                    return;
                }
                break;
            case CLIMATE:
                climateDialog(e);
                return;
            case COVER:
                if ((e.features() & 4) != 0 && e.available()) {
                    positionDialog(e);
                    return;
                }
                break;
            case ALARM:
                alarmDialog(e);
                return;
            case MEDIA:
                mediaDialog(e);
                return;
            case VACUUM:
                vacuumDialog(e);
                return;
            case CAMERA:
                cameraDialog(e);
                return;
            default:
                break;
        }
        infoDialog(e);
    }

    @Override
    public void openMenu(final Entity e) {
        final List<String> favorites = session.favorites();
        final boolean fav = favorites.contains(e.id);
        String[] items = {fav ? "Убрать из «Главного»" : "Закрепить в «Главном»", "Подробнее"};
        new AlertDialog.Builder(this)
                .setTitle(e.name())
                .setItems(items, new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int which) {
                        if (which == 0) {
                            if (fav) favorites.remove(e.id);
                            else favorites.add(e.id);
                            session.setFavorites(favorites);
                            Toast.makeText(MainActivity.this, fav ? "Убрано" : "Закреплено в «Главном»",
                                    Toast.LENGTH_SHORT).show();
                            rebuild();
                        } else {
                            infoDialog(e);
                        }
                    }
                })
                .show();
    }

    // ---- dialogs -------------------------------------------------------------

    private int dp(float v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private interface SeekDone {
        void onValue(int value);
    }

    private AlertDialog.Builder seekDialog(String title, final String suffix, int value, final SeekDone done) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(24), dp(16), dp(24), dp(8));
        final TextView label = new TextView(this);
        label.setTextSize(28);
        label.setGravity(Gravity.CENTER);
        label.setText(value + suffix);
        SeekBar bar = new SeekBar(this);
        bar.setMax(100);
        bar.setProgress(value);
        bar.setPadding(dp(8), dp(24), dp(8), dp(16));
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar s, int p, boolean fromUser) {
                label.setText(p + suffix);
            }

            @Override
            public void onStartTrackingTouch(SeekBar s) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar s) {
                done.onValue(s.getProgress());
            }
        });
        box.addView(label);
        box.addView(bar);
        return new AlertDialog.Builder(this).setTitle(title).setView(box)
                .setPositiveButton("Готово", null);
    }

    private void brightnessDialog(final Entity e) {
        int pct = e.isOn() ? (int) Math.round(e.attributes.optInt("brightness", 255) / 2.55) : 0;
        seekDialog(e.name(), "%", pct, new SeekDone() {
            @Override
            public void onValue(int value) {
                try {
                    if (value == 0) call("light", "turn_off", e, null);
                    else call("light", "turn_on", e, new JSONObject().put("brightness_pct", value));
                } catch (JSONException ignored) {
                    // Plain number.
                }
            }
        }).setNeutralButton(e.isOn() ? "Выключить" : "Включить", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface d, int w) {
                toggle(e, !e.isOn());
            }
        }).show();
    }

    private void positionDialog(final Entity e) {
        seekDialog(e.name(), "% открыто", e.attributes.optInt("current_position", 0), new SeekDone() {
            @Override
            public void onValue(int value) {
                try {
                    call("cover", "set_cover_position", e, new JSONObject().put("position", value));
                } catch (JSONException ignored) {
                    // Plain number.
                }
            }
        }).show();
    }

    private void climateDialog(final Entity e) {
        final List<String> labels = new ArrayList<String>();
        final List<String[]> actions = new ArrayList<String[]>();
        JSONArray modes = e.attributes.optJSONArray("hvac_modes");
        if (modes != null) {
            for (int i = 0; i < modes.length(); i++) {
                String m = modes.optString(i);
                labels.add((m.equals(e.state) ? "✓ " : "    ") + "Режим: " + Format.state(m));
                actions.add(new String[]{"set_hvac_mode", "hvac_mode", m});
            }
        }
        JSONArray presets = e.attributes.optJSONArray("preset_modes");
        if (presets != null) {
            String current = e.attributes.optString("preset_mode");
            for (int i = 0; i < presets.length(); i++) {
                String p = presets.optString(i);
                labels.add((p.equals(current) ? "✓ " : "    ") + "Пресет: " + Format.preset(p));
                actions.add(new String[]{"set_preset_mode", "preset_mode", p});
            }
        }
        if (e.attributes.has("temperature") && !e.attributes.isNull("temperature")) {
            labels.add("    Задать температуру…");
            actions.add(null);
        }
        new AlertDialog.Builder(this)
                .setTitle(e.name() + "\n" + Format.climate(e))
                .setItems(labels.toArray(new String[0]), new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int which) {
                        String[] a = actions.get(which);
                        if (a == null) {
                            temperatureInput(e);
                            return;
                        }
                        try {
                            call(e.domain, a[0], e, new JSONObject().put(a[1], a[2]));
                        } catch (JSONException ignored) {
                            // Plain strings.
                        }
                    }
                })
                .show();
    }

    private void temperatureInput(final Entity e) {
        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        input.setText(Format.number(e.attributes.optDouble("temperature")).replace(',', '.'));
        input.setSelectAllOnFocus(true);
        FrameLayout box = new FrameLayout(this);
        box.setPadding(dp(24), dp(8), dp(24), 0);
        box.addView(input);
        new AlertDialog.Builder(this)
                .setTitle("Температура, °")
                .setView(box)
                .setPositiveButton("Установить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        try {
                            double v = Double.parseDouble(input.getText().toString().replace(',', '.'));
                            sendTemperature(e, v);
                        } catch (NumberFormatException ex) {
                            Toast.makeText(MainActivity.this, "Неверное число", Toast.LENGTH_SHORT).show();
                        }
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void alarmDialog(final Entity e) {
        final List<String> labels = new ArrayList<String>();
        final List<String> services = new ArrayList<String>();
        int f = e.features();
        if (!"disarmed".equals(e.state)) {
            labels.add("Снять с охраны");
            services.add("alarm_disarm");
        }
        if ((f & 2) != 0 && !"armed_away".equals(e.state)) {
            labels.add("Поставить на охрану (никого нет)");
            services.add("alarm_arm_away");
        }
        if ((f & 1) != 0 && !"armed_home".equals(e.state)) {
            labels.add("Охрана «дома»");
            services.add("alarm_arm_home");
        }
        if ((f & 4) != 0 && !"armed_night".equals(e.state)) {
            labels.add("Ночная охрана");
            services.add("alarm_arm_night");
        }
        if ((f & 32) != 0 && !"armed_vacation".equals(e.state)) {
            labels.add("Охрана «отпуск»");
            services.add("alarm_arm_vacation");
        }
        new AlertDialog.Builder(this)
                .setTitle(e.name() + ": " + Format.state(e.state))
                .setItems(labels.toArray(new String[0]), new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int which) {
                        final String service = services.get(which);
                        boolean hasCode = !e.attributes.isNull("code_format") && e.attributes.has("code_format");
                        boolean needsCode = hasCode && ("alarm_disarm".equals(service)
                                || e.attributes.optBoolean("code_arm_required", true));
                        if (!needsCode) {
                            call(e.domain, service, e, null);
                            return;
                        }
                        final EditText code = new EditText(MainActivity.this);
                        code.setInputType("number".equals(e.attributes.optString("code_format"))
                                ? InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD
                                : InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
                        FrameLayout box = new FrameLayout(MainActivity.this);
                        box.setPadding(dp(24), dp(8), dp(24), 0);
                        box.addView(code);
                        new AlertDialog.Builder(MainActivity.this)
                                .setTitle("Код охраны")
                                .setView(box)
                                .setPositiveButton("OK", new DialogInterface.OnClickListener() {
                                    @Override
                                    public void onClick(DialogInterface d2, int w) {
                                        try {
                                            call(e.domain, service, e,
                                                    new JSONObject().put("code", code.getText().toString()));
                                        } catch (JSONException ignored) {
                                            // Plain string.
                                        }
                                    }
                                })
                                .setNegativeButton("Отмена", null)
                                .show();
                    }
                })
                .show();
    }

    private void actionDialog(final Entity e, String title, final String[] labels, final String[] services) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setItems(labels, new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int which) {
                        call(e.domain, services[which], e, null);
                    }
                })
                .show();
    }

    private void mediaDialog(Entity e) {
        actionDialog(e, e.name() + ": " + Format.state(e.state),
                new String[]{"Играть / пауза", "Следующий", "Предыдущий", "Громче", "Тише", "Выключить"},
                new String[]{"media_play_pause", "media_next_track", "media_previous_track",
                        "volume_up", "volume_down", "turn_off"});
    }

    private void vacuumDialog(Entity e) {
        actionDialog(e, e.name() + ": " + Format.state(e.state),
                new String[]{"Начать уборку", "Пауза", "Остановить", "На базу", "Найти пылесос"},
                new String[]{"start", "pause", "stop", "return_to_base", "locate"});
    }

    private void cameraDialog(final Entity e) {
        final ImageView image = new ImageView(this);
        image.setBackgroundColor(0xFF000000);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        image.setImageBitmap(cameras.cached(e.id));
        Dialog dialog = new Dialog(this, android.R.style.Theme_Black_NoTitleBar_Fullscreen);
        dialog.setContentView(image);
        fullscreenCamera = e.id;
        fullscreenImage = image;
        final int width = getResources().getDisplayMetrics().widthPixels;
        final Runnable refresh = new Runnable() {
            @Override
            public void run() {
                if (e.id.equals(fullscreenCamera)) {
                    cameras.request(e.id, Math.max(width, 1280), true);
                    ui.postDelayed(this, 2000);
                }
            }
        };
        dialog.setOnDismissListener(new DialogInterface.OnDismissListener() {
            @Override
            public void onDismiss(DialogInterface d) {
                fullscreenCamera = null;
                fullscreenImage = null;
                ui.removeCallbacks(refresh);
            }
        });
        image.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                fullscreenCamera = null;
                ((Dialog) v.getTag()).dismiss();
            }
        });
        image.setTag(dialog);
        dialog.show();
        refresh.run();
    }

    private void infoDialog(Entity e) {
        StringBuilder sb = new StringBuilder();
        sb.append("Состояние: ").append(Format.stateOf(e)).append('\n');
        if (e.area != null) sb.append("Комната: ").append(e.area).append('\n');
        sb.append("ID: ").append(e.id).append("\n\n");
        Iterator<String> keys = e.attributes.keys();
        List<String> names = new ArrayList<String>();
        while (keys.hasNext()) names.add(keys.next());
        Collections.sort(names);
        for (String k : names) {
            if (k.equals("friendly_name") || k.equals("entity_picture") || k.equals("access_token")) continue;
            String v = String.valueOf(e.attributes.opt(k));
            if (v.length() > 200) v = v.substring(0, 200) + "…";
            sb.append(k).append(": ").append(v).append('\n');
        }
        AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle(e.name())
                .setMessage(sb.toString().trim())
                .setPositiveButton("Закрыть", null);
        if (e.kind() == Entity.Kind.ACTION) {
            final Entity entity = e;
            b.setNeutralButton("Запустить", new DialogInterface.OnClickListener() {
                @Override
                public void onClick(DialogInterface d, int w) {
                    boolean press = "button".equals(entity.domain) || "input_button".equals(entity.domain);
                    call(entity.domain, press ? "press" : "turn_on", entity, null);
                }
            });
        }
        b.show();
    }

    private void showMainMenu(View anchor) {
        String[] items = {"Обновить", "Выйти (" + session.baseUrl().replaceFirst("^https?://", "") + ")"};
        new AlertDialog.Builder(this)
                .setItems(items, new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        if (which == 0) {
                            if (connection != null) {
                                connection.stop();
                                connection = null;
                            }
                            setStatus("Подключение…", R.color.text_dim);
                            retryDelayMs = 2000;
                            connect();
                        } else {
                            new AlertDialog.Builder(MainActivity.this)
                                    .setMessage("Выйти из аккаунта?")
                                    .setPositiveButton("Выйти", new DialogInterface.OnClickListener() {
                                        @Override
                                        public void onClick(DialogInterface d, int w) {
                                            logout();
                                        }
                                    })
                                    .setNegativeButton("Отмена", null)
                                    .show();
                        }
                    }
                })
                .show();
    }

    private void logout() {
        started = false;
        if (connection != null) {
            connection.stop();
            connection = null;
        }
        session.logout();
        cacheFile().delete();
        startActivity(new Intent(this, LoginActivity.class));
        finish();
    }
}
