package com.andreia.smarthome;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

public class LoginActivity extends Activity {

    private EditText url;
    private EditText username;
    private EditText password;
    private EditText code;
    private TextView codeLabel;
    private TextView error;
    private Button login;
    private View progress;

    /** Set when the server asked for a two-factor code. */
    private String mfaFlowId;
    private String mfaUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        HaSession session = HaSession.get(this);
        if (session.loggedIn()) {
            openMain();
            return;
        }
        setContentView(R.layout.activity_login);
        url = (EditText) findViewById(R.id.url);
        username = (EditText) findViewById(R.id.username);
        password = (EditText) findViewById(R.id.password);
        code = (EditText) findViewById(R.id.code);
        codeLabel = (TextView) findViewById(R.id.code_label);
        error = (TextView) findViewById(R.id.error);
        login = (Button) findViewById(R.id.login);
        progress = findViewById(R.id.progress);

        url.setText(session.lastUrl());
        username.setText(session.lastUser());

        login.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                submit();
            }
        });
    }

    private void submit() {
        final String base = HaAuth.normalizeUrl(url.getText().toString());
        final String user = username.getText().toString().trim();
        final String pass = password.getText().toString();
        final String mfaCode = code.getText().toString();
        final String flowId = base.equals(mfaUrl) ? mfaFlowId : null;
        if (user.isEmpty() || pass.isEmpty()) {
            showError("Введите логин и пароль");
            return;
        }
        if (flowId != null && mfaCode.trim().isEmpty()) {
            showError("Введите код подтверждения");
            return;
        }
        setBusy(true);
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final HaAuth.LoginResult result = flowId != null
                            ? HaAuth.submitMfa(base, flowId, mfaCode)
                            : HaAuth.login(base, user, pass);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            setBusy(false);
                            if (result.tokens != null) {
                                HaSession.get(LoginActivity.this).saveLogin(base, user, result.tokens);
                                openMain();
                            } else {
                                mfaFlowId = result.mfaFlowId;
                                mfaUrl = base;
                                codeLabel.setVisibility(View.VISIBLE);
                                code.setVisibility(View.VISIBLE);
                                code.requestFocus();
                                showError("Введите код из приложения-аутентификатора");
                            }
                        }
                    });
                } catch (final HaAuth.AuthException e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            setBusy(false);
                            if (flowId != null) {
                                // A failed code ends the flow; the next attempt starts over.
                                mfaFlowId = null;
                                code.setText("");
                                codeLabel.setVisibility(View.GONE);
                                code.setVisibility(View.GONE);
                            }
                            showError(e.getMessage());
                        }
                    });
                }
            }
        }).start();
    }

    private void setBusy(boolean busy) {
        login.setEnabled(!busy);
        login.setText(busy ? "Вход…" : "Войти");
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        if (busy) {
            error.setVisibility(View.GONE);
        }
    }

    private void showError(String message) {
        error.setText(message);
        error.setVisibility(View.VISIBLE);
    }

    private void openMain() {
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }
}
