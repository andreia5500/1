package com.andreia.smarthome;

import android.content.Context;
import android.graphics.PorterDuff;
import android.graphics.Typeface;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Small view factory for the "light minimalism" look, so screens read like the mockups. */
final class Ui {

    static final Typeface LIGHT = Typeface.create("sans-serif-light", Typeface.NORMAL);
    static final Typeface MEDIUM = Typeface.create("sans-serif-medium", Typeface.NORMAL);

    final Context context;
    private final float density;

    Ui(Context context) {
        this.context = context;
        this.density = context.getResources().getDisplayMetrics().density;
    }

    int dp(float v) {
        return Math.round(v * density);
    }

    int color(int res) {
        return context.getResources().getColor(res);
    }

    TextView text(float sp, int colorRes) {
        TextView t = new TextView(context);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(color(colorRes));
        return t;
    }

    TextView text(String s, float sp, int colorRes) {
        TextView t = text(sp, colorRes);
        t.setText(s);
        return t;
    }

    /** Small uppercase label, e.g. "ОХРАНА". */
    TextView kicker(String s) {
        TextView t = text(s, 11, R.color.text_dim);
        t.setAllCaps(true);
        t.setLetterSpacing(0.14f);
        t.setTypeface(MEDIUM);
        return t;
    }

    /** Big light number, e.g. "−3,4°". */
    TextView number(String s, float sp) {
        TextView t = text(s, sp, R.color.text);
        t.setTypeface(LIGHT);
        t.setLetterSpacing(-0.03f);
        t.setIncludeFontPadding(false);
        return t;
    }

    TextView title(String s, float sp) {
        TextView t = text(s, sp, R.color.text);
        t.setTypeface(MEDIUM);
        t.setLetterSpacing(-0.015f);
        return t;
    }

    LinearLayout vertical() {
        LinearLayout l = new LinearLayout(context);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    LinearLayout horizontal() {
        LinearLayout l = new LinearLayout(context);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        return l;
    }

    /** A rounded card with the given background drawable and padding. */
    LinearLayout card(int drawable, float padV, float padH) {
        LinearLayout c = vertical();
        c.setBackgroundResource(drawable);
        c.setPadding(dp(padH), dp(padV), dp(padH), dp(padV));
        return c;
    }

    /** Screen header: kicker line and a 27sp title. */
    LinearLayout header(String kicker, String title) {
        LinearLayout h = vertical();
        h.setPadding(dp(22), dp(30), dp(22), dp(14));
        TextView k = kicker(kicker);
        k.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10.5f);
        k.setLetterSpacing(0.16f);
        h.addView(k);
        TextView t = title(title, 27);
        t.setLetterSpacing(-0.02f);
        h.addView(t, margins(wrap(), 0, 7, 0, 0));
        return h;
    }

    TextView button(String label, int drawable, int textColor, float heightDp) {
        TextView b = text(label, 14.5f, textColor);
        b.setTypeface(MEDIUM);
        b.setGravity(Gravity.CENTER);
        b.setBackgroundResource(drawable);
        b.setPadding(dp(18), 0, dp(18), 0);
        b.setClickable(true);
        b.setFocusable(true);
        b.setMinHeight(dp(heightDp));
        b.setSingleLine(true);
        b.setEllipsize(TextUtils.TruncateAt.END);
        return b;
    }

    ImageView icon(int drawable, int colorRes, float sizeDp) {
        ImageView i = new ImageView(context);
        i.setImageResource(drawable);
        i.setColorFilter(color(colorRes), PorterDuff.Mode.SRC_IN);
        i.setLayoutParams(new LinearLayout.LayoutParams(dp(sizeDp), dp(sizeDp)));
        return i;
    }

    View divider() {
        View v = new View(context);
        v.setBackgroundColor(color(R.color.line));
        return v;
    }

    View spacer(float dp) {
        View v = new View(context);
        v.setLayoutParams(new LinearLayout.LayoutParams(dp(dp), dp(dp)));
        return v;
    }

    LinearLayout.LayoutParams wrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    LinearLayout.LayoutParams matchWidth() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    LinearLayout.LayoutParams weight(float w) {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, w);
    }

    LinearLayout.LayoutParams weight(float w, float heightDp) {
        return new LinearLayout.LayoutParams(0, dp(heightDp), w);
    }

    LinearLayout.LayoutParams margins(LinearLayout.LayoutParams lp, float l, float t, float r, float b) {
        lp.setMargins(dp(l), dp(t), dp(r), dp(b));
        return lp;
    }
}
