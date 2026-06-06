package com.gameai;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

public class GameAIAccessibilityService extends AccessibilityService {

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Not used - we read screen on demand
    }

    @Override
    public void onInterrupt() {
        // Not used
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        GameAIEngine.setAccessibilityService(this);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        GameAIEngine.setAccessibilityService(null);
    }

    public String getScreenContent() {
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root == null) return "";
            StringBuilder sb = new StringBuilder();
            traverseNode(root, sb, 0);
            return sb.toString().trim();
        } catch (Exception e) {
            return "读取屏幕失败: " + e.getMessage();
        }
    }

    private void traverseNode(AccessibilityNodeInfo node, StringBuilder sb, int depth) {
        if (node == null || depth > 15) return;

        CharSequence text = node.getText();
        CharSequence desc = node.getContentDescription();

        if (text != null && text.length() > 0) {
            sb.append(text.toString()).append("\n");
        }
        if (desc != null && desc.length() > 0) {
            sb.append("[").append(desc.toString()).append("]\n");
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            try {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) {
                    traverseNode(child, sb, depth + 1);
                    child.recycle();
                }
            } catch (Exception ignored) {}
        }
    }

    public void performTap(int x, int y) {
        try {
            GestureDescription.Builder builder = new GestureDescription.Builder();
            Path path = new Path();
            path.moveTo(x, y);
            builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 100));
            dispatchGesture(builder.build(), null, null);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void performLongPress(int x, int y, long duration) {
        try {
            GestureDescription.Builder builder = new GestureDescription.Builder();
            Path path = new Path();
            path.moveTo(x, y);
            builder.addStroke(new GestureDescription.StrokeDescription(path, 0, Math.max(duration, 500)));
            dispatchGesture(builder.build(), null, null);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void performSwipe(int startX, int startY, int endX, int endY) {
        try {
            GestureDescription.Builder builder = new GestureDescription.Builder();
            Path path = new Path();
            path.moveTo(startX, startY);
            path.lineTo(endX, endY);
            builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 500));
            dispatchGesture(builder.build(), null, null);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
