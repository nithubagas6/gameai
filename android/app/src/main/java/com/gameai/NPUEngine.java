package com.gameai;

import android.content.Context;
import android.util.Log;

/**
 * NPU引擎 - 本地模型推理
 * 支持多种NPU后端：高通Hexagon、联发科APU、华为Da Vinci
 */
public class NPUEngine {

    private static final String TAG = "NPUEngine";

    private Context context;
    private GameAIEngine.Backend backend;
    private boolean isLoaded = false;

    // JNI方法
    static {
        System.loadLibrary("gameai_npu");
    }

    private native long nativeCreate(int backend);
    private native boolean nativeLoadModel(long handle, String modelPath);
    private native String nativeGenerate(long handle, String prompt, int maxTokens);
    private native void nativeDestroy(long handle);

    private long nativeHandle;

    public NPUEngine(Context context, GameAIEngine.Backend backend) {
        this.context = context;
        this.backend = backend;
        this.nativeHandle = nativeCreate(backend.ordinal());
    }

    /**
     * 加载模型
     * @param modelPath 模型文件路径
     * @return 是否成功
     */
    public boolean loadModel(String modelPath) {
        if (isLoaded) return true;

        try {
            isLoaded = nativeLoadModel(nativeHandle, modelPath);
            if (isLoaded) {
                Log.i(TAG, "Model loaded successfully: " + modelPath);
            } else {
                Log.e(TAG, "Failed to load model: " + modelPath);
            }
        } catch (Exception e) {
            Log.e(TAG, "Load model error", e);
        }

        return isLoaded;
    }

    /**
     * 生成文本
     * @param prompt 输入提示
     * @return 生成的文本
     */
    public String generate(String prompt) {
        return generate(prompt, 1024);
    }

    /**
     * 生成文本
     * @param prompt 输入提示
     * @param maxTokens 最大token数
     * @return 生成的文本
     */
    public String generate(String prompt, int maxTokens) {
        if (!isLoaded) {
            Log.e(TAG, "Model not loaded");
            return "{\"error\": \"Model not loaded\"}";
        }

        try {
            return nativeGenerate(nativeHandle, prompt, maxTokens);
        } catch (Exception e) {
            Log.e(TAG, "Generate error", e);
            return "{\"error\": \"" + e.getMessage() + "\"}";
        }
    }

    /**
     * 检查是否支持NPU
     * @return 是否支持
     */
    public static boolean isNPUSupported() {
        try {
            // 检查芯片类型
            String hardware = android.os.Build.HARDWARE;
            String soc = getSystemProperty("ro.hardware.chipname", "");

            // 高通骁龙
            if (hardware.contains("qcom") || soc.contains("sm")) {
                return true;
            }

            // 联发科
            if (hardware.contains("mt") || soc.contains("mt")) {
                return true;
            }

            // 华为麒麟
            if (hardware.contains("kirin") || soc.contains("kirin")) {
                return true;
            }

            return false;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 获取系统属性
     */
    private static String getSystemProperty(String key, String defaultValue) {
        try {
            Class<?> clazz = Class.forName("android.os.SystemProperties");
            java.lang.reflect.Method method = clazz.getMethod("get", String.class, String.class);
            return (String) method.invoke(null, key, defaultValue);
        } catch (Exception e) {
            return defaultValue;
        }
    }

    /**
     * 获取NPU信息
     * @return NPU信息字符串
     */
    public static String getNPUInfo() {
        String hardware = android.os.Build.HARDWARE;
        String soc = getSystemProperty("ro.hardware.chipname", "");

        if (hardware.contains("qcom") || soc.contains("sm")) {
            return "Qualcomm Hexagon NPU";
        } else if (hardware.contains("mt") || soc.contains("mt")) {
            return "MediaTek APU";
        } else if (hardware.contains("kirin") || soc.contains("kirin")) {
            return "Huawei Da Vinci NPU";
        }

        return "Unknown NPU";
    }

    /**
     * 释放资源
     */
    public void destroy() {
        if (nativeHandle != 0) {
            nativeDestroy(nativeHandle);
            nativeHandle = 0;
        }
        isLoaded = false;
    }

    @Override
    protected void finalize() throws Throwable {
        destroy();
        super.finalize();
    }
}
