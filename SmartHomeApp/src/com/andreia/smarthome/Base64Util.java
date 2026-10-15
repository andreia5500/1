package com.andreia.smarthome;

/** Base64 encoder that works on every API level and on the desktop JVM. */
final class Base64Util {
    private static final char[] ALPHABET =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".toCharArray();

    private Base64Util() {
    }

    static String encode(byte[] data) {
        StringBuilder sb = new StringBuilder((data.length + 2) / 3 * 4);
        for (int i = 0; i < data.length; i += 3) {
            int b = (data[i] & 0xFF) << 16;
            if (i + 1 < data.length) b |= (data[i + 1] & 0xFF) << 8;
            if (i + 2 < data.length) b |= data[i + 2] & 0xFF;
            sb.append(ALPHABET[(b >> 18) & 63]).append(ALPHABET[(b >> 12) & 63]);
            sb.append(i + 1 < data.length ? ALPHABET[(b >> 6) & 63] : '=');
            sb.append(i + 2 < data.length ? ALPHABET[b & 63] : '=');
        }
        return sb.toString();
    }
}
