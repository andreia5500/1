package com.andreia.smarthome;

import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** "Главная": alerts, alarm, temperatures, power and safety sensors, then pinned items. */
final class HomeScreen {

    interface Host {
        void alarmAction(Entity alarm, String service);

        void openDetails(Entity e);

        void showGroup(String title, List<Entity> sensors);

        void dismissAlert(Entity e);

        void pickEntity(String prefKey, String title, List<Entity> candidates);

        void openAllDevices();

        EntityAdapter favoritesAdapter();

        void vkCommand(String command);

        void stepTemperature(Entity e, int direction);
    }

    /** One line of the event log. */
    static final class Event {
        final long when;
        final String entityId;
        final String state;

        Event(long when, String entityId, String state) {
            this.when = when;
            this.entityId = entityId;
            this.state = state;
        }
    }

    /** What the screen shows besides entity states. */
    static final class Model {
        Map<String, Entity> entities;
        String location;
        boolean online;
        long dataTime;
        List<String> favorites;
        Set<String> dismissed; // "entityId@lastChanged"
        String insideId;
        String powerId;
        double[] powerHistory;
        List<Event> events;
    }

    private static final String[] DOOR = {"door", "window", "garage_door", "opening"};
    private static final String[] LEAK = {"moisture"};
    private static final String[] SMOKE = {"smoke", "gas", "carbon_monoxide"};

    private final Ui ui;
    private final LinearLayout root;
    private final Host host;

    HomeScreen(Ui ui, LinearLayout root, Host host) {
        this.ui = ui;
        this.root = root;
        this.host = host;
    }

    private Map<String, Entity> lastEntities;

    void render(Model m) {
        lastEntities = m.entities;
        root.removeAllViews();
        Collection<Entity> all = m.entities.values();
        List<Entity> alerts = alerts(m);
        Entity alarm = first(all, "alarm_control_panel");
        boolean attention = !alerts.isEmpty() || (alarm != null && "triggered".equals(alarm.state));

        String when = new SimpleDateFormat("d MMMM, HH:mm", new Locale("ru")).format(new Date());
        LinearLayout header = ui.header(m.location + " · " + when, attention ? "Требует внимания" : "Всё спокойно");
        if (!m.online) {
            String since = m.dataTime > 0
                    ? " · данные на " + new SimpleDateFormat("HH:mm", Locale.US).format(new Date(m.dataTime)) : "";
            TextView off = ui.text("Нет связи с домом" + since, 13, R.color.warn);
            header.addView(off, ui.margins(ui.wrap(), 0, 4, 0, 0));
        }
        root.addView(header);

        if (!m.online) {
            add(vkCard(true)); // no internet to the house: VK is the way in
        }
        if (m.entities.isEmpty()) {
            TextView t = ui.text(m.online ? "Загрузка дома…" : "Подключение…", 15, R.color.text_dim);
            t.setGravity(Gravity.CENTER);
            t.setPadding(0, ui.dp(48), 0, 0);
            root.addView(t, ui.matchWidth());
            return;
        }

        for (Entity a : alerts) {
            add(alertCard(a));
        }
        if (alarm != null) {
            add(alarmCard(alarm, all));
        }
        View temps = temperatureCard(m);
        if (temps != null) add(temps);
        View power = powerCard(m, alerts.isEmpty());
        if (power != null) add(power);
        View ups = upsCard(m.entities);
        if (ups != null) add(ups);
        View sensors = sensorsCard(all);
        if (sensors != null) add(sensors);
        View heating = heatingCard(all);
        if (heating != null) add(heating);
        View log = eventsCard(m);
        if (log != null) add(log);
        addFavorites(m);
        if (m.online) {
            add(vkCard(false));
        }
    }

    // ---- commands through VK ----------------------------------------------------------

    private View vkCard(boolean offline) {
        LinearLayout card = ui.card(R.drawable.card, 16, 18);
        card.addView(ui.kicker("Команды через ВК"));
        TextView sub = ui.text(offline
                ? "Нет связи с домом. Команда уйдёт в группу ВК — вставьте её в чат и отправьте."
                : "Если интернет до дома заблокирован, а ВК работает.", 13, R.color.text_dim);
        sub.setLineSpacing(0, 1.15f);
        card.addView(sub, ui.margins(ui.matchWidth(), 0, 6, 0, 4));
        String[][] cmds = VkCommands.COMMANDS;
        for (int i = 0; i < cmds.length; i += 2) {
            LinearLayout row = ui.horizontal();
            row.addView(vkButton(cmds[i], i == 0), ui.weight(1, 44));
            row.addView(ui.spacer(9));
            if (i + 1 < cmds.length) {
                row.addView(vkButton(cmds[i + 1], false), ui.weight(1, 44));
            } else {
                row.addView(new View(ui.context), ui.weight(1, 44));
            }
            card.addView(row, ui.margins(ui.matchWidth(), 0, 9, 0, 0));
        }
        return card;
    }

    private View vkButton(final String[] cmd, boolean primary) {
        TextView b = ui.button(cmd[1], primary ? R.drawable.btn_accent : R.drawable.btn_outline,
                primary ? R.color.on_dark : R.color.text, 44);
        b.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 13.5f);
        b.setPadding(ui.dp(8), 0, ui.dp(8), 0);
        b.setContentDescription(cmd[1] + ", команда /" + cmd[0]);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.vkCommand(cmd[0]);
            }
        });
        return b;
    }

    private void add(View v) {
        root.addView(v, ui.margins(ui.matchWidth(), 18, 0, 18, 12));
    }

    // ---- alerts ----------------------------------------------------------------

    private List<Entity> alerts(Model m) {
        List<Entity> list = new ArrayList<Entity>();
        for (Entity e : m.entities.values()) {
            boolean firing = ("binary_sensor".equals(e.domain) && "on".equals(e.state)
                    && (has(LEAK, e.deviceClass()) || has(SMOKE, e.deviceClass())))
                    || ("alarm_control_panel".equals(e.domain) && "triggered".equals(e.state))
                    || onBattery(e);
            if (firing && e.primary() && !m.dismissed.contains(alertKey(e))) {
                list.add(e);
            }
        }
        Collections.sort(list, new Comparator<Entity>() {
            @Override
            public int compare(Entity a, Entity b) {
                return Long.compare(b.lastChanged, a.lastChanged);
            }
        });
        return list;
    }

    static String alertKey(Entity e) {
        return e.id + "@" + e.lastChanged;
    }

    private View alertCard(final Entity e) {
        LinearLayout card = ui.horizontal();
        card.setGravity(Gravity.TOP);
        card.setBackgroundResource(R.drawable.card_alert);
        card.setPadding(ui.dp(18), ui.dp(18), ui.dp(18), ui.dp(18));

        LinearLayout box = ui.horizontal();
        box.setGravity(Gravity.CENTER);
        box.setBackgroundResource(R.drawable.icon_box_alarm);
        box.addView(ui.icon(R.drawable.ic_warning, R.color.on_dark, 19));
        card.addView(box, new LinearLayout.LayoutParams(ui.dp(38), ui.dp(38)));

        LinearLayout body = ui.vertical();
        String kind = "alarm_control_panel".equals(e.domain) ? "Тревога охраны"
                : onBattery(e) ? "Нет электричества"
                : has(LEAK, e.deviceClass()) ? "Протечка" : "Дым";
        String place = "alarm_control_panel".equals(e.domain) ? e.name()
                : onBattery(e) ? "дом на ИБП" : shortName(e);
        TextView title = ui.text(kind + " — " + place, 16.5f, R.color.alarm);
        title.setTypeface(Ui.MEDIUM);
        body.addView(title);
        String time = e.lastChanged > 0
                ? "Сработал в " + new SimpleDateFormat("HH:mm", Locale.US).format(new Date(e.lastChanged)) + ". "
                : "";
        String detail = onBattery(e) ? upsSummary(lastEntities, upsPrefix(e)) : "Датчик: " + e.name() + ".";
        TextView desc = ui.text((onBattery(e) && e.lastChanged > 0
                ? "С " + new SimpleDateFormat("HH:mm", Locale.US).format(new Date(e.lastChanged)) + ". " : time)
                + detail, 13.5f, R.color.text_body);
        desc.setLineSpacing(0, 1.2f);
        body.addView(desc, ui.margins(ui.matchWidth(), 0, 4, 0, 0));

        LinearLayout buttons = ui.horizontal();
        TextView more = ui.button("Подробнее", R.drawable.btn_danger, R.color.on_dark, 44);
        TextView hide = ui.button("Скрыть", R.drawable.btn_outline, R.color.text, 44);
        more.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openDetails(e);
            }
        });
        hide.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.dismissAlert(e);
            }
        });
        buttons.addView(more, ui.margins(ui.wrap(), 0, 0, 9, 0));
        buttons.addView(hide, ui.wrap());
        body.addView(buttons, ui.margins(ui.matchWidth(), 0, 14, 0, 0));
        card.addView(body, ui.margins(ui.weight(1), 14, 0, 0, 0));
        return card;
    }

    // ---- alarm -------------------------------------------------------------------

    private View alarmCard(final Entity alarm, Collection<Entity> all) {
        String s = alarm.state;
        boolean armed = s.startsWith("armed") || "triggered".equals(s) || "pending".equals(s)
                || "arming".equals(s);
        boolean dark = armed;
        LinearLayout card = ui.card(dark ? R.drawable.card_dark : R.drawable.card, 18, 18);
        int dim = dark ? R.color.on_dark_dim : R.color.text_dim;
        int ink = dark ? R.color.on_dark : R.color.text;

        LinearLayout top = ui.horizontal();
        TextView k = ui.kicker("Охрана");
        k.setTextColor(ui.color(dim));
        top.addView(k, ui.weight(1));
        View dot = new View(ui.context);
        dot.setBackgroundResource(R.drawable.dot);
        dot.getBackground().mutate().setTint(ui.color(dark ? R.color.on_dark : R.color.ink));
        top.addView(dot, ui.margins(new LinearLayout.LayoutParams(ui.dp(7), ui.dp(7)), 0, 0, 7, 0));
        String since = alarm.lastChanged > 0
                ? "с " + new SimpleDateFormat("HH:mm", Locale.US).format(new Date(alarm.lastChanged)) : "";
        top.addView(ui.text(armed ? since : (alarm.available() ? "Готово к постановке" : "Нет связи"),
                12.5f, dim));
        card.addView(top);

        String title;
        switch (s) {
            case "armed_away": title = "Под охраной · ухожу"; break;
            case "armed_home": title = "Под охраной · я дома"; break;
            case "armed_night": title = "Под охраной · ночь"; break;
            case "triggered": title = "ТРЕВОГА"; break;
            default: title = Format.state(s);
        }
        TextView t = ui.title(title, 23);
        t.setTextColor(ui.color("triggered".equals(s) ? R.color.on_dark : ink));
        card.addView(t, ui.margins(ui.matchWidth(), 0, 12, 0, 0));

        int[] counts = safetyCounts(all);
        String sub = counts[1] == 0
                ? "Все зоны в норме · " + counts[0] + " " + plural(counts[0], "датчик", "датчика", "датчиков") + " на связи"
                : "Не в норме: " + counts[1] + " из " + counts[0];
        card.addView(ui.text(sub, 13, dim), ui.margins(ui.matchWidth(), 0, 4, 0, 0));

        LinearLayout buttons = ui.horizontal();
        int f = alarm.features();
        if (armed) {
            buttons.addView(alarmButton(alarm, "Снять с охраны", "alarm_disarm", R.drawable.btn_outline_dark,
                    R.color.on_dark), ui.weight(1, 46));
        } else {
            boolean home = (f & 1) != 0, away = (f & 2) != 0 || f == 0;
            if (home) {
                buttons.addView(alarmButton(alarm, "Я дома", "alarm_arm_home", R.drawable.btn_outline,
                        R.color.text), ui.weight(1, 46));
            }
            if (home && away) buttons.addView(ui.spacer(9));
            if (away) {
                buttons.addView(alarmButton(alarm, "Ухожу", "alarm_arm_away", R.drawable.btn_accent,
                        R.color.on_dark), ui.weight(1, 46));
            }
        }
        if (alarm.available()) {
            card.addView(buttons, ui.margins(ui.matchWidth(), 0, 15, 0, 0));
        }
        return card;
    }

    private TextView alarmButton(final Entity alarm, String label, final String service, int bg, int color) {
        TextView b = ui.button(label, bg, color, 46);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.alarmAction(alarm, service);
            }
        });
        return b;
    }

    // ---- temperatures ----------------------------------------------------------------

    private View temperatureCard(final Model m) {
        Entity weather = null;
        for (Entity e : m.entities.values()) {
            if ("weather".equals(e.domain) && e.available() && (weather == null || e.id.contains("yandex"))) {
                weather = e;
            }
        }
        final List<Entity> candidates = temperatureCandidates(m.entities.values());
        Entity inside = m.insideId != null ? m.entities.get(m.insideId) : null;
        if (inside == null) {
            for (Entity e : candidates) {
                if ("climate".equals(e.domain) && (inside == null || e.name().toLowerCase().contains("комнат"))) {
                    inside = e;
                }
            }
            if (inside == null && !candidates.isEmpty()) inside = candidates.get(0);
        }
        if (weather == null && inside == null) {
            return null;
        }
        LinearLayout card = ui.horizontal();
        card.setGravity(Gravity.NO_GRAVITY);
        card.setBackgroundResource(R.drawable.card);
        card.setPadding(ui.dp(18), ui.dp(16), ui.dp(18), ui.dp(16));

        if (weather != null) {
            String t = Format.number(weather.attributes.optString("temperature"));
            String feels = Format.number(weather.attributes.optString("apparent_temperature"));
            card.addView(tempColumn("На улице", t != null ? signed(t) + "°" : "—",
                    feels != null ? "ощущается " + signed(feels) : Format.stateOf(weather).toLowerCase()),
                    ui.weight(1));
        }
        if (weather != null && inside != null) {
            View line = ui.divider();
            card.addView(line, ui.margins(new LinearLayout.LayoutParams(ui.dp(1),
                    ViewGroup.LayoutParams.MATCH_PARENT), 16, 2, 16, 2));
        }
        if (inside != null) {
            StringBuilder others = new StringBuilder();
            for (Entity e : candidates) {
                if (e == inside || !"climate".equals(e.domain) || others.length() > 24) continue;
                String v = Format.number(e.attributes.optString("current_temperature"));
                if (v == null) continue;
                if (others.length() > 0) others.append(" · ");
                others.append(lastWord(e.name())).append(' ').append(signed(v));
            }
            String value = Format.number(temperatureOf(inside));
            card.addView(tempColumn("В доме", value != null ? signed(value) + "°" : "—", others.toString()),
                    ui.weight(1));
        }
        card.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                host.pickEntity("inside_temp", "Что показывать «В доме»", candidates);
                return true;
            }
        });
        return card;
    }

    private View tempColumn(String label, String value, String sub) {
        LinearLayout col = ui.vertical();
        col.addView(ui.kicker(label));
        col.addView(ui.number(value, 36), ui.margins(ui.wrap(), 0, 6, 0, 0));
        if (sub != null && !sub.isEmpty()) {
            TextView s = ui.text(sub, 12.5f, R.color.text_dim);
            s.setSingleLine(true);
            s.setEllipsize(android.text.TextUtils.TruncateAt.END);
            col.addView(s, ui.margins(ui.wrap(), 0, 4, 0, 0));
        }
        return col;
    }

    static List<Entity> temperatureCandidates(Collection<Entity> all) {
        List<Entity> list = new ArrayList<Entity>();
        for (Entity e : all) {
            if (!e.primary() || !e.available()) continue;
            if (("climate".equals(e.domain) && e.attributes.has("current_temperature"))
                    || ("sensor".equals(e.domain) && "temperature".equals(e.deviceClass()))) {
                list.add(e);
            }
        }
        Collections.sort(list, new Comparator<Entity>() {
            @Override
            public int compare(Entity a, Entity b) {
                if (!a.domain.equals(b.domain)) return a.domain.compareTo(b.domain); // climate first
                return a.name().compareToIgnoreCase(b.name());
            }
        });
        return list;
    }

    private static String temperatureOf(Entity e) {
        return "climate".equals(e.domain) ? e.attributes.optString("current_temperature") : e.state;
    }

    // ---- power -------------------------------------------------------------------

    static Entity powerSensor(Map<String, Entity> entities, String chosen) {
        Entity c = chosen != null ? entities.get(chosen) : null;
        if (c != null) return c;
        Entity best = null;
        int bestScore = -1;
        for (Entity e : entities.values()) {
            if (!"sensor".equals(e.domain) || !"power".equals(e.deviceClass()) || !e.primary()) continue;
            String n = e.name().toLowerCase();
            int score = n.contains("общ") || n.contains("ввод") || n.contains("сеть") ? 3
                    : n.contains("электричеств") ? 2 : e.available() ? 1 : 0;
            // A meter that has not changed for an hour is stuck (e.g. its integration dropped).
            if (e.available() && System.currentTimeMillis() - e.lastChanged < 3600000L) score += 10;
            if (score > bestScore) {
                best = e;
                bestScore = score;
            }
        }
        return best;
    }

    static double watts(Entity e) {
        try {
            double v = Double.parseDouble(e.state);
            return "kW".equalsIgnoreCase(e.attributes.optString("unit_of_measurement")) ? v * 1000 : v;
        } catch (NumberFormatException ex) {
            return Double.NaN;
        }
    }

    private View powerCard(final Model m, boolean big) {
        final Entity p = powerSensor(m.entities, m.powerId);
        if (p == null) return null;
        LinearLayout card = ui.card(R.drawable.card, 16, 18);
        double w = watts(p);
        String value = Double.isNaN(w) ? "—" : String.format(new Locale("ru"), "%,d", Math.round(w))
                .replace(' ', ' ');

        LinearLayout top = ui.horizontal();
        top.addView(ui.kicker("Мощность сети"), ui.weight(1));
        if (big) top.addView(ui.text("сейчас", 12.5f, R.color.text_dim));
        if (big) {
            card.addView(top);
            LinearLayout row = ui.horizontal();
            row.setGravity(Gravity.BOTTOM);
            row.addView(ui.number(value, 40));
            row.addView(ui.text("Вт", 15, R.color.text_dim), ui.margins(ui.wrap(), 7, 0, 0, 3));
            card.addView(row, ui.margins(ui.matchWidth(), 0, 8, 0, 0));
            if (m.powerHistory != null && m.powerHistory.length > 1) {
                SparklineView chart = new SparklineView(ui.context);
                chart.setValues(m.powerHistory, true);
                card.addView(chart, ui.margins(new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ui.dp(46)), 0, 10, 0, 0));
            }
            String footer = powerFooter(m.entities, p);
            if (!footer.isEmpty()) {
                card.addView(ui.divider(), ui.margins(new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ui.dp(1)), 0, 8, 0, 0));
                card.addView(ui.text(footer, 12.5f, R.color.text_dim), ui.margins(ui.matchWidth(), 0, 11, 0, 0));
            }
        } else {
            // Compact variant while alerts are on screen.
            LinearLayout row = ui.horizontal();
            LinearLayout left = ui.vertical();
            left.addView(top);
            LinearLayout num = ui.horizontal();
            num.setGravity(Gravity.BOTTOM);
            num.addView(ui.number(value, 28));
            num.addView(ui.text("Вт", 13.5f, R.color.text_dim), ui.margins(ui.wrap(), 6, 0, 0, 2));
            left.addView(num, ui.margins(ui.wrap(), 0, 6, 0, 0));
            row.addView(left, ui.weight(1));
            if (m.powerHistory != null && m.powerHistory.length > 1) {
                SparklineView chart = new SparklineView(ui.context);
                chart.setValues(m.powerHistory, false);
                row.addView(chart, new LinearLayout.LayoutParams(ui.dp(104), ui.dp(38)));
            }
            card.addView(row);
        }
        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openDetails(p);
            }
        });
        card.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                List<Entity> list = new ArrayList<Entity>();
                for (Entity e : m.entities.values()) {
                    if ("sensor".equals(e.domain) && "power".equals(e.deviceClass()) && e.primary()) list.add(e);
                }
                Collections.sort(list, new Comparator<Entity>() {
                    @Override
                    public int compare(Entity a, Entity b) {
                        return a.name().compareToIgnoreCase(b.name());
                    }
                });
                host.pickEntity("power_sensor", "Датчик мощности", list);
                return true;
            }
        });
        return card;
    }

    /** "10,7 А · 225 В" from sibling sensors of the same meter. */
    private static String powerFooter(Map<String, Entity> entities, Entity p) {
        String base = p.id.endsWith("_power") ? p.id.substring(0, p.id.length() - 6) : null;
        if (base == null) return "";
        StringBuilder sb = new StringBuilder();
        Entity cur = entities.get(base + "_current");
        Entity volt = entities.get(base + "_voltage");
        if (cur != null && Format.number(cur.state) != null) sb.append(Format.number(cur.state)).append(" А");
        if (volt != null && Format.number(volt.state) != null) {
            if (sb.length() > 0) sb.append(" · ");
            sb.append(Math.round(Double.parseDouble(volt.state))).append(" В");
        }
        return sb.toString();
    }

    // ---- safety sensors ----------------------------------------------------------------

    private static List<Entity> group(Collection<Entity> all, String[] classes) {
        List<Entity> list = new ArrayList<Entity>();
        for (Entity e : all) {
            if ("binary_sensor".equals(e.domain) && e.primary() && has(classes, e.deviceClass())) list.add(e);
        }
        Collections.sort(list, new Comparator<Entity>() {
            @Override
            public int compare(Entity a, Entity b) {
                return a.name().compareToIgnoreCase(b.name());
            }
        });
        return list;
    }

    /** {sensors online, sensors not in normal state} over doors, leaks and smoke. */
    private static int[] safetyCounts(Collection<Entity> all) {
        int online = 0, bad = 0;
        for (String[] g : new String[][]{DOOR, LEAK, SMOKE}) {
            for (Entity e : group(all, g)) {
                if (e.available()) online++;
                if ("on".equals(e.state)) bad++;
            }
        }
        return new int[]{online, bad};
    }

    private View sensorsCard(Collection<Entity> all) {
        List<Entity> doors = group(all, DOOR), leaks = group(all, LEAK), smoke = group(all, SMOKE);
        if (doors.isEmpty() && leaks.isEmpty() && smoke.isEmpty()) return null;
        LinearLayout card = ui.card(R.drawable.card, 6, 18);
        List<View> rows = new ArrayList<View>();
        if (!doors.isEmpty()) rows.add(sensorRow(R.drawable.ic_door, "Двери", doors, "Закрыты", "открыта", false));
        if (!leaks.isEmpty()) rows.add(sensorRow(R.drawable.ic_drop, "Протечка", leaks, "Сухо", "Влага", true));
        if (!smoke.isEmpty()) rows.add(sensorRow(R.drawable.ic_flame, "Дым и CO", smoke, "Норма", "Дым", true));
        for (int i = 0; i < rows.size(); i++) {
            if (i > 0) card.addView(ui.divider(), new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ui.dp(1)));
            card.addView(rows.get(i));
        }
        return card;
    }

    private View sensorRow(int icon, final String title, final List<Entity> sensors, String okText,
                           String badText, boolean danger) {
        List<Entity> on = new ArrayList<Entity>();
        int online = 0;
        for (Entity e : sensors) {
            if ("on".equals(e.state)) on.add(e);
            if (e.available()) online++;
        }
        int color = on.isEmpty() ? R.color.text : danger ? R.color.alarm : R.color.text;
        LinearLayout row = ui.horizontal();
        row.setPadding(0, ui.dp(13), 0, ui.dp(13));
        row.setMinimumHeight(ui.dp(48));
        row.addView(ui.icon(icon, on.isEmpty() || !danger ? R.color.ink : R.color.alarm, 19));
        TextView name = ui.text(title, 14.5f, color);
        name.setTypeface(Ui.MEDIUM);
        row.addView(name, ui.margins(ui.weight(1), 13, 0, 8, 0));

        String status;
        int statusColor;
        if (on.isEmpty()) {
            status = online == 0 ? "Нет связи" : okText + " · " + online;
            statusColor = R.color.text_dim;
        } else if (on.size() == 1) {
            String place = shortName(on.get(0));
            status = danger ? badText + " · " + place.toLowerCase() : capitalize(place) + " " + badText;
            statusColor = danger ? R.color.alarm : R.color.warn;
        } else {
            status = (danger ? badText : "Открыто") + ": " + on.size();
            statusColor = danger ? R.color.alarm : R.color.warn;
        }
        TextView s = ui.text(status, 13.5f, statusColor);
        if (!on.isEmpty()) s.setTypeface(Ui.MEDIUM);
        s.setSingleLine(true);
        s.setEllipsize(android.text.TextUtils.TruncateAt.END);
        row.addView(s, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        row.setBackgroundResource(R.drawable.nav_item);
        row.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.showGroup(title, sensors);
            }
        });
        return row;
    }

    // ---- pinned ---------------------------------------------------------------------

    private void addFavorites(Model m) {
        List<Object> items = new ArrayList<Object>();
        for (String id : m.favorites) {
            Entity e = m.entities.get(id);
            if (e != null) items.add(e);
        }
        if (!items.isEmpty()) {
            TextView k = ui.kicker("Избранное");
            root.addView(k, ui.margins(ui.matchWidth(), 26, 10, 22, 8));
            EntityAdapter adapter = host.favoritesAdapter();
            adapter.setItems(items);
            for (int i = 0; i < items.size(); i++) {
                View row = adapter.getView(i, null, root);
                root.addView(row, ui.margins(ui.matchWidth(), 18, 0, 18, 8));
            }
        }
        LinearLayout link = ui.horizontal();
        link.setBackgroundResource(R.drawable.card);
        link.setPadding(ui.dp(18), ui.dp(15), ui.dp(14), ui.dp(15));
        TextView t = ui.text(items.isEmpty()
                ? "Все устройства · удерживайте любое, чтобы закрепить здесь" : "Все устройства", 14.5f, R.color.text);
        t.setTypeface(Ui.MEDIUM);
        link.addView(t, ui.weight(1));
        link.addView(ui.icon(R.drawable.ic_chevron, R.color.text_nav, 16));
        link.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openAllDevices();
            }
        });
        root.addView(link, ui.margins(ui.matchWidth(), 18, items.isEmpty() ? 0 : 4, 18, 12));
    }

    // ---- UPS (Network UPS Tools) ---------------------------------------------------------

    /** NUT exposes "<ups>_status_data" with flags like "OL" (mains) or "OB DISCHRG" (battery). */
    static boolean onBattery(Entity e) {
        return "sensor".equals(e.domain) && e.id.endsWith("_status_data")
                && (" " + e.state + " ").contains(" OB ");
    }

    private static String upsPrefix(Entity statusData) {
        return statusData.id.substring(0, statusData.id.length() - "_status_data".length());
    }

    private static Entity upsStatus(Map<String, Entity> all) {
        for (Entity e : all.values()) {
            if ("sensor".equals(e.domain) && e.id.endsWith("_status_data") && all.containsKey(
                    upsPrefix(e) + "_battery_charge")) {
                return e;
            }
        }
        return null;
    }

    private static String num(Map<String, Entity> all, String id) {
        Entity e = all.get(id);
        return e == null ? null : Format.number(e.state);
    }

    /** "Заряд 100% · хватит на ~33 мин · нагрузка 12%". */
    static String upsSummary(Map<String, Entity> all, String prefix) {
        StringBuilder sb = new StringBuilder();
        String charge = num(all, prefix + "_battery_charge");
        if (charge != null) sb.append("Заряд ").append(charge).append('%');
        Entity rt = all.get(prefix + "_battery_runtime");
        if (rt != null) {
            try {
                long min = Math.round(Double.parseDouble(rt.state) / 60);
                if (sb.length() > 0) sb.append(" · ");
                sb.append("хватит на ~").append(min >= 90 ? (min / 60) + " ч " + (min % 60) + " мин" : min + " мин");
            } catch (NumberFormatException ignored) {
                // Unknown runtime.
            }
        }
        String load = num(all, prefix + "_load");
        if (load != null) {
            if (sb.length() > 0) sb.append(" · ");
            sb.append("нагрузка ").append(load).append('%');
        }
        return sb.toString();
    }

    private View upsCard(Map<String, Entity> all) {
        final Entity status = upsStatus(all);
        if (status == null || !status.available()) return null;
        String prefix = upsPrefix(status);
        boolean battery = onBattery(status);
        LinearLayout card = ui.horizontal();
        card.setBackgroundResource(R.drawable.card);
        card.setPadding(ui.dp(18), ui.dp(15), ui.dp(18), ui.dp(15));
        card.addView(ui.icon(R.drawable.ic_bolt, battery ? R.color.alarm : R.color.ink, 19));
        LinearLayout body = ui.vertical();
        TextView t = ui.text(battery ? "Дом на ИБП" : "Электричество есть", 14.5f,
                battery ? R.color.alarm : R.color.text);
        t.setTypeface(Ui.MEDIUM);
        body.addView(t);
        String in = num(all, prefix + "_input_voltage");
        String summary = upsSummary(all, prefix);
        TextView sub = ui.text((in != null && !battery ? "Сеть " + in + " В · " : "") + "ИБП: "
                + summary.substring(0, 1).toLowerCase() + summary.substring(1), 12.5f, R.color.text_dim);
        body.addView(sub, ui.margins(ui.matchWidth(), 0, 2, 0, 0));
        card.addView(body, ui.margins(ui.weight(1), 13, 0, 0, 0));
        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openDetails(status);
            }
        });
        return card;
    }

    // ---- heating --------------------------------------------------------------------

    /** "Обогрев тамбур z2 Температура тамбур" -> "Тамбур". */
    static String climateLabel(Entity e) {
        List<String> out = new ArrayList<String>();
        for (String w : e.name().split("\\s+")) {
            String l = w.toLowerCase();
            if (l.equals("обогрев") || l.equals("z2") || l.equals("температура") || l.equals("отопление")) continue;
            boolean dup = false;
            for (String o : out) {
                if (o.equalsIgnoreCase(w)) dup = true;
            }
            if (!dup) out.add(w);
        }
        if (out.isEmpty()) return e.name();
        StringBuilder sb = new StringBuilder();
        for (String w : out) {
            if (sb.length() > 0) sb.append(' ');
            sb.append(w);
        }
        return capitalize(sb.toString());
    }

    private View heatingCard(Collection<Entity> all) {
        List<Entity> list = new ArrayList<Entity>();
        for (Entity e : all) {
            if ("climate".equals(e.domain) && e.primary()) list.add(e);
        }
        if (list.isEmpty()) return null;
        Collections.sort(list, new Comparator<Entity>() {
            @Override
            public int compare(Entity a, Entity b) {
                return climateLabel(a).compareToIgnoreCase(climateLabel(b));
            }
        });
        LinearLayout card = ui.card(R.drawable.card, 14, 18);
        int heating = 0;
        for (Entity e : list) {
            if ("heating".equals(e.attributes.optString("hvac_action"))) heating++;
        }
        LinearLayout top = ui.horizontal();
        top.addView(ui.kicker("Отопление"), ui.weight(1));
        top.addView(ui.text(heating > 0 ? "греет: " + heating : "никто не греет", 12.5f,
                heating > 0 ? R.color.accent : R.color.text_dim));
        card.addView(top, ui.margins(ui.matchWidth(), 0, 2, 0, 4));
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) card.addView(ui.divider(), new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ui.dp(1)));
            card.addView(heatingRow(list.get(i)));
        }
        return card;
    }

    private View heatingRow(final Entity e) {
        LinearLayout row = ui.horizontal();
        row.setPadding(0, ui.dp(10), 0, ui.dp(10));
        row.setBackgroundResource(R.drawable.nav_item);
        LinearLayout texts = ui.vertical();
        TextView name = ui.text(climateLabel(e), 14.5f, R.color.text);
        name.setTypeface(Ui.MEDIUM);
        texts.addView(name);
        String cur = Format.number(e.attributes.optString("current_temperature"));
        boolean off = "off".equals(e.state) || !e.available();
        boolean heats = "heating".equals(e.attributes.optString("hvac_action"));
        String sub = (cur != null ? "сейчас " + signedTemp(cur) + "°" : "")
                + (off ? " · " + (e.available() ? "выключен" : "нет связи") : heats ? " · греет" : "");
        TextView st = ui.text(sub, 12.5f, heats ? R.color.accent : R.color.text_dim);
        texts.addView(st, ui.margins(ui.wrap(), 0, 1, 0, 0));
        row.addView(texts, ui.weight(1));

        double target = e.attributes.optDouble("temperature", Double.NaN);
        boolean settable = !off && !Double.isNaN(target);
        TextView minus = smallButton("−", settable);
        TextView value = ui.number(Double.isNaN(target) ? "—" : Format.number(target) + "°", 20);
        value.setGravity(Gravity.CENTER);
        value.setMinWidth(ui.dp(56));
        value.setAlpha(settable ? 1f : 0.45f);
        TextView plus = smallButton("+", settable);
        row.addView(minus);
        row.addView(value);
        row.addView(plus);
        minus.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.stepTemperature(e, -1);
            }
        });
        plus.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.stepTemperature(e, 1);
            }
        });
        row.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openDetails(e); // modes, presets, exact temperature
            }
        });
        return row;
    }

    private TextView smallButton(String label, boolean enabled) {
        TextView b = ui.button(label, R.drawable.btn_small, R.color.text, 40);
        b.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 18);
        b.setPadding(0, 0, 0, 0);
        b.setLayoutParams(new LinearLayout.LayoutParams(ui.dp(44), ui.dp(40)));
        b.setEnabled(enabled);
        b.setAlpha(enabled ? 1f : 0.35f);
        return b;
    }

    private static String signedTemp(String formatted) {
        return formatted.startsWith("−") || formatted.equals("0") ? formatted : "+" + formatted;
    }

    // ---- event log -------------------------------------------------------------------

    /** Entities whose changes are worth a line in the log. */
    static boolean logWorthy(Entity e) {
        if (!e.primary()) return false;
        if ("alarm_control_panel".equals(e.domain)) return true;
        if ("binary_sensor".equals(e.domain)) {
            String dc = e.deviceClass();
            return has(DOOR, dc) || has(LEAK, dc) || has(SMOKE, dc) || e.id.endsWith("_person_occupancy");
        }
        return "sensor".equals(e.domain) && e.id.endsWith("_status_data");
    }

    /** "Баня: дверь открыта" etc.; null when the change is not interesting (e.g. person left). */
    static String describe(Entity e, String state) {
        if ("alarm_control_panel".equals(e.domain)) {
            return "Охрана: " + Format.state(state).toLowerCase();
        }
        if ("sensor".equals(e.domain)) {
            return (" " + state + " ").contains(" OB ") ? "Пропало электричество, дом на ИБП"
                    : (" " + state + " ").contains(" OL ") ? "Электричество есть" : null;
        }
        boolean on = "on".equals(state);
        String dc = e.deviceClass();
        if (e.id.endsWith("_person_occupancy")) {
            if (!on) return null;
            String cam = e.name().replaceAll("(?i)\\s*person occupancy$", "");
            return "Человек · " + cam;
        }
        if (has(DOOR, dc)) {
            if (!"on".equals(state) && !"off".equals(state)) return null;
            return capitalize(shortName(e)) + ": " + (on ? "открыто" : "закрыто");
        }
        if (has(LEAK, dc)) return on ? "Протечка · " + shortName(e).toLowerCase() : null;
        if (has(SMOKE, dc)) return on ? "Дым · " + shortName(e).toLowerCase() : null;
        return null;
    }

    private View eventsCard(Model m) {
        if (m.events == null) return null;
        List<String[]> lines = new ArrayList<String[]>();
        SimpleDateFormat hm = new SimpleDateFormat("HH:mm", Locale.US);
        for (int i = m.events.size() - 1; i >= 0 && lines.size() < 8; i--) {
            Event ev = m.events.get(i);
            Entity e = m.entities.get(ev.entityId);
            if (e == null) continue;
            String text = describe(e, ev.state);
            if (text == null) continue;
            lines.add(new String[]{hm.format(new Date(ev.when)), text});
        }
        LinearLayout card = ui.card(R.drawable.card, 14, 18);
        LinearLayout top = ui.horizontal();
        top.addView(ui.kicker("События"), ui.weight(1));
        top.addView(ui.text("за 12 часов", 12.5f, R.color.text_dim));
        card.addView(top, ui.margins(ui.matchWidth(), 0, 2, 0, 6));
        if (lines.isEmpty()) {
            card.addView(ui.text("Ничего не происходило", 13.5f, R.color.text_dim),
                    ui.margins(ui.matchWidth(), 0, 4, 0, 2));
        }
        for (String[] l : lines) {
            LinearLayout row = ui.horizontal();
            row.setGravity(Gravity.TOP);
            TextView time = ui.text(l[0], 13.5f, R.color.text_dim);
            time.setMinWidth(ui.dp(52));
            row.addView(time);
            TextView text = ui.text(l[1], 13.5f, l[1].startsWith("Протечка") || l[1].startsWith("Дым")
                    || l[1].startsWith("Пропало") ? R.color.alarm : R.color.text);
            row.addView(text, ui.weight(1));
            card.addView(row, ui.margins(ui.matchWidth(), 0, 7, 0, 0));
        }
        return card;
    }

    // ---- helpers ----------------------------------------------------------------------

    private static Entity first(Collection<Entity> all, String domain) {
        Entity found = null;
        for (Entity e : all) {
            if (domain.equals(e.domain) && e.primary() && (found == null || e.id.compareTo(found.id) < 0)) {
                found = e;
            }
        }
        return found;
    }

    static boolean has(String[] list, String v) {
        for (String s : list) {
            if (s.equals(v)) return true;
        }
        return false;
    }

    private static final String[] NOISE = {"датчик", "датчика", "двери", "дверь", "протечки", "протечка",
            "влага", "влажность", "дым", "дыма", "газа", "газ", "z2", "contact", "sensor", "smoke", "leak",
            "water", "moisture", "door", "window", "окна", "окно"};

    /** "Датчик двери баня Дверь" -> "баня". */
    static String shortName(Entity e) {
        String[] words = e.name().split("\\s+");
        StringBuilder sb = new StringBuilder();
        for (String w : words) {
            if (has(NOISE, w.toLowerCase())) continue;
            if (sb.length() > 0) sb.append(' ');
            sb.append(w);
        }
        return sb.length() > 0 ? sb.toString() : e.name();
    }

    private static String lastWord(String s) {
        String[] w = s.trim().split("\\s+");
        return w[w.length - 1].toLowerCase();
    }

    private static String capitalize(String s) {
        return s.isEmpty() ? s : s.substring(0, 1).toUpperCase() + s.substring(1);
    }

    /** Explicit "+" for positive temperatures, as on the mockup. */
    private static String signed(String formatted) {
        return formatted.startsWith("−") || formatted.equals("0") ? formatted : "+" + formatted;
    }

    static String plural(int n, String one, String few, String many) {
        int m10 = n % 10, m100 = n % 100;
        if (m10 == 1 && m100 != 11) return one;
        if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
        return many;
    }
}
