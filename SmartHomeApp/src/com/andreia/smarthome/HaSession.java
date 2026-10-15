package com.andreia.smarthome;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;

import java.util.ArrayList;
import java.util.List;

/** Server address, tokens and favourites, kept in the app's private preferences. */
final class HaSession {

    static final String DEFAULT_URL = "https://ha.andreia.netcraze.club";

    private static HaSession instance;

    private final SharedPreferences prefs;
    private String baseUrl;
    private String accessToken;
    private String refreshToken;
    private long expiresAtMs;

    private HaSession(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences("ha", Context.MODE_PRIVATE);
        baseUrl = prefs.getString("url", null);
        accessToken = prefs.getString("access", null);
        refreshToken = prefs.getString("refresh", null);
        expiresAtMs = prefs.getLong("expires", 0);
    }

    static synchronized HaSession get(Context context) {
        if (instance == null) {
            instance = new HaSession(context);
        }
        return instance;
    }

    synchronized boolean loggedIn() {
        return baseUrl != null && refreshToken != null;
    }

    synchronized String baseUrl() {
        return baseUrl;
    }

    String lastUrl() {
        return prefs.getString("last_url", DEFAULT_URL);
    }

    String lastUser() {
        return prefs.getString("last_user", "");
    }

    synchronized void saveLogin(String url, String user, HaAuth.Tokens tokens) {
        baseUrl = url;
        prefs.edit().putString("url", url).putString("last_url", url).putString("last_user", user).apply();
        store(tokens);
    }

    private void store(HaAuth.Tokens tokens) {
        accessToken = tokens.accessToken;
        refreshToken = tokens.refreshToken;
        expiresAtMs = tokens.expiresAtMs;
        prefs.edit()
                .putString("access", accessToken)
                .putString("refresh", refreshToken)
                .putLong("expires", expiresAtMs)
                .apply();
    }

    /** Returns a working access token, refreshing it when it is about to expire. Blocking. */
    synchronized String validAccessToken() throws HaAuth.AuthException {
        if (refreshToken == null) {
            throw new HaAuth.AuthException("Не выполнен вход", true);
        }
        if (accessToken == null || System.currentTimeMillis() > expiresAtMs - 60000) {
            store(HaAuth.refresh(baseUrl, refreshToken));
        }
        return accessToken;
    }

    /** The server rejected the access token: refresh it on next use. */
    synchronized void invalidateAccessToken() {
        accessToken = null;
    }

    /** Forgets the session; the token is revoked on the server in the background. */
    void logout() {
        final String url;
        final String token;
        synchronized (this) {
            url = baseUrl;
            token = refreshToken;
            baseUrl = null;
            accessToken = null;
            refreshToken = null;
            prefs.edit().remove("url").remove("access").remove("refresh").remove("expires").apply();
        }
        if (url != null && token != null) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    HaAuth.revoke(url, token);
                }
            }).start();
        }
    }

    List<String> favorites() {
        List<String> list = new ArrayList<String>();
        try {
            JSONArray a = new JSONArray(prefs.getString("favorites", "[]"));
            for (int i = 0; i < a.length(); i++) {
                list.add(a.getString(i));
            }
        } catch (org.json.JSONException ignored) {
            // Start over with an empty list.
        }
        return list;
    }

    void setFavorites(List<String> ids) {
        prefs.edit().putString("favorites", new JSONArray(ids).toString()).apply();
    }
}
