package com.gameai;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.IBinder;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import java.nio.ByteBuffer;

/**
 * 悬浮窗服务
 * 提供游戏内控制界面
 */
public class FloatingWindowService extends Service {

    private static final String TAG = "FloatingWindowService";
    private static final String CHANNEL_ID = "gameai_channel";
    private static final int NOTIFICATION_ID = 1;

    private WindowManager windowManager;
    private View floatingView;
    private View controlPanel;
    private WindowManager.LayoutParams params;
    private WindowManager.LayoutParams panelParams;

    private GameAIEngine gameAIEngine;
    private MediaProjection mediaProjection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;

    private String goal;
    private String mode;
    private String apiKey;
    private String baseUrl;
    private String model;

    private TextView tvStatus;
    private EditText etGoal;
    private Button btnStart;
    private Button btnStop;

    @Override
    public void onCreate() {
        super.onCreate();

        createNotificationChannel();
        startForeground(NOTIFICATION_ID, createNotification());

        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        createFloatingView();
        createControlPanel();

        gameAIEngine = new GameAIEngine(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            goal = intent.getStringExtra("goal");
            mode = intent.getStringExtra("mode");
            apiKey = intent.getStringExtra("apiKey");
            baseUrl = intent.getStringExtra("baseUrl");
            model = intent.getStringExtra("model");

            // 配置引擎
            if ("api".equals(mode)) {
                gameAIEngine.setMode(GameAIEngine.Mode.API);
                gameAIEngine.configure(apiKey, baseUrl, model);
            } else {
                gameAIEngine.setMode(GameAIEngine.Mode.LOCAL);
            }

            // 更新UI
            if (etGoal != null && goal != null) {
                etGoal.setText(goal);
            }
        }

        return START_STICKY;
    }

    private void createFloatingView() {
        params = new WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        );
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 0;
        params.y = 100;

        floatingView = LayoutInflater.from(this).inflate(R.layout.floating_button, null);
        windowManager.addView(floatingView, params);

        // 拖动
        floatingView.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int) (event.getRawX() - initialTouchX);
                        params.y = initialY + (int) (event.getRawY() - initialTouchY);
                        windowManager.updateViewLayout(floatingView, params);
                        return true;
                }
                return false;
            }
        });

        // 点击打开控制面板
        floatingView.setOnClickListener(v -> toggleControlPanel());
    }

    private void createControlPanel() {
        panelParams = new WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        );
        panelParams.gravity = Gravity.CENTER;

        controlPanel = LayoutInflater.from(this).inflate(R.layout.control_panel, null);
        controlPanel.setVisibility(View.GONE);

        // 初始化控件
        tvStatus = controlPanel.findViewById(R.id.tv_status);
        etGoal = controlPanel.findViewById(R.id.et_goal);
        btnStart = controlPanel.findViewById(R.id.btn_start);
        btnStop = controlPanel.findViewById(R.id.btn_stop);
        Button btnClose = controlPanel.findViewById(R.id.btn_close);

        // 设置目标
        if (goal != null) {
            etGoal.setText(goal);
        }

        // 开始按钮
        btnStart.setOnClickListener(v -> startAI());

        // 停止按钮
        btnStop.setOnClickListener(v -> stopAI());

        // 关闭按钮
        btnClose.setOnClickListener(v -> {
            controlPanel.setVisibility(View.GONE);
            windowManager.updateViewLayout(controlPanel, panelParams);
        });

        windowManager.addView(controlPanel, panelParams);
    }

    private void toggleControlPanel() {
        if (controlPanel.getVisibility() == View.VISIBLE) {
            controlPanel.setVisibility(View.GONE);
        } else {
            controlPanel.setVisibility(View.VISIBLE);
        }
        windowManager.updateViewLayout(controlPanel, panelParams);
    }

    private void startAI() {
        String currentGoal = etGoal.getText().toString().trim();
        if (currentGoal.isEmpty()) {
            tvStatus.setText("请输入目标");
            return;
        }

        tvStatus.setText("运行中...");
        btnStart.setEnabled(false);
        btnStop.setEnabled(true);

        // 截图
        Bitmap screenshot = captureScreen();

        // 设置回调
        gameAIEngine.setCallback(new GameAIEngine.Callback() {
            @Override
            public void onStepUpdate(int step, int maxSteps, String message) {
                tvStatus.setText("步骤 " + step + "/" + maxSteps);
            }

            @Override
            public void onAction(java.util.List<GameAIEngine.GameAction> actions) {
                tvStatus.setText("执行 " + actions.size() + " 个动作");
            }

            @Override
            public void onGoalAchieved(String message) {
                tvStatus.setText("目标完成！");
                btnStart.setEnabled(true);
                btnStop.setEnabled(false);
            }

            @Override
            public void onError(String error) {
                tvStatus.setText("错误: " + error);
                btnStart.setEnabled(true);
                btnStop.setEnabled(false);
            }
        });

        // 启动
        gameAIEngine.start(currentGoal, 10, screenshot);
    }

    private void stopAI() {
        gameAIEngine.stop();
        tvStatus.setText("已停止");
        btnStart.setEnabled(true);
        btnStop.setEnabled(false);
    }

    private Bitmap captureScreen() {
        try {
            if (mediaProjection == null) {
                MediaProjectionManager mpManager = 
                    (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
                // 需要从Activity获取权限
                return null;
            }

            DisplayMetrics metrics = new DisplayMetrics();
            windowManager.getDefaultDisplay().getMetrics(metrics);

            int width = metrics.widthPixels;
            int height = metrics.heightPixels;

            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2);
            virtualDisplay = mediaProjection.createVirtualDisplay(
                "GameAI", width, height, metrics.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(), null, null
            );

            Image image = imageReader.acquireLatestImage();
            if (image != null) {
                Image.Plane plane = image.getPlanes()[0];
                ByteBuffer buffer = plane.getBuffer();
                int pixelStride = plane.getPixelStride();
                int rowStride = plane.getRowStride();
                int rowPadding = rowStride - pixelStride * width;

                Bitmap bitmap = Bitmap.createBitmap(
                    width + rowPadding / pixelStride, height,
                    Bitmap.Config.ARGB_8888
                );
                bitmap.copyPixelsFromBuffer(buffer);
                image.close();

                return Bitmap.createScaledBitmap(bitmap, width, height, true);
            }
        } catch (Exception e) {
            Log.e(TAG, "Screen capture failed", e);
        }
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "GameAI Service",
                NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
        }
    }

    private Notification createNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        return builder
            .setContentTitle("GameAI")
            .setContentText("AI游戏助手运行中")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .build();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();

        if (floatingView != null) {
            windowManager.removeView(floatingView);
        }
        if (controlPanel != null) {
            windowManager.removeView(controlPanel);
        }
        if (gameAIEngine != null) {
            gameAIEngine.stop();
        }
        if (virtualDisplay != null) {
            virtualDisplay.release();
        }
        if (mediaProjection != null) {
            mediaProjection.stop();
        }
    }
}
