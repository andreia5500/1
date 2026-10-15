package com.andreia.smarthome;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.Iterator;

/**
 * Home Assistant login with username and password, the same flow the HA web
 * frontend uses: /auth/login_flow gives an authorization code, /auth/token
 * exchanges it for an access token (30 min) and a refresh token. The password
 * is never stored, only the refresh token.
 */
public final class HaAuth {

    public static final class Tokens {
        public final String accessToken;
        public final String refreshToken;
        public final long expiresAtMs;

        public Tokens(String accessToken, String refreshToken, long expiresAtMs) {
            this.accessToken = accessToken;
            this.refreshToken = refreshToken;
            this.expiresAtMs = expiresAtMs;
        }
    }

    /** Result of a login step: either tokens, or a request for a two-factor code. */
    public static final class LoginResult {
        public final Tokens tokens;
        public final String mfaFlowId;

        LoginResult(Tokens tokens, String mfaFlowId) {
            this.tokens = tokens;
            this.mfaFlowId = mfaFlowId;
        }
    }

    public static final class AuthException extends Exception {
        /** True when the server rejected the credentials (as opposed to a network error). */
        public final boolean rejected;

        AuthException(String message, boolean rejected) {
            super(message);
            this.rejected = rejected;
        }
    }

    private HaAuth() {
    }

    /** "ha.example.com/" -> "https://ha.example.com" */
    public static String normalizeUrl(String input) {
        String url = input.trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "https://" + url;
        }
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    public static String clientId(String baseUrl) {
        return baseUrl + "/";
    }

    public static LoginResult login(String baseUrl, String username, String password)
            throws AuthException {
        LoginResult result = tryLogin(baseUrl, username, password);
        String lower = username.trim().toLowerCase();
        if (result == null && !lower.equals(username)) {
            // HA usernames are lowercase; people often type them capitalised.
            result = tryLogin(baseUrl, lower, password);
        }
        if (result == null) {
            throw new AuthException("Неверный логин или пароль", true);
        }
        return result;
    }

    /** Second step when two-factor authentication is enabled for the user. */
    public static LoginResult submitMfa(String baseUrl, String flowId, String code) throws AuthException {
        try {
            JSONObject body = new JSONObject();
            body.put("client_id", clientId(baseUrl));
            body.put("code", code.trim());
            JSONObject step = postJson(baseUrl + "/auth/login_flow/" + flowId, body);
            LoginResult result = handleStep(baseUrl, step);
            if (result == null) {
                throw new AuthException("Неверный код подтверждения", true);
            }
            return result;
        } catch (JSONException e) {
            throw new AuthException("Непонятный ответ сервера: " + e.getMessage(), false);
        }
    }

    public static Tokens refresh(String baseUrl, String refreshToken) throws AuthException {
        String form = "grant_type=refresh_token"
                + "&refresh_token=" + enc(refreshToken)
                + "&client_id=" + enc(clientId(baseUrl));
        JSONObject json = postForm(baseUrl + "/auth/token", form);
        try {
            return new Tokens(json.getString("access_token"), refreshToken,
                    System.currentTimeMillis() + json.optLong("expires_in", 1800) * 1000L);
        } catch (JSONException e) {
            throw new AuthException("Непонятный ответ сервера: " + e.getMessage(), false);
        }
    }

    /** Logs out: the refresh token stops working on the server. */
    public static void revoke(String baseUrl, String refreshToken) {
        try {
            postForm(baseUrl + "/auth/token", "action=revoke&token=" + enc(refreshToken));
        } catch (AuthException ignored) {
            // Offline logout still clears the local session.
        }
    }

    /** Returns null when the credentials were rejected. */
    private static LoginResult tryLogin(String baseUrl, String username, String password)
            throws AuthException {
        try {
            JSONObject start = new JSONObject();
            start.put("client_id", clientId(baseUrl));
            start.put("handler", new org.json.JSONArray().put("homeassistant").put(JSONObject.NULL));
            start.put("redirect_uri", baseUrl + "/?auth_callback=1");
            JSONObject flow = postJson(baseUrl + "/auth/login_flow", start);
            String flowId = flow.optString("flow_id", null);
            if (flowId == null) {
                throw new AuthException("Сервер не начал вход: " + flow, false);
            }

            JSONObject creds = new JSONObject();
            creds.put("client_id", clientId(baseUrl));
            creds.put("username", username);
            creds.put("password", password);
            return handleStep(baseUrl, postJson(baseUrl + "/auth/login_flow/" + flowId, creds));
        } catch (JSONException e) {
            throw new AuthException("Непонятный ответ сервера: " + e.getMessage(), false);
        }
    }

    private static LoginResult handleStep(String baseUrl, JSONObject step) throws AuthException {
        String type = step.optString("type");
        if ("create_entry".equals(type)) {
            String code = step.optString("result", null);
            if (code == null) {
                throw new AuthException("Сервер не выдал код входа", false);
            }
            return new LoginResult(exchangeCode(baseUrl, code), null);
        }
        if ("form".equals(type)) {
            JSONObject errors = step.optJSONObject("errors");
            if (errors != null && errors.length() > 0) {
                Iterator<String> keys = errors.keys();
                String error = errors.optString(keys.next());
                if ("invalid_auth".equals(error) || "invalid_code".equals(error)) {
                    return null;
                }
                throw new AuthException("Ошибка входа: " + error, true);
            }
            if ("mfa".equals(step.optString("step_id"))) {
                return new LoginResult(null, step.optString("flow_id"));
            }
            return null;
        }
        if ("abort".equals(type)) {
            throw new AuthException("Вход прерван сервером: " + step.optString("reason"), true);
        }
        throw new AuthException("Непонятный ответ сервера: " + step, false);
    }

    private static Tokens exchangeCode(String baseUrl, String code) throws AuthException {
        String form = "grant_type=authorization_code"
                + "&code=" + enc(code)
                + "&client_id=" + enc(clientId(baseUrl));
        JSONObject json = postForm(baseUrl + "/auth/token", form);
        try {
            return new Tokens(json.getString("access_token"), json.getString("refresh_token"),
                    System.currentTimeMillis() + json.optLong("expires_in", 1800) * 1000L);
        } catch (JSONException e) {
            throw new AuthException("Непонятный ответ сервера: " + e.getMessage(), false);
        }
    }

    private static JSONObject postJson(String url, JSONObject body) throws AuthException {
        return post(url, "application/json", body.toString());
    }

    private static JSONObject postForm(String url, String form) throws AuthException {
        return post(url, "application/x-www-form-urlencoded", form);
    }

    private static JSONObject post(String url, String contentType, String body) throws AuthException {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(20000);
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", contentType);
            OutputStream os = conn.getOutputStream();
            os.write(body.getBytes("UTF-8"));
            os.close();
            int code = conn.getResponseCode();
            InputStream is = code < 400 ? conn.getInputStream() : conn.getErrorStream();
            String text = is == null ? "" : readAll(is);
            if (code == 400 || code == 401 || code == 403) {
                String detail = text;
                try {
                    JSONObject err = new JSONObject(text);
                    detail = err.optString("error_description", err.optString("message", text));
                } catch (JSONException ignored) {
                    // Not JSON.
                }
                throw new AuthException(code == 403
                        ? "Доступ запрещён (слишком много попыток входа?)"
                        : "Сервер отказал: " + detail, true);
            }
            if (code >= 300) {
                throw new AuthException("Ошибка сервера " + code, false);
            }
            if (text.isEmpty()) {
                return new JSONObject();
            }
            return new JSONObject(text);
        } catch (IOException e) {
            throw new AuthException("Нет связи с сервером: " + e.getMessage(), false);
        } catch (JSONException e) {
            throw new AuthException("Это не похоже на Home Assistant (ответ не JSON)", false);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    static String readAll(InputStream is) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        byte[] chunk = new byte[8192];
        int n;
        while ((n = is.read(chunk)) > 0) {
            buf.write(chunk, 0, n);
        }
        is.close();
        return new String(buf.toByteArray(), "UTF-8");
    }

    private static String enc(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8");
        } catch (java.io.UnsupportedEncodingException e) {
            throw new AssertionError(e);
        }
    }
}
