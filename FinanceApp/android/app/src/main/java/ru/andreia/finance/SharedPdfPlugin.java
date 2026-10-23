package ru.andreia.finance;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Принимает PDF, присланные в приложение через «Поделиться» или «Открыть с помощью»,
 * и отдаёт их веб-части по запросу take().
 */
@CapacitorPlugin(name = "SharedPdf")
public class SharedPdfPlugin extends Plugin {
    private static final String TAG = "SharedPdf";
    private static final int MAX_BYTES = 25 * 1024 * 1024;
    private static final List<JSObject> pending = new ArrayList<>();

    /** Вызывается из MainActivity при запуске и при получении нового Intent */
    static synchronized boolean collect(Activity activity, Intent intent) {
        if (intent == null || intent.getAction() == null) return false;
        String action = intent.getAction();
        List<Uri> uris = new ArrayList<>();
        if (Intent.ACTION_SEND.equals(action)) {
            Uri u = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (u != null) uris.add(u);
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(action)) {
            ArrayList<Uri> list = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
            if (list != null) uris.addAll(list);
        } else if (Intent.ACTION_VIEW.equals(action) && intent.getData() != null) {
            uris.add(intent.getData());
        } else {
            return false;
        }
        if (uris.isEmpty() && intent.getClipData() != null) {
            ClipData clip = intent.getClipData();
            for (int i = 0; i < clip.getItemCount(); i++) {
                Uri u = clip.getItemAt(i).getUri();
                if (u != null) uris.add(u);
            }
        }
        boolean added = false;
        for (Uri uri : uris) {
            try {
                byte[] bytes = readAll(activity, uri);
                if (bytes == null) continue;
                JSObject f = new JSObject();
                f.put("name", displayName(activity, uri));
                f.put("data", Base64.encodeToString(bytes, Base64.NO_WRAP));
                pending.add(f);
                added = true;
            } catch (Exception e) {
                Log.e(TAG, "Не удалось прочитать файл " + uri, e);
            }
        }
        // чтобы тот же Intent не обработался повторно
        intent.setAction(Intent.ACTION_MAIN);
        return added;
    }

    private static byte[] readAll(Activity activity, Uri uri) throws Exception {
        try (InputStream in = activity.getContentResolver().openInputStream(uri)) {
            if (in == null) return null;
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
                if (out.size() > MAX_BYTES) throw new Exception("Файл слишком большой");
            }
            return out.toByteArray();
        }
    }

    private static String displayName(Activity activity, Uri uri) {
        try (Cursor c = activity.getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                String name = c.getString(0);
                if (name != null) return name;
            }
        } catch (Exception ignored) {
        }
        String last = uri.getLastPathSegment();
        return last != null ? last : "statement.pdf";
    }

    @PluginMethod
    public void take(PluginCall call) {
        JSArray files = new JSArray();
        synchronized (SharedPdfPlugin.class) {
            for (JSObject f : pending) files.put(f);
            pending.clear();
        }
        JSObject ret = new JSObject();
        ret.put("files", files);
        call.resolve(ret);
    }
}
