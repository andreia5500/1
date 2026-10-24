package com.andreia.smarthome;

import android.accessibilityservice.AccessibilityService;
import android.content.ComponentName;
import android.content.Context;
import android.graphics.Rect;
import android.os.Bundle;
import android.provider.Settings;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

/**
 * Puts a pending command (e.g. "/end") into the message field of the VK chat that
 * the app has just opened. It never presses "Send" and does nothing unless a
 * command was requested in the last few seconds.
 */
public class VkInsertService extends AccessibilityService {

    private static final long TIMEOUT_MS = 20000;
    static final String VK_PACKAGE = "com.vkontakte.android";

    private static volatile String pendingText;
    private static volatile long pendingAt;

    static void request(String text) {
        pendingText = text;
        pendingAt = System.currentTimeMillis();
    }

    static boolean isEnabled(Context context) {
        String enabled = Settings.Secure.getString(context.getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        String me = new ComponentName(context, VkInsertService.class).flattenToString();
        String meShort = new ComponentName(context, VkInsertService.class).flattenToShortString();
        for (String s : enabled.split(":")) {
            if (s.equalsIgnoreCase(me) || s.equalsIgnoreCase(meShort)) return true;
        }
        return false;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        String text = pendingText;
        if (text == null) return;
        if (System.currentTimeMillis() - pendingAt > TIMEOUT_MS) {
            pendingText = null;
            return;
        }
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null || root.getPackageName() == null
                || !VK_PACKAGE.contentEquals(root.getPackageName())) {
            return;
        }
        AccessibilityNodeInfo input = lowestEditable(root, null);
        if (input == null) return; // chat not shown yet; wait for the next event
        input.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
        if (input.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) {
            Bundle sel = new Bundle();
            sel.putInt(AccessibilityNodeInfo.ACTION_ARGUMENT_SELECTION_START_INT, text.length());
            sel.putInt(AccessibilityNodeInfo.ACTION_ARGUMENT_SELECTION_END_INT, text.length());
            input.performAction(AccessibilityNodeInfo.ACTION_SET_SELECTION, sel);
            pendingText = null; // done: the user presses "Send"
        }
    }

    /** The message box is the editable field lowest on the screen. */
    private static AccessibilityNodeInfo lowestEditable(AccessibilityNodeInfo node, AccessibilityNodeInfo best) {
        if (node == null) return best;
        if (node.isEditable() && node.isVisibleToUser()) {
            if (best == null || bottom(node) > bottom(best)) best = node;
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            best = lowestEditable(node.getChild(i), best);
        }
        return best;
    }

    private static int bottom(AccessibilityNodeInfo n) {
        Rect r = new Rect();
        n.getBoundsInScreen(r);
        return r.bottom;
    }

    @Override
    public void onInterrupt() {
    }
}
