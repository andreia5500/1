package com.andreia.smarthome;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.nio.charset.Charset;
import java.security.SecureRandom;
import java.util.concurrent.atomic.AtomicBoolean;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;

/**
 * Minimal RFC 6455 WebSocket client (text frames only), enough for the
 * Home Assistant API. No external libraries.
 */
public final class WebSocketClient {

    public interface Listener {
        void onText(String text);

        /** Called once when the connection ends for any reason. */
        void onClosed(String reason);
    }

    private static final Charset UTF8 = Charset.forName("UTF-8");
    /** HA answers our pings, so a silent socket for this long is dead. */
    private static final int READ_TIMEOUT_MS = 60000;

    private final URI uri;
    private final Listener listener;
    private final SecureRandom random = new SecureRandom();

    private Socket socket;
    private OutputStream out;
    private volatile boolean closed;
    private final AtomicBoolean notified = new AtomicBoolean();

    public WebSocketClient(URI uri, Listener listener) {
        this.uri = uri;
        this.listener = listener;
    }

    /** Opens the connection and starts the reader thread. Blocking; call off the UI thread. */
    public void connect() throws IOException {
        boolean secure = "wss".equals(uri.getScheme());
        String host = uri.getHost();
        int port = uri.getPort() != -1 ? uri.getPort() : (secure ? 443 : 80);

        Socket s;
        if (secure) {
            Socket plain = new Socket();
            plain.connect(new InetSocketAddress(host, port), 15000);
            // Layering over a connected socket with the host name enables SNI.
            SSLSocket ssl = (SSLSocket) ((SSLSocketFactory) SSLSocketFactory.getDefault())
                    .createSocket(plain, host, port, true);
            ssl.startHandshake();
            HostnameVerifier verifier = HttpsURLConnection.getDefaultHostnameVerifier();
            if (!verifier.verify(host, ssl.getSession())) {
                ssl.close();
                throw new IOException("Сертификат сервера не подходит для " + host);
            }
            s = ssl;
        } else {
            s = new Socket();
            s.connect(new InetSocketAddress(host, port), 15000);
        }
        s.setSoTimeout(READ_TIMEOUT_MS);
        s.setTcpNoDelay(true);
        socket = s;
        out = s.getOutputStream();
        final InputStream in = new BufferedInputStream(s.getInputStream());

        byte[] keyBytes = new byte[16];
        random.nextBytes(keyBytes);
        String key = Base64Util.encode(keyBytes);
        String path = uri.getRawPath() == null || uri.getRawPath().isEmpty() ? "/" : uri.getRawPath();
        String hostHeader = uri.getPort() == -1 ? host : host + ":" + port;
        String request = "GET " + path + " HTTP/1.1\r\n"
                + "Host: " + hostHeader + "\r\n"
                + "Upgrade: websocket\r\n"
                + "Connection: Upgrade\r\n"
                + "Sec-WebSocket-Key: " + key + "\r\n"
                + "Sec-WebSocket-Version: 13\r\n"
                + "User-Agent: SmartHome-Android\r\n"
                + "\r\n";
        out.write(request.getBytes(UTF8));
        out.flush();

        String status = readHeaders(in);
        if (!status.startsWith("HTTP/1.1 101")) {
            s.close();
            throw new IOException("Сервер отклонил WebSocket: " + status);
        }

        Thread reader = new Thread(new Runnable() {
            @Override
            public void run() {
                readLoop(in);
            }
        }, "ws-reader");
        reader.setDaemon(true);
        reader.start();
    }

    public synchronized void send(String text) throws IOException {
        if (closed || out == null) {
            throw new IOException("closed");
        }
        writeFrame(0x1, text.getBytes(UTF8));
    }

    public void close() {
        if (closed) {
            return;
        }
        try {
            synchronized (this) {
                if (out != null) {
                    writeFrame(0x8, new byte[0]);
                }
            }
        } catch (IOException ignored) {
            // Closing anyway.
        }
        shutdown("closed by client");
    }

    private void shutdown(String reason) {
        closed = true;
        try {
            if (socket != null) {
                socket.close();
            }
        } catch (IOException ignored) {
            // Nothing to do.
        }
        if (notified.compareAndSet(false, true)) {
            listener.onClosed(reason);
        }
    }

    private static String readHeaders(InputStream in) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        int last4 = 0;
        while (last4 != 0x0D0A0D0A) {
            int b = in.read();
            if (b < 0) {
                throw new EOFException("Соединение закрыто при подключении");
            }
            buf.write(b);
            last4 = (last4 << 8) | b;
            if (buf.size() > 16384) {
                throw new IOException("Слишком длинный ответ сервера");
            }
        }
        String headers = new String(buf.toByteArray(), UTF8);
        int eol = headers.indexOf("\r\n");
        return eol > 0 ? headers.substring(0, eol) : headers;
    }

    private void readLoop(InputStream raw) {
        DataInputStream in = new DataInputStream(raw);
        ByteArrayOutputStream message = new ByteArrayOutputStream();
        String reason = "connection closed";
        try {
            while (!closed) {
                int b0 = in.readUnsignedByte();
                int b1 = in.readUnsignedByte();
                boolean fin = (b0 & 0x80) != 0;
                int opcode = b0 & 0x0F;
                boolean masked = (b1 & 0x80) != 0;
                long len = b1 & 0x7F;
                if (len == 126) {
                    len = in.readUnsignedShort();
                } else if (len == 127) {
                    len = in.readLong();
                }
                if (len < 0 || len > 64L * 1024 * 1024) {
                    throw new IOException("frame too large: " + len);
                }
                byte[] mask = null;
                if (masked) {
                    mask = new byte[4];
                    in.readFully(mask);
                }
                byte[] payload = new byte[(int) len];
                in.readFully(payload);
                if (mask != null) {
                    for (int i = 0; i < payload.length; i++) {
                        payload[i] ^= mask[i % 4];
                    }
                }
                switch (opcode) {
                    case 0x0: // continuation
                    case 0x1: // text
                    case 0x2: // binary (not expected, treated as text)
                        message.write(payload);
                        if (fin) {
                            String text = new String(message.toByteArray(), UTF8);
                            message.reset();
                            listener.onText(text);
                        }
                        break;
                    case 0x8:
                        shutdown("closed by server");
                        return;
                    case 0x9:
                        synchronized (this) {
                            writeFrame(0xA, payload);
                        }
                        break;
                    default:
                        // 0xA pong and unknown control frames are ignored.
                        break;
                }
            }
        } catch (IOException e) {
            if (!closed) {
                reason = e.getMessage() != null ? e.getMessage() : e.toString();
            }
        } catch (RuntimeException e) {
            reason = e.toString();
        }
        shutdown(reason);
    }

    private void writeFrame(int opcode, byte[] payload) throws IOException {
        ByteArrayOutputStream frame = new ByteArrayOutputStream(payload.length + 14);
        frame.write(0x80 | opcode);
        int len = payload.length;
        if (len < 126) {
            frame.write(0x80 | len);
        } else if (len <= 0xFFFF) {
            frame.write(0x80 | 126);
            frame.write(len >>> 8);
            frame.write(len);
        } else {
            frame.write(0x80 | 127);
            for (int i = 7; i >= 0; i--) {
                frame.write((int) ((long) len >>> (8 * i)));
            }
        }
        byte[] mask = new byte[4];
        random.nextBytes(mask);
        frame.write(mask);
        for (int i = 0; i < len; i++) {
            frame.write(payload[i] ^ mask[i % 4]);
        }
        out.write(frame.toByteArray());
        out.flush();
    }
}
