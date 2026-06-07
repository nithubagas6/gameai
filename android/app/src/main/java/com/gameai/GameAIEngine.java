package com.gameai;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okio.BufferedSource;

public class GameAIEngine {

    private static GameAIEngine instance;
    private static GameAIAccessibilityService accessibilityService;

    public interface EngineCallback {
        void onStatus(String status);
        void onError(String error);
        void onStopped();
    }

    private OkHttpClient client;
    private String apiUrl, apiKey, model, goal;
    private boolean useLocalModel = false;
    private String localServerUrl;
    private boolean running = false;
    private Thread workerThread;
    private ExperienceManager experienceManager;
    private EngineCallback callback;

    private static final String SYSTEM_PROMPT =
        "你是一个游戏AI助手，正在帮助玩家通过触屏操作完成游戏目标。\n\n" +
        "触屏操作类型：\n" +
        "1. tap: 点击屏幕 - {\"type\":\"tap\",\"x\":500,\"y\":300}\n" +
        "2. long_press: 长按 - {\"type\":\"long_press\",\"x\":500,\"y\":300,\"duration\":1000}\n" +
        "3. double_tap: 双击 - {\"type\":\"double_tap\",\"x\":500,\"y\":300}\n" +
        "4. swipe: 滑动 - {\"type\":\"swipe\",\"x\":500,\"y\":1500,\"endX\":500,\"endY\":500}\n\n" +
        "必须严格以JSON格式输出：\n" +
        "{\"actions\":[{\"type\":\"tap\",\"x\":500,\"y\":300}],\"confidence\":0.9,\"reasoning\":\"推理过程\",\"goal_achieved\":false}\n\n" +
        "规则：\n" +
        "1. x,y是屏幕坐标\n" +
        "2. 可以输出多个动作按顺序执行\n" +
        "3. reasoning说明为什么执行这些操作\n" +
        "4. goal_achieved标记目标是否已完成";

    public static GameAIEngine getInstance() {
        if (instance == null) {
            instance = new GameAIEngine();
        }
        return instance;
    }

    public static void setAccessibilityService(GameAIAccessibilityService service) {
        accessibilityService = service;
    }

    public void configure(String apiUrl, String apiKey, String model, String goal, Context context) {
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
        this.model = model;
        this.goal = goal;
        this.useLocalModel = false;
        this.experienceManager = new ExperienceManager(context);
        this.client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();
    }

    /**
     * Configure for local model mode (Qwen3.5-0.8B via llama.cpp server).
     * The local server exposes an OpenAI-compatible /v1/chat/completions endpoint.
     */
    public void configureLocal(String localServerUrl, String goal, Context context) {
        this.localServerUrl = localServerUrl;
        this.model = "local";
        this.goal = goal;
        this.useLocalModel = true;
        this.experienceManager = new ExperienceManager(context);
        this.client = new OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(300, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .build();
    }

    public void start(EngineCallback cb) {
        if (running) return;
        this.callback = cb;
        this.running = true;
        workerThread = new Thread(this::runLoop);
        workerThread.start();
    }

    public void stop() {
        running = false;
        if (workerThread != null) {
            workerThread.interrupt();
            workerThread = null;
        }
    }

    public boolean isRunning() {
        return running;
    }

    private void runLoop() {
        int step = 0;
        while (running) {
            step++;
            try {
                notifyStatus("步骤" + step + ": 读取屏幕...");

                // 1. Read screen content
                String screenContent = readScreen();
                notifyStatus("步骤" + step + ": 屏幕内容已获取 (" + screenContent.length() + "字)");

                // 2. Call AI API
                notifyStatus("步骤" + step + ": 请求AI分析...");
                String aiResponse = callApi(screenContent);

                // 3. Parse response
                JSONObject parsed = parseResponse(aiResponse);
                String reasoning = parsed.optString("reasoning", "");
                boolean goalAchieved = parsed.optBoolean("goal_achieved", false);
                JSONArray actions = parsed.optJSONArray("actions");

                notifyStatus("步骤" + step + ": " + reasoning.substring(0, Math.min(50, reasoning.length())));

                // 4. Execute actions
                if (actions != null && accessibilityService != null) {
                    for (int i = 0; i < actions.length() && running; i++) {
                        JSONObject action = actions.getJSONObject(i);
                        executeAction(action);
                        Thread.sleep(300);
                    }
                } else if (accessibilityService == null) {
                    notifyStatus("无障碍服务未连接，请在设置中开启");
                }

                // 5. Save experience
                experienceManager.add(goal, screenContent, reasoning);

                // 6. Check goal
                if (goalAchieved) {
                    notifyStatus("目标已达成!");
                    break;
                }

                // 7. Wait
                Thread.sleep(1500);

            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                notifyError(e.getMessage());
                try { Thread.sleep(3000); } catch (InterruptedException ie) { break; }
            }
        }
        running = false;
        if (callback != null) callback.onStopped();
    }

    private String readScreen() {
        if (accessibilityService != null) {
            String content = accessibilityService.getScreenContent();
            if (content != null && !content.isEmpty()) {
                return content;
            }
        }
        return "无法读取屏幕内容";
    }

    private String callApi(String screenContent) throws IOException {
        String userMsg = "[当前目标]\n" + goal + "\n\n[游戏屏幕内容]\n" + screenContent;

        String recentExp = experienceManager.getRecent(3);
        if (!recentExp.isEmpty()) {
            userMsg += "\n\n[历史经验]\n" + recentExp;
        }

        JSONObject body = new JSONObject();
        try {
            body.put("model", model);
            body.put("temperature", 0.3);
            body.put("max_tokens", 512);
            body.put("stream", true);

            JSONArray messages = new JSONArray();
            JSONObject sysMsg = new JSONObject();
            sysMsg.put("role", "system");
            sysMsg.put("content", SYSTEM_PROMPT);
            messages.put(sysMsg);

            JSONObject userMsgObj = new JSONObject();
            userMsgObj.put("role", "user");
            userMsgObj.put("content", userMsg);
            messages.put(userMsgObj);

            body.put("messages", messages);
        } catch (JSONException e) {
            throw new IOException("JSON构造失败: " + e.getMessage());
        }

        // Build URL based on mode
        String requestUrl;
        Request.Builder requestBuilder = new Request.Builder()
            .addHeader("Content-Type", "application/json")
            .post(RequestBody.create(body.toString(), MediaType.parse("application/json")));

        if (useLocalModel) {
            // Local mode: llama.cpp server with OpenAI-compatible API
            requestUrl = localServerUrl + "/v1/chat/completions";
        } else {
            // API mode: external cloud API
            requestUrl = apiUrl + "/chat/completions";
            requestBuilder.addHeader("Authorization", "Bearer " + apiKey);
        }

        Request request = requestBuilder.url(requestUrl).build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("API请求失败: HTTP " + response.code());
            }

            StringBuilder result = new StringBuilder();
            BufferedSource source = response.body().source();
            while (!source.exhausted()) {
                String line = source.readUtf8Line();
                if (line == null) break;
                if (line.startsWith("data: ") && !line.equals("data: [DONE]")) {
                    try {
                        JSONObject chunk = new JSONObject(line.substring(6));
                        String delta = chunk.getJSONArray("choices")
                            .getJSONObject(0)
                            .getJSONObject("delta")
                            .optString("content", "");
                        result.append(delta);
                    } catch (JSONException ignored) {}
                }
            }
            return result.toString();
        }
    }

    private JSONObject parseResponse(String raw) {
        String jsonStr = raw;
        // Try to extract JSON from response
        int start = raw.indexOf("{");
        int end = raw.lastIndexOf("}");
        if (start != -1 && end != -1 && end > start) {
            jsonStr = raw.substring(start, end + 1);
        }
        try {
            return new JSONObject(jsonStr);
        } catch (JSONException e) {
            JSONObject fallback = new JSONObject();
            try {
                fallback.put("actions", new JSONArray());
                fallback.put("reasoning", "解析失败: " + raw.substring(0, Math.min(100, raw.length())));
                fallback.put("goal_achieved", false);
            } catch (JSONException ignored) {}
            return fallback;
        }
    }

    private void executeAction(JSONObject action) throws JSONException, InterruptedException {
        if (accessibilityService == null) return;

        String type = action.optString("type", "tap");
        int x = action.optInt("x", 0);
        int y = action.optInt("y", 0);

        switch (type) {
            case "tap":
                accessibilityService.performTap(x, y);
                break;
            case "double_tap":
                accessibilityService.performTap(x, y);
                Thread.sleep(100);
                accessibilityService.performTap(x, y);
                break;
            case "long_press":
                long duration = action.optLong("duration", 1000);
                accessibilityService.performLongPress(x, y, duration);
                break;
            case "swipe":
                int endX = action.optInt("endX", x);
                int endY = action.optInt("endY", y);
                accessibilityService.performSwipe(x, y, endX, endY);
                break;
            default:
                notifyStatus("未知操作类型: " + type);
        }
    }

    private void notifyStatus(String status) {
        if (callback != null) callback.onStatus(status);
    }

    private void notifyError(String error) {
        if (callback != null) callback.onError(error);
    }
}
