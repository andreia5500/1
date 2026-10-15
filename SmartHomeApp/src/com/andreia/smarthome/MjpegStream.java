package com.andreia.smarthome;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Live video from HA's /api/camera_proxy_stream (multipart MJPEG): frames are cut
 * out by their JPEG start/end markers and decoded one by one. No player library.
 */
final class MjpegStream {

    interface Listener {
        void onFrame(Bitmap frame, float fps);

        void onStatus(String status);
    }

    private final HaSession session;
    private final String entityId;
    private final int maxWidth;
    private final Listener listener;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean running;
    private volatile HttpURLConnection conn;

    MjpegStream(HaSession session, String entityId, int maxWidth, Listener listener) {
        this.session = session;
        this.entityId = entityId;
        this.maxWidth = maxWidth;
        this.listener = listener;
    }

    void start() {
        running = true;
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                while (running) {
                    try {
                        read();
                    } catch (Exception e) {
                        status("Переподключение видео…");
                    }
                    sleep(2000);
                }
            }
        }, "mjpeg-" + entityId);
        t.setDaemon(true);
        t.start();
    }

    void stop() {
        running = false;
        HttpURLConnection c = conn;
        if (c != null) {
            c.disconnect(); // unblocks the reading thread
        }
    }

    private void read() throws Exception {
        String token = session.validAccessToken();
        HttpURLConnection c = (HttpURLConnection) new URL(
                session.baseUrl() + "/api/camera_proxy_stream/" + entityId).openConnection();
        conn = c;
        c.setConnectTimeout(10000);
        c.setReadTimeout(15000);
        c.setRequestProperty("Authorization", "Bearer " + token);
        try {
            if (c.getResponseCode() != 200) {
                status("Видео недоступно (" + c.getResponseCode() + ")");
                return;
            }
            InputStream in = new BufferedInputStream(c.getInputStream(), 65536);
            ByteArrayOutputStream frame = new ByteArrayOutputStream(256 * 1024);
            boolean inFrame = false;
            int prev = -1;
            long windowStart = System.currentTimeMillis();
            int framesInWindow = 0;
            float fps = 0;
            int b;
            while (running && (b = in.read()) != -1) {
                if (!inFrame) {
                    if (prev == 0xFF && b == 0xD8) {
                        inFrame = true;
                        frame.reset();
                        frame.write(0xFF);
                        frame.write(0xD8);
                    }
                } else {
                    frame.write(b);
                    if (prev == 0xFF && b == 0xD9) {
                        inFrame = false;
                        framesInWindow++;
                        long now = System.currentTimeMillis();
                        if (now - windowStart >= 2000) {
                            fps = framesInWindow * 1000f / (now - windowStart);
                            windowStart = now;
                            framesInWindow = 0;
                        }
                        deliver(frame.toByteArray(), fps);
                    } else if (frame.size() > 8 * 1024 * 1024) {
                        inFrame = false; // garbage, resync
                    }
                }
                prev = b;
            }
        } finally {
            c.disconnect();
            conn = null;
        }
    }

    private void deliver(byte[] jpeg, final float fps) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length, bounds);
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inSampleSize = 1;
        while (bounds.outWidth / (opts.inSampleSize * 2) >= maxWidth) {
            opts.inSampleSize *= 2;
        }
        final Bitmap bmp = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length, opts);
        if (bmp == null) {
            return;
        }
        ui.post(new Runnable() {
            @Override
            public void run() {
                if (running) {
                    listener.onFrame(bmp, fps);
                }
            }
        });
    }

    private void status(final String s) {
        ui.post(new Runnable() {
            @Override
            public void run() {
                if (running) {
                    listener.onStatus(s);
                }
            }
        });
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ignored) {
            // Loop checks running.
        }
    }
}
