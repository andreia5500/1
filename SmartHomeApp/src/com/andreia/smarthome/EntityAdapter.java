package com.andreia.smarthome;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Typeface;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.CompoundButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.Switch;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** List rows for entities (with controls per kind) and section headers (plain strings). */
final class EntityAdapter extends BaseAdapter {

    interface Controller {
        void call(String domain, String service, Entity e, JSONObject data);

        void toggle(Entity e, boolean on);

        void stepTemperature(Entity e, int direction);

        void openDetails(Entity e);

        void openMenu(Entity e);

        Bitmap cameraImage(Entity e, int width);
    }

    private static final int TYPE_HEADER = Entity.Kind.values().length;

    private final Context context;
    private final Controller controller;
    private final float density;
    private List<Object> items = new ArrayList<Object>();

    EntityAdapter(Context context, Controller controller) {
        this.context = context;
        this.controller = controller;
        this.density = context.getResources().getDisplayMetrics().density;
    }

    void setItems(List<Object> items) {
        this.items = items;
        notifyDataSetChanged();
    }

    @Override
    public int getCount() {
        return items.size();
    }

    @Override
    public Object getItem(int position) {
        return items.get(position);
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public int getViewTypeCount() {
        return TYPE_HEADER + 1;
    }

    @Override
    public int getItemViewType(int position) {
        Object item = items.get(position);
        return item instanceof Entity ? ((Entity) item).kind().ordinal() : TYPE_HEADER;
    }

    @Override
    public boolean isEnabled(int position) {
        return items.get(position) instanceof Entity;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        Object item = items.get(position);
        if (!(item instanceof Entity)) {
            TextView header = convertView instanceof TextView ? (TextView) convertView : newHeader();
            header.setText(item.toString());
            return header;
        }
        Entity e = (Entity) item;
        Holder h;
        if (convertView != null && convertView.getTag() instanceof Holder) {
            h = (Holder) convertView.getTag();
        } else {
            h = e.kind() == Entity.Kind.CAMERA ? newCameraRow() : newRow(e.kind());
        }
        bind(h, e);
        return h.root;
    }

    // ---- views -------------------------------------------------------------

    private static final class Holder {
        View root;
        Entity entity;
        TextView icon, name, subtitle, value;
        Switch toggle;
        TextView minus, target, plus;
        TextView b1, b2, b3;
        ImageView image;
        CompoundButton.OnCheckedChangeListener toggleListener;
    }

    private int dp(float v) {
        return Math.round(v * density);
    }

    private TextView newHeader() {
        TextView t = new TextView(context);
        t.setTextColor(context.getResources().getColor(R.color.text_dim));
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        t.setTypeface(Ui.MEDIUM);
        t.setAllCaps(true);
        t.setLetterSpacing(0.14f);
        t.setPadding(dp(4), dp(18), dp(4), dp(2));
        return t;
    }

    private TextView text(float sp, int color) {
        TextView t = new TextView(context);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(context.getResources().getColor(color));
        return t;
    }

    private TextView smallButton(String label) {
        TextView b = text(18, R.color.text);
        b.setText(label);
        b.setGravity(Gravity.CENTER);
        b.setBackgroundResource(R.drawable.btn_small);
        b.setMinWidth(dp(44));
        b.setMinHeight(dp(40));
        b.setPadding(dp(10), 0, dp(10), 0);
        b.setClickable(true);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        lp.leftMargin = dp(6);
        b.setLayoutParams(lp);
        return b;
    }

    private Holder newRow(Entity.Kind kind) {
        final Holder h = new Holder();
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), dp(12), dp(12), dp(12));
        row.setMinimumHeight(dp(64));
        ViewGroup.MarginLayoutParams rowLp = new ViewGroup.MarginLayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        row.setLayoutParams(new android.widget.AbsListView.LayoutParams(rowLp));

        h.icon = text(22, R.color.text);
        h.icon.setVisibility(View.GONE); // the minimal look has no icon column
        row.addView(h.icon);

        LinearLayout texts = new LinearLayout(context);
        texts.setOrientation(LinearLayout.VERTICAL);
        texts.setPadding(dp(4), 0, dp(6), 0);
        h.name = text(15, R.color.text);
        h.name.setTypeface(Ui.MEDIUM);
        h.name.setMaxLines(2);
        h.name.setEllipsize(TextUtils.TruncateAt.END);
        h.subtitle = text(13, R.color.text_dim);
        h.subtitle.setSingleLine(true);
        h.subtitle.setEllipsize(TextUtils.TruncateAt.END);
        texts.addView(h.name);
        texts.addView(h.subtitle);
        row.addView(texts, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        switch (kind) {
            case TOGGLE:
            case LIGHT:
            case LOCK:
                h.toggle = new Switch(context);
                row.addView(h.toggle);
                h.toggleListener = new CompoundButton.OnCheckedChangeListener() {
                    @Override
                    public void onCheckedChanged(CompoundButton b, boolean checked) {
                        controller.toggle(h.entity, checked);
                    }
                };
                break;
            case CLIMATE:
                h.minus = smallButton("−");
                h.target = text(18, R.color.text);
                h.target.setGravity(Gravity.CENTER);
                h.target.setMinWidth(dp(58));
                h.plus = smallButton("+");
                row.addView(h.minus);
                row.addView(h.target);
                row.addView(h.plus);
                h.minus.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        controller.stepTemperature(h.entity, -1);
                    }
                });
                h.plus.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        controller.stepTemperature(h.entity, 1);
                    }
                });
                break;
            case COVER:
                h.b1 = smallButton("▲");
                h.b2 = smallButton("■");
                h.b3 = smallButton("▼");
                addServiceButton(row, h, h.b1, "open_cover");
                addServiceButton(row, h, h.b2, "stop_cover");
                addServiceButton(row, h, h.b3, "close_cover");
                break;
            case ACTION:
                h.b1 = smallButton("▶");
                row.addView(h.b1);
                h.b1.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Entity e = h.entity;
                        String service = "button".equals(e.domain) || "input_button".equals(e.domain)
                                ? "press" : "turn_on";
                        controller.call(e.domain, service, e, null);
                    }
                });
                break;
            case MEDIA:
                h.b1 = smallButton("⏯");
                addServiceButton(row, h, h.b1, "media_play_pause");
                break;
            case VACUUM:
                h.b1 = smallButton("▶");
                h.b2 = smallButton("⌂");
                addServiceButton(row, h, h.b1, "start");
                addServiceButton(row, h, h.b2, "return_to_base");
                break;
            default:
                h.value = text(16, R.color.text);
                h.value.setGravity(Gravity.END);
                h.value.setMaxWidth(dp(150));
                h.value.setMaxLines(2);
                h.value.setEllipsize(TextUtils.TruncateAt.END);
                row.addView(h.value);
                break;
        }

        row.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (h.toggle != null && h.entity.kind() == Entity.Kind.TOGGLE && h.toggle.isEnabled()) {
                    h.toggle.toggle();
                } else {
                    controller.openDetails(h.entity);
                }
            }
        });
        row.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                controller.openMenu(h.entity);
                return true;
            }
        });
        h.root = row;
        row.setTag(h);
        return h;
    }

    private void addServiceButton(LinearLayout row, final Holder h, TextView b, final String service) {
        row.addView(b);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                controller.call(h.entity.domain, service, h.entity, null);
            }
        });
    }

    private Holder newCameraRow() {
        final Holder h = new Holder();
        LinearLayout card = new LinearLayout(context);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(8), dp(8), dp(8), dp(10));
        card.setLayoutParams(new android.widget.AbsListView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        h.image = new ImageView(context);
        h.image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        h.image.setBackgroundColor(context.getResources().getColor(R.color.placeholder));
        h.image.setClipToOutline(true);
        card.addView(h.image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(200)));
        h.name = text(15, R.color.text);
        h.name.setPadding(dp(6), dp(8), dp(6), 0);
        card.addView(h.name);
        h.subtitle = text(12, R.color.text_dim);
        h.subtitle.setPadding(dp(6), 0, dp(6), 0);
        card.addView(h.subtitle);
        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                controller.openDetails(h.entity);
            }
        });
        card.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                controller.openMenu(h.entity);
                return true;
            }
        });
        h.root = card;
        card.setTag(h);
        return h;
    }

    // ---- binding -----------------------------------------------------------

    private void bind(Holder h, Entity e) {
        h.entity = e;
        boolean available = e.available() || "unknown".equals(e.state) && e.kind() == Entity.Kind.ACTION;
        h.root.setBackgroundResource(e.controllable() && e.isOn() && e.available()
                ? R.drawable.card_on : R.drawable.row_card);
        h.root.setAlpha(available || e.kind() == Entity.Kind.VALUE ? 1f : 0.55f);
        h.name.setText(e.name());

        if (e.kind() == Entity.Kind.CAMERA) {
            h.subtitle.setText(e.area != null ? e.area : Format.state(e.state));
            int width = h.root.getWidth() > 0 ? h.root.getWidth() : context.getResources().getDisplayMetrics().widthPixels;
            Bitmap bitmap = controller.cameraImage(e, width);
            if (bitmap != null) {
                h.image.setImageBitmap(bitmap);
            } else {
                h.image.setImageDrawable(null);
            }
            return;
        }

        h.icon.setText(Format.icon(e));
        String subtitle = subtitle(e);
        h.subtitle.setText(subtitle);
        h.subtitle.setVisibility(subtitle.isEmpty() ? View.GONE : View.VISIBLE);

        switch (e.kind()) {
            case TOGGLE:
            case LIGHT:
            case LOCK:
                h.toggle.setOnCheckedChangeListener(null);
                h.toggle.setChecked(e.isOn());
                h.toggle.setEnabled(e.available());
                h.toggle.setOnCheckedChangeListener(h.toggleListener);
                break;
            case CLIMATE:
                double target = e.attributes.optDouble("temperature", Double.NaN);
                boolean settable = !Double.isNaN(target) && e.available() && !"off".equals(e.state);
                h.target.setText(Double.isNaN(target) ? "—" : Format.number(target) + "°");
                h.target.setAlpha(settable ? 1f : 0.5f);
                h.minus.setEnabled(settable);
                h.plus.setEnabled(settable);
                h.minus.setAlpha(settable ? 1f : 0.4f);
                h.plus.setAlpha(settable ? 1f : 0.4f);
                break;
            case COVER:
            case ACTION:
            case MEDIA:
            case VACUUM:
                setEnabled(h.b1, available);
                setEnabled(h.b2, available);
                setEnabled(h.b3, available);
                break;
            case ALARM:
                h.value.setText(Format.state(e.state));
                h.value.setTextColor(context.getResources().getColor(alarmColor(e.state)));
                h.value.setTypeface(Typeface.DEFAULT_BOLD);
                break;
            default:
                h.value.setText(Format.stateOf(e));
                h.value.setTextColor(context.getResources().getColor(e.available() ? R.color.text : R.color.text_dim));
                h.value.setTypeface(Typeface.DEFAULT);
                break;
        }
    }

    private static void setEnabled(View v, boolean enabled) {
        if (v != null) {
            v.setEnabled(enabled);
            v.setAlpha(enabled ? 1f : 0.4f);
        }
    }

    static int alarmColor(String state) {
        if ("disarmed".equals(state)) return R.color.text_dim;
        if ("triggered".equals(state)) return R.color.error;
        if (state.startsWith("armed")) return R.color.ok;
        return R.color.warn;
    }

    private String subtitle(Entity e) {
        switch (e.kind()) {
            case CLIMATE:
                return Format.climate(e);
            case COVER:
                String s = Format.state(e.state);
                if (e.attributes.has("current_position")) {
                    s += " · " + e.attributes.optInt("current_position") + "%";
                }
                return s;
            case LIGHT:
                if (e.isOn() && e.attributes.has("brightness") && !e.attributes.isNull("brightness")) {
                    return Math.round(e.attributes.optInt("brightness") / 2.55) + "%";
                }
                return withArea(e, Format.state(e.state));
            case MEDIA:
                String title = e.attributes.optString("media_title", "");
                return title.isEmpty() ? Format.state(e.state) : Format.state(e.state) + " · " + title;
            case ACTION:
            case ALARM:
            case VALUE:
                return e.area != null ? e.area : "";
            default:
                return withArea(e, Format.state(e.state));
        }
    }

    private static String withArea(Entity e, String text) {
        return e.area != null ? text + " · " + e.area : text;
    }
}
