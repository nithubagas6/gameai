package com.gameai;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;

public class FloatingWindowService extends Service {

    private WindowManager windowManager;
    private View floatingView;
    private WindowManager.LayoutParams params;
    private boolean isPanelExpanded = false;
    private TextView tvStatus;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(1, buildNotification());
        createFloatingWindow();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                "gameai_service", "GameAI Service", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    private Notification buildNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, "gameai_service");
        } else {
            builder = new Notification.Builder(this);
        }
        return builder
            .setContentTitle("GameAI")
            .setContentText(getString(R.string.notification_text))
            .setSmallIcon(android.R.drawable.ic_media_play)
            .build();
    }

    private void createFloatingWindow() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        floatingView = LayoutInflater.from(this).inflate(R.layout.floating_control, null);

        params = new WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        );
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 0;
        params.y = 200;

        windowManager.addView(floatingView, params);
        setupListeners();
    }

    private void setupListeners() {
        View btnLayout = floatingView.findViewById(R.id.layout_floating_btn);
        View panelLayout = floatingView.findViewById(R.id.layout_control_panel);
        tvStatus = floatingView.findViewById(R.id.tv_floating_status);

        btnLayout.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float startTouchX, startTouchY;
            private boolean dragging = false;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        startTouchX = event.getRawX();
                        startTouchY = event.getRawY();
                        dragging = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        float dx = event.getRawX() - startTouchX;
                        float dy = event.getRawY() - startTouchY;
                        if (!dragging && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) {
                            dragging = true;
                        }
                        if (dragging) {
                            params.x = initialX + (int) dx;
                            params.y = initialY + (int) dy;
                            windowManager.updateViewLayout(floatingView, params);
                        }
                        return true;
                    case MotionEvent.ACTION_UP:
                        if (!dragging) {
                            togglePanel();
                        }
                        return true;
                }
                return false;
            }
        });

        floatingView.findViewById(R.id.btn_floating_close).setOnClickListener(v -> {
            if (isPanelExpanded) togglePanel();
        });

        floatingView.findViewById(R.id.btn_floating_start).setOnClickListener(v -> startAI());
        floatingView.findViewById(R.id.btn_floating_stop).setOnClickListener(v -> stopAI());
    }

    private void togglePanel() {
        View btnLayout = floatingView.findViewById(R.id.layout_floating_btn);
        View panelLayout = floatingView.findViewById(R.id.layout_control_panel);

        if (isPanelExpanded) {
            btnLayout.setVisibility(View.VISIBLE);
            panelLayout.setVisibility(View.GONE);
        } else {
            btnLayout.setVisibility(View.GONE);
            panelLayout.setVisibility(View.VISIBLE);
        }
        windowManager.updateViewLayout(floatingView, params);
        isPanelExpanded = !isPanelExpanded;
    }

    private void startAI() {
        SharedPreferences prefs = getSharedPreferences("gameai_config", MODE_PRIVATE);
        String apiUrl = prefs.getString("api_url", "https://api.deepseek.com/v1");
        String apiKey = prefs.getString("api_key", "");
        String model = prefs.getString("model", "deepseek-chat");
        String goal = prefs.getString("goal", "");
        String localServerUrl = prefs.getString("local_server_url", "http://192.168.1.100:8080");
        boolean localMode = prefs.getBoolean("local_mode", false);

        if (goal.isEmpty()) {
            updateStatus("请先在主界面设置游戏目标");
            return;
        }

        GameAIEngine engine = GameAIEngine.getInstance();

        if (localMode) {
            if (localServerUrl.isEmpty()) {
                updateStatus("请先在主界面配置本地服务器地址");
                return;
            }
            engine.configureLocal(localServerUrl, goal, getApplicationContext());
        } else {
            if (apiKey.isEmpty()) {
                updateStatus("请先在主界面配置API Key");
                return;
            }
            engine.configure(apiUrl, apiKey, model, goal, getApplicationContext());
        }

        engine.start(new GameAIEngine.EngineCallback() {
            @Override
            public void onStatus(String status) {
                updateStatus(status);
            }

            @Override
            public void onError(String error) {
                updateStatus("错误: " + error);
            }

            @Override
            public void onStopped() {
                updateStatus("已停止");
            }
        });
        updateStatus("AI已启动，等待操作...");
    }

    private void stopAI() {
        GameAIEngine.getInstance().stop();
        updateStatus("已停止");
    }

    private void updateStatus(String status) {
        if (tvStatus != null) {
            tvStatus.post(() -> tvStatus.setText(status));
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (floatingView != null && windowManager != null) {
            try {
                windowManager.removeView(floatingView);
            } catch (Exception ignored) {}
        }
        GameAIEngine.getInstance().stop();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
