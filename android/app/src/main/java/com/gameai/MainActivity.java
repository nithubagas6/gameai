package com.gameai;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private EditText etApiUrl, etApiKey, etModel, etGoal;
    private Button btnStart, btnOverlay, btnAccessibility;
    private TextView tvStatus, tvLog;
    private SharedPreferences prefs;
    private boolean isServiceRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences("gameai_config", MODE_PRIVATE);

        etApiUrl = findViewById(R.id.et_api_url);
        etApiKey = findViewById(R.id.et_api_key);
        etModel = findViewById(R.id.et_model);
        etGoal = findViewById(R.id.et_goal);
        btnStart = findViewById(R.id.btn_start);
        btnOverlay = findViewById(R.id.btn_overlay);
        btnAccessibility = findViewById(R.id.btn_accessibility);
        tvStatus = findViewById(R.id.tv_status);
        tvLog = findViewById(R.id.tv_log);

        loadSettings();

        btnStart.setOnClickListener(v -> toggleService());
        btnOverlay.setOnClickListener(v -> requestOverlayPermission());
        btnAccessibility.setOnClickListener(v -> openAccessibilitySettings());
    }

    @Override
    protected void onResume() {
        super.onResume();
        updatePermissionStatus();
    }

    private void loadSettings() {
        etApiUrl.setText(prefs.getString("api_url", "https://api.deepseek.com/v1"));
        etApiKey.setText(prefs.getString("api_key", ""));
        etModel.setText(prefs.getString("model", "deepseek-chat"));
        etGoal.setText(prefs.getString("goal", ""));
    }

    private void saveSettings() {
        prefs.edit()
            .putString("api_url", etApiUrl.getText().toString().trim())
            .putString("api_key", etApiKey.getText().toString().trim())
            .putString("model", etModel.getText().toString().trim())
            .putString("goal", etGoal.getText().toString().trim())
            .apply();
    }

    private void toggleService() {
        saveSettings();
        if (isServiceRunning) {
            stopService(new Intent(this, FloatingWindowService.class));
            GameAIEngine.getInstance().stop();
            isServiceRunning = false;
            btnStart.setText(R.string.btn_start);
            tvStatus.setText(R.string.status_idle);
            tvStatus.setTextColor(0xFF4CAF50);
        } else {
            if (!Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "请先授予悬浮窗权限", Toast.LENGTH_SHORT).show();
                return;
            }
            if (etApiKey.getText().toString().trim().isEmpty()) {
                Toast.makeText(this, "请先输入API Key", Toast.LENGTH_SHORT).show();
                return;
            }
            Intent intent = new Intent(this, FloatingWindowService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent);
            } else {
                startService(intent);
            }
            isServiceRunning = true;
            btnStart.setText(R.string.btn_stop);
            tvStatus.setText(R.string.status_running);
            tvStatus.setTextColor(0xFF2196F3);
        }
    }

    private void requestOverlayPermission() {
        if (!Settings.canDrawOverlays(this)) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
            startActivityForResult(intent, 1001);
        } else {
            Toast.makeText(this, "悬浮窗权限已授予", Toast.LENGTH_SHORT).show();
        }
    }

    private void openAccessibilitySettings() {
        Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        startActivity(intent);
    }

    private void updatePermissionStatus() {
        boolean overlay = Settings.canDrawOverlays(this);
        btnOverlay.setText(overlay ? "悬浮窗权限 ✓" : "授予悬浮窗权限");
    }
}
