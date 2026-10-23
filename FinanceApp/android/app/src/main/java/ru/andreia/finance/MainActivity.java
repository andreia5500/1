package ru.andreia.finance;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SharedPdfPlugin.class);
        super.onCreate(savedInstanceState);
        SharedPdfPlugin.collect(this, getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (SharedPdfPlugin.collect(this, intent) && getBridge() != null) {
            // сообщаем веб-части, что пришли новые файлы
            getBridge().triggerWindowJSEvent("sharedpdf");
        }
    }
}
