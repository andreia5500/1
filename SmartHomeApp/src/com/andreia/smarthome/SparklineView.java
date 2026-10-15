package com.andreia.smarthome;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

/** A thin line chart with a soft fill under it, for the power card. */
final class SparklineView extends View {

    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private double[] values = new double[0];
    private boolean filled = true;

    SparklineView(Context context) {
        super(context);
        line.setStyle(Paint.Style.STROKE);
        line.setStrokeWidth(1.6f * context.getResources().getDisplayMetrics().density);
        line.setStrokeJoin(Paint.Join.ROUND);
        line.setStrokeCap(Paint.Cap.ROUND);
        line.setColor(context.getResources().getColor(R.color.accent));
        fill.setStyle(Paint.Style.FILL);
        fill.setColor(context.getResources().getColor(R.color.accent_soft));
    }

    void setValues(double[] values, boolean filled) {
        this.values = values;
        this.filled = filled;
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        if (values.length < 2) {
            return;
        }
        double min = Double.MAX_VALUE, max = -Double.MAX_VALUE;
        for (double v : values) {
            min = Math.min(min, v);
            max = Math.max(max, v);
        }
        if (max - min < 1e-9) {
            max = min + 1;
        }
        float pad = line.getStrokeWidth();
        float w = getWidth() - 2 * pad, h = getHeight() - 2 * pad;
        Path p = new Path();
        for (int i = 0; i < values.length; i++) {
            float x = pad + w * i / (values.length - 1);
            float y = pad + (float) (h * (1 - (values[i] - min) / (max - min)) * 0.85 + h * 0.1);
            if (i == 0) p.moveTo(x, y);
            else p.lineTo(x, y);
        }
        if (filled) {
            Path area = new Path(p);
            area.lineTo(pad + w, getHeight());
            area.lineTo(pad, getHeight());
            area.close();
            canvas.drawPath(area, fill);
        }
        canvas.drawPath(p, line);
    }
}
