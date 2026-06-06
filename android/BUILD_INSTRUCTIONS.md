# GameAI Android 编译说明

## 前置条件

1. 下载并安装 Android Studio: https://developer.android.com/studio
2. 或者下载 Android SDK: https://www.androiddevtools.cn/

## 编译步骤

### 方法1: 使用Android Studio
1. 打开 Android Studio
2. 选择 "Open an existing project"
3. 选择 `android` 目录
4. 等待 Gradle 同步完成
5. 点击 Build -> Build Bundle(s) / APK(s) -> Build APK(s)
6. APK 生成在 `android/app/build/outputs/apk/debug/` 目录

### 方法2: 使用命令行
```bash
cd android
gradlew assembleDebug
```

## 安装APK

1. 将生成的APK文件传输到手机
2. 在手机上打开APK文件进行安装
3. 如果提示"未知来源"，需要在设置中允许安装

## 需要的权限

- 悬浮窗权限
- 截图权限
- 无障碍权限
- 存储权限
