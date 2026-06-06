package com.gameai;

import android.content.Context;
import android.graphics.Bitmap;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * GameAI 核心引擎 - 安卓版
 * 支持API模式和本地模式（触屏操作）
 */
public class GameAIEngine {

    private static final String TAG = "GameAIEngine";

    public enum Mode {
        API, LOCAL
    }

    public enum Backend {
        CPU, GPU, NPU
    }

    /**
     * 安卓触屏操作类型
     */
    public enum ActionType {
        TAP,           // 点击屏幕
        LONG_PRESS,    // 长按
        DOUBLE_TAP,    // 双击
        SWIPE,         // 滑动
        DRAG,          // 拖拽
        PINCH,         // 缩放（两指）
        WAIT           // 等待
    }

    /**
     * 触屏动作
     */
    public static class GameAction {
        public ActionType type;
        public int x, y;           // 坐标
        public int endX, endY;     // 滑动/拖拽终点
        public int duration;       // 持续时间(ms)
        public float scale;        // 缩放比例
        public String direction;   // 方向（上/下/左/右）

        public GameAction(ActionType type) {
            this.type = type;
        }

        @Override
        public String toString() {
            switch (type) {
                case TAP:
                    return "点击(" + x + "," + y + ")";
                case LONG_PRESS:
                    return "长按(" + x + "," + y + "," + duration + "ms)";
                case DOUBLE_TAP:
                    return "双击(" + x + "," + y + ")";
                case SWIPE:
                    return "滑动(" + x + "," + y + "→" + endX + "," + endY + ")";
                case DRAG:
                    return "拖拽(" + x + "," + y + "→" + endX + "," + endY + ")";
                case PINCH:
                    return "缩放(" + scale + ")";
                case WAIT:
                    return "等待(" + duration + "ms)";
                default:
                    return "未知操作";
            }
        }
    }

    private Context context;
    private Mode mode = Mode.API;
    private Backend backend = Backend.CPU;

    // API配置
    private String apiKey;
    private String baseUrl;
    private String model;

    // 本地模型
    private NPUEngine npuEngine;

    // OCR引擎
    private OCREngine ocrEngine;

    // 执行器
    private ExecutorService executor = Executors.newSingleThreadExecutor();
    private Handler mainHandler = new Handler(Looper.getMainLooper());

    // 状态
    private boolean isRunning = false;
    private String currentGoal;
    private List<String> stepHistory = new ArrayList<>();

    // 回调
    public interface Callback {
        void onStepUpdate(int step, int maxSteps, String message);
        void onAction(List<GameAction> actions);
        void onGoalAchieved(String message);
        void onError(String error);
    }

    private Callback callback;

    public GameAIEngine(Context context) {
        this.context = context;
        this.ocrEngine = new OCREngine(context);
    }

    public void setMode(Mode mode) {
        this.mode = mode;
    }

    public void setBackend(Backend backend) {
        this.backend = backend;
    }

    public void setCallback(Callback callback) {
        this.callback = callback;
    }

    public void configure(String apiKey, String baseUrl, String model) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.model = model;
    }

    public boolean testConnection() {
        try {
            URL url = new URL(baseUrl + "/models");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            int responseCode = conn.getResponseCode();
            return responseCode == 200;
        } catch (Exception e) {
            Log.e(TAG, "Test connection failed", e);
            return false;
        }
    }

    public void start(String goal, int maxSteps, Bitmap screenshot) {
        if (isRunning) return;

        this.currentGoal = goal;
        this.isRunning = true;
        this.stepHistory.clear();

        executor.execute(() -> {
            try {
                for (int step = 1; step <= maxSteps && isRunning; step++) {
                    // OCR识别
                    String ocrText = "";
                    if (screenshot != null) {
                        ocrText = ocrEngine.recognize(screenshot);
                    }

                    // 获取AI决策
                    String response;
                    if (mode == Mode.API) {
                        response = callAPI(goal, ocrText, step);
                    } else {
                        response = callLocal(goal, ocrText, step);
                    }

                    // 解析动作
                    List<GameAction> actions = parseActions(response);

                    // 通知UI
                    if (callback != null) {
                        final int currentStep = step;
                        mainHandler.post(() -> callback.onStepUpdate(currentStep, maxSteps,
                            "步骤 " + currentStep + ": 执行中..."));
                        mainHandler.post(() -> callback.onAction(actions));
                    }

                    // 执行动作
                    executeActions(actions);

                    // 检查是否完成
                    if (isGoalAchieved(response)) {
                        if (callback != null) {
                            mainHandler.post(() -> callback.onGoalAchieved("目标已完成！"));
                        }
                        break;
                    }

                    stepHistory.add("步骤" + step + ": " + actions.size() + "个动作");
                }
            } catch (Exception e) {
                Log.e(TAG, "Execution failed", e);
                if (callback != null) {
                    mainHandler.post(() -> callback.onError(e.getMessage()));
                }
            } finally {
                isRunning = false;
            }
        });
    }

    public void stop() {
        isRunning = false;
    }

    private String callAPI(String goal, String ocrText, int step) throws Exception {
        String prompt = buildPrompt(goal, ocrText, step);

        URL url = new URL(baseUrl + "/chat/completions");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Authorization", "Bearer " + apiKey);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);
        conn.setConnectTimeout(30000);
        conn.setReadTimeout(60000);

        JSONObject body = new JSONObject();
        body.put("model", model);
        body.put("temperature", 0.3);
        body.put("max_tokens", 1024);

        JSONArray messages = new JSONArray();
        JSONObject systemMsg = new JSONObject();
        systemMsg.put("role", "system");
        systemMsg.put("content", getSystemPrompt());
        messages.put(systemMsg);

        JSONObject userMsg = new JSONObject();
        userMsg.put("role", "user");
        userMsg.put("content", prompt);
        messages.put(userMsg);

        body.put("messages", messages);

        try (OutputStream os = conn.getOutputStream()) {
            os.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }

        StringBuilder response = new StringBuilder();
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (line.startsWith("data: ") && !line.equals("data: [DONE]")) {
                    try {
                        JSONObject chunk = new JSONObject(line.substring(6));
                        JSONArray choices = chunk.getJSONArray("choices");
                        if (choices.length() > 0) {
                            JSONObject delta = choices.getJSONObject(0).optJSONObject("delta");
                            if (delta != null && delta.has("content")) {
                                response.append(delta.getString("content"));
                            }
                        }
                    } catch (Exception ignored) {}
                }
            }
        }

        return response.toString();
    }

    private String callLocal(String goal, String ocrText, int step) throws Exception {
        if (npuEngine == null) {
            npuEngine = new NPUEngine(context, backend);
        }

        String prompt = buildPrompt(goal, ocrText, step);
        return npuEngine.generate(getSystemPrompt() + "\n\n" + prompt);
    }

    /**
     * 安卓版系统提示 - 触屏操作
     */
    private String getSystemPrompt() {
        return "你是一个安卓手机游戏AI助手。根据OCR识别的游戏画面做出触屏操作决策。\n\n" +
            "可用的触屏操作类型：\n" +
            "1. tap - 点击屏幕某个位置\n" +
            "   {\"type\": \"tap\", \"x\": 500, \"y\": 300}\n\n" +
            "2. long_press - 长按屏幕\n" +
            "   {\"type\": \"long_press\", \"x\": 500, \"y\": 300, \"duration\": 1000}\n\n" +
            "3. double_tap - 双击屏幕\n" +
            "   {\"type\": \"double_tap\", \"x\": 500, \"y\": 300}\n\n" +
            "4. swipe - 滑动（从A点滑到B点）\n" +
            "   {\"type\": \"swipe\", \"x\": 500, \"y\": 1500, \"endX\": 500, \"endY\": 500, \"duration\": 300}\n\n" +
            "5. drag - 拖拽\n" +
            "   {\"type\": \"drag\", \"x\": 200, \"y\": 300, \"endX\": 800, \"endY\": 300, \"duration\": 500}\n\n" +
            "6. pinch - 缩放\n" +
            "   {\"type\": \"pinch\", \"scale\": 1.5}  // 放大\n" +
            "   {\"type\": \"pinch\", \"scale\": 0.5}  // 缩小\n\n" +
            "7. wait - 等待\n" +
            "   {\"type\": \"wait\", \"duration\": 1000}\n\n" +
            "常见操作参考：\n" +
            "- 点击按钮：tap\n" +
            "- 上下滑动页面：swipe\n" +
            "- 长按菜单：long_press\n" +
            "- 放大缩小地图：pinch\n" +
            "- 拖拽物品：drag\n\n" +
            "必须严格以JSON格式输出：\n" +
            "{\"actions\": [{\"type\": \"...\", ...}], \"reasoning\": \"...\", \"goal_achieved\": false, \"progress\": \"...\"}";
    }

    private String buildPrompt(String goal, String ocrText, int step) {
        StringBuilder sb = new StringBuilder();
        sb.append("[目标]\n").append(goal).append("\n\n");

        if (ocrText != null && !ocrText.isEmpty()) {
            sb.append("[OCR识别的游戏画面]\n").append(ocrText).append("\n\n");
        }

        if (!stepHistory.isEmpty()) {
            sb.append("[已执行步骤]\n");
            for (int i = Math.max(0, stepHistory.size() - 5); i < stepHistory.size(); i++) {
                sb.append(stepHistory.get(i)).append("\n");
            }
        }

        return sb.toString();
    }

    /**
     * 解析触屏动作
     */
    private List<GameAction> parseActions(String response) {
        List<GameAction> actions = new ArrayList<>();

        try {
            // 提取JSON
            int start = response.indexOf("{");
            int end = response.lastIndexOf("}");
            if (start == -1 || end == -1) return actions;

            String jsonStr = response.substring(start, end + 1);
            JSONObject json = new JSONObject(jsonStr);

            JSONArray actionsArray = json.optJSONArray("actions");
            if (actionsArray == null) return actions;

            for (int i = 0; i < actionsArray.length(); i++) {
                JSONObject actionJson = actionsArray.getJSONObject(i);
                String type = actionJson.optString("type", "tap");

                GameAction action;
                switch (type) {
                    case "tap":
                        action = new GameAction(ActionType.TAP);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        break;

                    case "long_press":
                        action = new GameAction(ActionType.LONG_PRESS);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        action.duration = actionJson.optInt("duration", 1000);
                        break;

                    case "double_tap":
                        action = new GameAction(ActionType.DOUBLE_TAP);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        break;

                    case "swipe":
                        action = new GameAction(ActionType.SWIPE);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        action.endX = actionJson.optInt("endX", 0);
                        action.endY = actionJson.optInt("endY", 0);
                        action.duration = actionJson.optInt("duration", 300);
                        break;

                    case "drag":
                        action = new GameAction(ActionType.DRAG);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        action.endX = actionJson.optInt("endX", 0);
                        action.endY = actionJson.optInt("endY", 0);
                        action.duration = actionJson.optInt("duration", 500);
                        break;

                    case "pinch":
                        action = new GameAction(ActionType.PINCH);
                        action.scale = (float) actionJson.optDouble("scale", 1.0);
                        break;

                    case "wait":
                        action = new GameAction(ActionType.WAIT);
                        action.duration = actionJson.optInt("duration", 1000);
                        break;

                    default:
                        action = new GameAction(ActionType.TAP);
                        action.x = actionJson.optInt("x", 0);
                        action.y = actionJson.optInt("y", 0);
                        break;
                }

                actions.add(action);
            }
        } catch (Exception e) {
            Log.e(TAG, "Parse actions failed", e);
        }

        return actions;
    }

    private boolean isGoalAchieved(String response) {
        try {
            int start = response.indexOf("{");
            int end = response.lastIndexOf("}");
            if (start != -1 && end != -1) {
                JSONObject json = new JSONObject(response.substring(start, end + 1));
                return json.optBoolean("goal_achieved", false);
            }
        } catch (Exception ignored) {}
        return false;
    }

    /**
     * 执行触屏动作
     */
    private void executeActions(List<GameAction> actions) {
        // 通过无障碍服务执行触屏动作
        AccessibilityServiceHelper helper = AccessibilityServiceHelper.getInstance();
        if (helper == null) {
            Log.e(TAG, "AccessibilityService not available");
            return;
        }

        for (GameAction action : actions) {
            switch (action.type) {
                case TAP:
                    helper.tap(action.x, action.y);
                    break;

                case LONG_PRESS:
                    helper.longPress(action.x, action.y, action.duration);
                    break;

                case DOUBLE_TAP:
                    helper.doubleTap(action.x, action.y);
                    break;

                case SWIPE:
                    helper.swipe(action.x, action.y, action.endX, action.endY, action.duration);
                    break;

                case DRAG:
                    helper.drag(action.x, action.y, action.endX, action.endY, action.duration);
                    break;

                case PINCH:
                    helper.pinch(action.scale);
                    break;

                case WAIT:
                    try {
                        Thread.sleep(action.duration);
                    } catch (InterruptedException e) {
                        break;
                    }
                    break;
            }

            try {
                Thread.sleep(100);  // 动作间隔
            } catch (InterruptedException e) {
                break;
            }
        }
    }
}
