package com.andreia.smarthome;

import android.graphics.Bitmap;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** "Камеры": a two-column grid of live snapshots with Frigate motion/person status. */
final class CamerasScreen {

    interface Host {
        Bitmap cameraImage(Entity camera, int width);

        void openCamera(Entity camera);

        void openMenu(Entity camera);
    }

    enum Filter { ALL, MOTION, PEOPLE }

    private static final long RECENT_MS = 15 * 60000L;

    private final Ui ui;
    private final LinearLayout root;
    private final Host host;
    private final Map<String, ImageView> images = new HashMap<String, ImageView>();
    private Filter filter = Filter.ALL;
    private Map<String, Entity> lastEntities;

    CamerasScreen(Ui ui, LinearLayout root, Host host) {
        this.ui = ui;
        this.root = root;
        this.host = host;
    }

    static List<Entity> cameras(Map<String, Entity> entities) {
        List<Entity> list = new ArrayList<Entity>();
        for (Entity e : entities.values()) {
            if ("camera".equals(e.domain) && e.primary() && e.available()) list.add(e);
        }
        Collections.sort(list, new Comparator<Entity>() {
            @Override
            public int compare(Entity a, Entity b) {
                return a.name().compareToIgnoreCase(b.name());
            }
        });
        return list;
    }

    private static String objectId(Entity camera) {
        return camera.id.substring(camera.id.indexOf('.') + 1);
    }

    private static Entity sensor(Map<String, Entity> all, Entity camera, String suffix) {
        return all.get("binary_sensor." + objectId(camera) + suffix);
    }

    void render(Map<String, Entity> entities) {
        lastEntities = entities;
        root.removeAllViews();
        images.clear();
        List<Entity> cams = cameras(entities);
        boolean frigate = false;
        for (Entity c : cams) {
            if ("frigate".equals(c.attributes.optString("client_id"))) frigate = true;
        }
        root.addView(ui.header((frigate ? "Frigate · " : "") + cams.size() + " "
                + HomeScreen.plural(cams.size(), "камера", "камеры", "камер") + " онлайн", "Камеры"));

        LinearLayout chips = ui.horizontal();
        chips.setPadding(ui.dp(18), ui.dp(4), ui.dp(18), ui.dp(12));
        addChip(chips, "Все", Filter.ALL);
        addChip(chips, "Движение", Filter.MOTION);
        addChip(chips, "Люди", Filter.PEOPLE);
        root.addView(chips);

        long now = System.currentTimeMillis();
        List<Entity> shown = new ArrayList<Entity>();
        for (Entity c : cams) {
            Entity motion = sensor(entities, c, "_motion");
            Entity person = sensor(entities, c, "_person_occupancy");
            boolean moving = motion != null && ("on".equals(motion.state) || now - motion.lastChanged < RECENT_MS);
            boolean people = person != null && "on".equals(person.state);
            if (filter == Filter.MOTION && !moving) continue;
            if (filter == Filter.PEOPLE && !people) continue;
            shown.add(c);
        }
        if (shown.isEmpty()) {
            TextView t = ui.text(cams.isEmpty() ? "Камер пока нет" : "Сейчас никого", 15, R.color.text_dim);
            t.setGravity(Gravity.CENTER);
            t.setPadding(0, ui.dp(48), 0, ui.dp(48));
            root.addView(t, ui.matchWidth());
        }
        int width = ui.context.getResources().getDisplayMetrics().widthPixels;
        int tileWidth = (width - ui.dp(36 + 11)) / 2;
        for (int i = 0; i < shown.size(); i += 2) {
            LinearLayout row = ui.horizontal();
            row.setGravity(Gravity.TOP);
            row.addView(tile(entities, shown.get(i), tileWidth, now), ui.weight(1));
            row.addView(ui.spacer(11));
            if (i + 1 < shown.size()) {
                row.addView(tile(entities, shown.get(i + 1), tileWidth, now), ui.weight(1));
            } else {
                row.addView(new View(ui.context), ui.weight(1));
            }
            root.addView(row, ui.margins(ui.matchWidth(), 18, 0, 18, 11));
        }
        View event = lastEvent(entities, cams);
        if (event != null) {
            root.addView(event, ui.margins(ui.matchWidth(), 18, 3, 18, 12));
        }
    }

    private void addChip(LinearLayout chips, String label, final Filter f) {
        boolean active = filter == f;
        TextView chip = ui.text(label, 13, active ? R.color.on_dark : R.color.text_body);
        chip.setTypeface(Ui.MEDIUM);
        chip.setGravity(Gravity.CENTER);
        chip.setPadding(ui.dp(15), 0, ui.dp(15), 0);
        chip.setBackgroundResource(active ? R.drawable.chip_active : R.drawable.chip);
        chip.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                filter = f;
                if (lastEntities != null) render(lastEntities);
            }
        });
        chips.addView(chip, ui.margins(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ui.dp(34)), 0, 0, 7, 0));
    }

    private View tile(Map<String, Entity> entities, final Entity cam, int width, long now) {
        LinearLayout tile = ui.vertical();
        tile.setBackgroundResource(R.drawable.tile);
        tile.setClipToOutline(true);

        FrameLayout frame = new FrameLayout(ui.context);
        frame.setBackgroundColor(ui.color(R.color.placeholder));
        ImageView placeholder = ui.icon(R.drawable.ic_camera, R.color.text_nav, 26);
        frame.addView(placeholder, new FrameLayout.LayoutParams(ui.dp(26), ui.dp(26), Gravity.CENTER));
        ImageView image = new ImageView(ui.context);
        image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        Bitmap bmp = host.cameraImage(cam, width);
        if (bmp != null) image.setImageBitmap(bmp);
        images.put(cam.id, image);
        frame.addView(image, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        LinearLayout badge = ui.horizontal();
        badge.setBackgroundResource(R.drawable.badge);
        badge.setPadding(ui.dp(6), ui.dp(3), ui.dp(8), ui.dp(3));
        View dot = new View(ui.context);
        dot.setBackgroundResource(R.drawable.dot);
        badge.addView(dot, ui.margins(new LinearLayout.LayoutParams(ui.dp(5), ui.dp(5)), 0, 0, 5, 0));
        boolean recording = "recording".equals(cam.state);
        TextView live = ui.text(recording ? "Запись" : "Эфир", 9.5f, R.color.on_dark);
        live.setAllCaps(true);
        live.setLetterSpacing(0.1f);
        live.setTypeface(Ui.MEDIUM);
        badge.addView(live);
        FrameLayout.LayoutParams blp = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.START);
        blp.setMargins(ui.dp(9), ui.dp(8), 0, 0);
        frame.addView(badge, blp);
        tile.addView(frame, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ui.dp(124)));

        LinearLayout text = ui.vertical();
        text.setPadding(ui.dp(12), ui.dp(10), ui.dp(12), ui.dp(12));
        TextView name = ui.text(cam.name(), 14, R.color.text);
        name.setTypeface(Ui.MEDIUM);
        name.setSingleLine(true);
        name.setEllipsize(android.text.TextUtils.TruncateAt.END);
        text.addView(name);
        TextView state = ui.text(status(entities, cam, now), 12, R.color.text_dim);
        state.setSingleLine(true);
        state.setEllipsize(android.text.TextUtils.TruncateAt.END);
        text.addView(state, ui.margins(ui.matchWidth(), 0, 2, 0, 0));
        tile.addView(text);

        tile.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openCamera(cam);
            }
        });
        tile.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                host.openMenu(cam);
                return true;
            }
        });
        return tile;
    }

    private static String status(Map<String, Entity> all, Entity cam, long now) {
        Entity person = sensor(all, cam, "_person_occupancy");
        if (person != null && "on".equals(person.state)) return "Человек в кадре";
        Entity motion = sensor(all, cam, "_motion");
        if (motion == null) return Format.state(cam.state);
        if ("on".equals(motion.state)) return "Движение сейчас";
        long ago = now - motion.lastChanged;
        if (motion.lastChanged > 0 && ago < 60 * 60000L) {
            long min = Math.max(1, ago / 60000);
            return "Движение " + min + " мин назад";
        }
        return "Тихо";
    }

    /** The latest "person" detection across cameras, like "Человек у ворот · 21:08". */
    private View lastEvent(Map<String, Entity> all, List<Entity> cams) {
        Entity bestCam = null;
        Entity best = null;
        for (Entity c : cams) {
            Entity p = sensor(all, c, "_person_occupancy");
            if (p == null || p.lastChanged == 0 || !p.available()) continue;
            if (!"on".equals(p.state) && System.currentTimeMillis() - p.lastChanged > 24 * 3600000L) continue;
            if (best == null || p.lastChanged > best.lastChanged) {
                best = p;
                bestCam = c;
            }
        }
        if (best == null) return null;
        final Entity cam = bestCam;
        LinearLayout card = ui.horizontal();
        card.setBackgroundResource(R.drawable.tile);
        card.setPadding(ui.dp(16), ui.dp(13), ui.dp(16), ui.dp(13));
        LinearLayout box = ui.horizontal();
        box.setGravity(Gravity.CENTER);
        box.setBackgroundResource(R.drawable.icon_box);
        box.addView(ui.icon(R.drawable.ic_person, R.color.ink, 17));
        card.addView(box, new LinearLayout.LayoutParams(ui.dp(34), ui.dp(34)));
        LinearLayout body = ui.vertical();
        TextView t = ui.text("Человек · " + cam.name(), 13.5f, R.color.text);
        t.setTypeface(Ui.MEDIUM);
        body.addView(t);
        String time = new SimpleDateFormat("HH:mm", Locale.US).format(new Date(best.lastChanged));
        TextView sub = ui.text("on".equals(best.state) ? "сейчас в кадре" : "последний раз в " + time,
                12, R.color.text_dim);
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        body.addView(sub, ui.margins(ui.matchWidth(), 0, 1, 0, 0));
        card.addView(body, ui.margins(ui.weight(1), 12, 0, 8, 0));
        card.addView(ui.icon(R.drawable.ic_chevron, R.color.text_nav, 16));
        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                host.openCamera(cam);
            }
        });
        return card;
    }

    /** A fresh snapshot arrived: update the tile in place. */
    void onImage(String entityId, Bitmap bitmap) {
        ImageView v = images.get(entityId);
        if (v != null && bitmap != null) {
            v.setImageBitmap(bitmap);
        }
    }

    /** Re-requests snapshots for the visible tiles. */
    void refreshImages(Map<String, Entity> entities, int width) {
        android.graphics.Rect visible = new android.graphics.Rect();
        for (Map.Entry<String, ImageView> en : images.entrySet()) {
            Entity e = entities.get(en.getKey());
            // Only tiles on screen: saves mobile data with many cameras.
            if (e != null && en.getValue().getLocalVisibleRect(visible)) host.cameraImage(e, width);
        }
    }
}
