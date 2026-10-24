package com.andreia.smarthome;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.text.InputType;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

/**
 * Commands to HA through the VK group when the internet to the house is blocked
 * but VK still works. HA's VK Notify integration turns "/end" etc. into
 * vk_notify_command events, which the automations listen to.
 *
 * VK does not let other apps send a message on the user's behalf without its own
 * API access, so the app opens the group chat in the VK app and, if the user has
 * enabled {@link VkInsertService}, types the command there; the user presses Send.
 * Without it the command is on the clipboard to paste.
 */
final class VkCommands {

    /** {command, label}, matching the vk_notify_command automations in HA. */
    static final String[][] COMMANDS = {
            {"end", "Поставить на охрану"},
            {"home", "Снять с охраны"},
            {"hotdom", "Греть дом"},
            {"t", "Температура"},
            {"cam", "Фото с камер"},
            {"ibp", "Питание (ИБП)"},
            {"poliv", "Полив газона"},
            {"polivoff", "Выключить полив"},
            {"start", "Список команд"},
    };

    private static final String VK_PACKAGE = VkInsertService.VK_PACKAGE;

    private final Activity activity;

    VkCommands(Activity activity) {
        this.activity = activity;
    }

    private String group() {
        return activity.getSharedPreferences("ha", Context.MODE_PRIVATE).getString("vk_group", null);
    }

    /** Copies "/command" and opens the group chat in VK. Asks for the group once. */
    void send(final String command) {
        if (group() == null) {
            askGroup(new Runnable() {
                @Override
                public void run() {
                    send(command);
                }
            });
            return;
        }
        final String text = "/" + command;
        ClipboardManager cm = (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("Команда", text)); // fallback: paste by hand

        final boolean auto = VkInsertService.isEnabled(activity);
        if (!auto && !activity.getSharedPreferences("ha", Context.MODE_PRIVATE)
                .getBoolean("vk_auto_declined", false)) {
            offerAutoInsert(new Runnable() {
                @Override
                public void run() {
                    openChat(text, false);
                }
            });
            return;
        }
        openChat(text, auto);
    }

    private void openChat(String text, boolean auto) {
        if (auto) {
            VkInsertService.request(text);
        }
        Uri chat = Uri.parse("https://vk.me/" + group());
        Intent open = new Intent(Intent.ACTION_VIEW, chat);
        open.setPackage(VK_PACKAGE);
        try {
            activity.startActivity(open);
        } catch (android.content.ActivityNotFoundException e) {
            try {
                activity.startActivity(new Intent(Intent.ACTION_VIEW, chat)); // VK not installed: browser
            } catch (android.content.ActivityNotFoundException e2) {
                Toast.makeText(activity, "Не найдено приложение ВКонтакте", Toast.LENGTH_LONG).show();
                return;
            }
        }
        Toast.makeText(activity, auto
                        ? "Команда " + text + " будет вписана в чат — нажмите «Отправить»"
                        : "Команда " + text + " скопирована — вставьте в чат и отправьте",
                Toast.LENGTH_LONG).show();
    }

    /** One-time offer to let the app type the command into VK itself. */
    private void offerAutoInsert(final Runnable manual) {
        new AlertDialog.Builder(activity)
                .setTitle("Вписывать команду автоматически?")
                .setMessage("Приложение может само вписать команду в поле сообщения в чате группы — "
                        + "вам останется нажать «Отправить».\n\nДля этого включите «Умный дом: команды в ВК» "
                        + "в Настройках → Специальные возможности (на Xiaomi: «Скачанные приложения»). "
                        + "Разрешение работает только внутри ВКонтакте и сразу после нажатия кнопки команды.")
                .setPositiveButton("Открыть настройки", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        activity.startActivity(new Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS));
                    }
                })
                .setNegativeButton("Вставлю сам", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        activity.getSharedPreferences("ha", Context.MODE_PRIVATE).edit()
                                .putBoolean("vk_auto_declined", true).apply();
                        manual.run();
                    }
                })
                .show();
    }

    /** "https://vk.com/hotdom" / "club123" / "hotdom" -> "hotdom" or "club123". */
    static String parseGroup(String input) {
        String s = input.trim();
        s = s.replaceFirst("^https?://", "").replaceFirst("^(m\\.)?vk\\.(com|ru|me)/", "");
        int q = s.indexOf('?');
        if (q >= 0) s = s.substring(0, q);
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        if (s.startsWith("public")) s = "club" + s.substring(6);
        if (s.matches("-?\\d+")) s = "club" + s.replace("-", "");
        return s.matches("[A-Za-z0-9_.]+") ? s : null;
    }

    void askGroup(final Runnable then) {
        final EditText input = new EditText(activity);
        input.setHint("vk.com/имя_группы");
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        String current = group();
        if (current != null) input.setText("vk.com/" + current);
        FrameLayout box = new FrameLayout(activity);
        int pad = Math.round(24 * activity.getResources().getDisplayMetrics().density);
        box.setPadding(pad, pad / 3, pad, 0);
        box.addView(input);
        new AlertDialog.Builder(activity)
                .setTitle("Группа ВК для команд")
                .setMessage("Ссылка на группу, в чат которой вы пишете команды (/end, /home…). "
                        + "Её видно в ВК: группа → «Поделиться» → «Скопировать ссылку».")
                .setView(box)
                .setPositiveButton("Сохранить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        String g = parseGroup(input.getText().toString());
                        if (g == null) {
                            Toast.makeText(activity, "Не похоже на ссылку на группу", Toast.LENGTH_LONG).show();
                            return;
                        }
                        activity.getSharedPreferences("ha", Context.MODE_PRIVATE).edit()
                                .putString("vk_group", g).apply();
                        if (then != null) then.run();
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }
}
