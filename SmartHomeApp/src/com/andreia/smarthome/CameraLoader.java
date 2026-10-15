package com.andreia.smarthome;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.LruCache;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Loads camera snapshots from /api/camera_proxy with the session's token. */
final class CameraLoader {

    interface Listener {
        void onCameraImage(String entityId);
    }

    private static final long STALE_MS = 5000;

    private final HaSession session;
    private final Listener listener;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService pool = Executors.newFixedThreadPool(3);
    private final LruCache<String, Bitmap> cache = new LruCache<String, Bitmap>(24 * 1024 * 1024) {
        @Override
        protected int sizeOf(String key, Bitmap value) {
            return value.getByteCount();
        }
    };
    private final Map<String, Long> loadedAt = new HashMap<String, Long>();
    private final Set<String> inFlight = new HashSet<String>();

    CameraLoader(HaSession session, Listener listener) {
        this.session = session;
        this.listener = listener;
    }

    Bitmap cached(String entityId) {
        return cache.get(entityId);
    }

    /** Starts a download unless one is running or the cached image is fresh (UI thread). */
    void request(final String entityId, final int maxWidth, boolean force) {
        Long at = loadedAt.get(entityId);
        if (inFlight.contains(entityId)
                || (!force && at != null && System.currentTimeMillis() - at < STALE_MS)) {
            return;
        }
        inFlight.add(entityId);
        pool.execute(new Runnable() {
            @Override
            public void run() {
                final Bitmap bitmap = download(entityId, maxWidth);
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        inFlight.remove(entityId);
                        loadedAt.put(entityId, System.currentTimeMillis());
                        if (bitmap != null) {
                            cache.put(entityId, bitmap);
                            listener.onCameraImage(entityId);
                        }
                    }
                });
            }
        });
    }

    void shutdown() {
        pool.shutdownNow();
    }

    private Bitmap download(String entityId, int maxWidth) {
        HttpURLConnection conn = null;
        try {
            String token = session.validAccessToken();
            conn = (HttpURLConnection) new URL(session.baseUrl() + "/api/camera_proxy/" + entityId)
                    .openConnection();
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(15000);
            conn.setRequestProperty("Authorization", "Bearer " + token);
            if (conn.getResponseCode() != 200) {
                return null;
            }
            InputStream in = conn.getInputStream();
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[16384];
            int n;
            while ((n = in.read(chunk)) > 0) {
                buf.write(chunk, 0, n);
            }
            in.close();
            byte[] data = buf.toByteArray();

            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(data, 0, data.length, bounds);
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = 1;
            while (bounds.outWidth / (opts.inSampleSize * 2) >= maxWidth) {
                opts.inSampleSize *= 2;
            }
            return BitmapFactory.decodeByteArray(data, 0, data.length, opts);
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }
}
