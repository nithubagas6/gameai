package com.gameai;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RadioGroup;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

/**
 * GameAI 主界面
 * 支持API模式和本地模式（NPU加速）
 */
public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_CODE_PERMISSIONS = 100;
    private static final int REQUEST_CODE_OVERLAY = 101;
    private static final int REQUEST_CODE_SCREEN_CAPTURE = 102;

    private EditText etGoal;
    private EditText etApiKey;
    private EditText etBaseUrl;
    private Spinner spModel;
    private Spinner spProvider;
    private RadioGroup rgMode;
    private Button btnStart;
    private Button btnStop;
    private Button btnTestConnection;
    private TextView tvStatus;

    private GameAIEngine gameAIEngine;
    private boolean isRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initViews();
        checkPermissions();
    }

    private void initViews() {
        etGoal = findViewById(R.id.et_goal);
        etApiKey = findViewById(R.id.et_api_key);
        etBaseUrl = findViewById(R.id.et_base_url);
        spModel = findViewById(R.id.sp_model);
        spProvider = findViewById(R.id.sp_provider);
        rgMode = findViewById(R.id.rg_mode);
        btnStart = findViewById(R.id.btn_start);
        btnStop = findViewById(R.id.btn_stop);
        btnTestConnection = findViewById(R.id.btn_test_connection);
        tvStatus = findViewById(R.id.tv_status);

        // 默认选择API模式
        rgMode.check(R.id.rb_api);
        onModeChanged();

        // 模式切换监听
        rgMode.setOnCheckedChangeListener((group, checkedId) -> onModeChanged());

        // 开始按钮
        btnStart.setOnClickListener(v -> startGameAI());

        // 停止按钮
        btnStop.setOnClickListener(v -> stopGameAI());

        // 测试连接
        btnTestConnection.setOnClickListener(v -> testConnection());
    }

    private void onModeChanged() {
        int selectedId = rgMode.getCheckedRadioButtonId();
        if (selectedId == R.id.rb_api) {
            // API模式：显示API配置
            findViewById(R.id.layout_api_config).setVisibility(android.view.View.VISIBLE);
            findViewById(R.id.layout_local_config).setVisibility(android.view.View.GONE);
        } else {
            // 本地模式：显示本地模型配置
            findViewById(R.id.layout_api_config).setVisibility(android.view.View.GONE);
            findViewById(R.id.layout_local_config).setVisibility(android.view.View.VISIBLE);
        }
    }

    private void checkPermissions() {
        String[] permissions = {
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.FOREGROUND_SERVICE
        };

        boolean allGranted = true;
        for (String permission : permissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                allGranted = false;
                break;
            }
        }

        if (!allGranted) {
            ActivityCompat.requestPermissions(this, permissions, REQUEST_CODE_PERMISSIONS);
        }

        // 检查悬浮窗权限
        if (!Settings.canDrawOverlays(this)) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
            startActivityForResult(intent, REQUEST_CODE_OVERLAY);
        }
    }

    private void testConnection() {
        String apiKey = etApiKey.getText().toString().trim();
        String baseUrl = etBaseUrl.getText().toString().trim();
        String model = spModel.getSelectedItem().toString();

        if (apiKey.isEmpty() || baseUrl.isEmpty()) {
            Toast.makeText(this, "请填写API Key和Base URL", Toast.LENGTH_SHORT).show();
            return;
        }

        tvStatus.setText("测试连接中...");
        btnTestConnection.setEnabled(false);

        // 在后台线程测试连接
        new Thread(() -> {
            try {
                GameAIEngine engine = new GameAIEngine(this);
                engine.configure(apiKey, baseUrl, model);
                boolean success = engine.testConnection();
                
                runOnUiThread(() -> {
                    tvStatus.setText(success ? "连接成功！" : "连接失败");
                    btnTestConnection.setEnabled(true);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    tvStatus.setText("连接失败: " + e.getMessage());
                    btnTestConnection.setEnabled(true);
                });
            }
        }).start();
    }

    private void startGameAI() {
        String goal = etGoal.getText().toString().trim();
        if (goal.isEmpty()) {
            Toast.makeText(this, "请输入目标", Toast.LENGTH_SHORT).show();
            return;
        }

        // 请求截图权限
        MediaProjectionManager projectionManager = 
            (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
        startActivityForResult(projectionManager.createScreenCaptureIntent(), 
            REQUEST_CODE_SCREEN_CAPTURE);
    }

    private void stopGameAI() {
        if (gameAIEngine != null) {
            gameAIEngine.stop();
        }
        isRunning = false;
        updateUI();
    }

    private void startForegroundService() {
        Intent serviceIntent = new Intent(this, FloatingWindowService.class);
        serviceIntent.putExtra("goal", etGoal.getText().toString());
        serviceIntent.putExtra("mode", rgMode.getCheckedRadioButtonId() == R.id.rb_api ? "api" : "local");
        serviceIntent.putExtra("apiKey", etApiKey.getText().toString());
        serviceIntent.putExtra("baseUrl", etBaseUrl.getText().toString());
        serviceIntent.putExtra("model", spModel.getSelectedItem().toString());

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }

        isRunning = true;
        updateUI();
    }

    private void updateUI() {
        btnStart.setEnabled(!isRunning);
        btnStop.setEnabled(isRunning);
        tvStatus.setText(isRunning ? "运行中..." : "就绪");
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        
        if (requestCode == REQUEST_CODE_SCREEN_CAPTURE) {
            if (resultCode == RESULT_OK && data != null) {
                // 获取截图权限成功，启动服务
                startForegroundService();
            } else {
                Toast.makeText(this, "需要截图权限才能使用", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            if (!allGranted) {
                Toast.makeText(this, "需要所有权限才能正常使用", Toast.LENGTH_LONG).show();
            }
        }
    }
}
