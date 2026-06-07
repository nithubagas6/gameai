# 📱 GameAI Android 安卓版

<div align="center">

![Android](https://img.shields.io/badge/Android-8.0%2B-green?style=flat-square&logo=android)
![API](https://img.shields.io/badge/API-触屏操作-blue?style=flat-square)
![NPU](https://img.shields.io/badge/NPU-加速-orange?style=flat-square)

**AI游戏助手 - 让AI帮你玩游戏**

</div>

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🎮 **触屏操作** | AI自动点击、滑动、长按、缩放等 |
| 📸 **截图OCR** | 自动识别游戏画面文字 |
| 🤖 **双模式** | API模式 / 本地NPU模式 / 本地服务器模式 |
| ⚡ **NPU加速** | 骁龙/天玑/麒麟芯片加速 |
| 🎯 **目标驱动** | 输入目标，AI自动完成 |
| 💬 **悬浮窗** | 游戏内随时控制 |

---

## 🎮 触屏操作类型

| 操作 | 说明 | 示例 |
|------|------|------|
| **tap** | 点击屏幕 | `{"type": "tap", "x": 500, "y": 300}` |
| **long_press** | 长按 | `{"type": "long_press", "x": 500, "y": 300, "duration": 1000}` |
| **double_tap** | 双击 | `{"type": "double_tap", "x": 500, "y": 300}` |
| **swipe** | 滑动 | `{"type": "swipe", "x": 500, "y": 1500, "endX": 500, "endY": 500}` |
| **drag** | 拖拽 | `{"type": "drag", "x": 200, "y": 300, "endX": 800, "endY": 300}` |
| **pinch** | 缩放 | `{"type": "pinch", "scale": 1.5}` |
| **wait** | 等待 | `{"type": "wait", "duration": 1000}` |

### 常见操作

- **点击按钮**: `tap`
- **上下滑动页面**: `swipe`
- **长按菜单**: `long_press`
- **放大缩小地图**: `pinch`
- **拖拽物品**: `drag`

---

## 📲 安装方法

### 方法1：直接安装

1. 下载 `GameAI.apk`
2. 允许安装未知来源应用
3. 安装并打开

### 方法2：编译源码

```bash
# 克隆仓库
git clone https://github.com/nithubagas6/gameai.git

# 用Android Studio打开 android/ 目录
# 编译运行
```

---

## 🚀 使用说明

### 1️⃣ 配置API

1. 打开应用
2. 点击设置图标
3. 选择API提供方（DeepSeek/硅基流动等）
4. 输入API Key
5. 点击测试连接

### 2️⃣ 加载本地模型（NPU模式）

1. 下载模型文件（Qwen3.5-0.8B，约1.6GB）
2. 放入手机 `Download/gameai/models/` 目录
3. 在设置中选择"本地模式"
4. 选择模型路径

### 2️⃣b 本地模型服务器模式

无需NPU，通过PC上的 llama.cpp 服务器运行本地模型：

1. 在PC上按照主项目 README 中的说明启动 llama.cpp 服务器
2. 确保安卓设备与PC在同一局域网（同一WiFi）
3. 在安卓版设置中选择"本地服务器"模式
4. 输入服务器地址（如 `http://192.168.1.100:8080`）
5. 点击测试连接

> **优势**：无需手机NPU支持，利用PC的GPU/CPU运行模型，所有安卓设备均可使用

### 3️⃣ 开始使用

1. 打开游戏
2. 点击悬浮球打开GameAI
3. 输入目标（如"击败Boss"）
4. 点击开始
5. AI会自动截图 → OCR识别 → 触屏操作

---

## ⚡ NPU加速

支持的NPU：

| 芯片 | NPU | 框架 |
|------|-----|------|
| 骁龙8 Gen2/3 | Hexagon | QNN/SNPE |
| 天玑9000/9200 | APU | NeuroPilot |
| 麒麟9000 | Da Vinci | HiAI |

---

## 🔐 权限说明

| 权限 | 用途 |
|------|------|
| 悬浮窗 | 显示控制面板 |
| 截图 | 识别游戏画面 |
| 无障碍 | 模拟触屏操作 |
| 存储 | 读取模型文件 |

---

## ❓ 常见问题

**Q: 为什么需要无障碍权限？**
A: 用于模拟触屏操作（点击、滑动、长按等）

**Q: 本地模式很慢怎么办？**
A: 确保手机支持NPU，并在设置中启用NPU加速。也可以使用本地服务器模式，通过PC运行模型。

**Q: 没有NPU的手机能用本地模型吗？**
A: 可以使用"本地服务器"模式，通过同一局域网内的PC运行 llama.cpp 服务器，无需手机NPU。

**Q: 本地服务器连接失败怎么办？**
A: 确保PC和手机在同一WiFi网络，检查PC防火墙是否放行了8080端口。

**Q: 支持哪些游戏？**
A: 理论上支持所有触屏游戏

---

## 📁 项目结构

```
android/
├── app/
│   └── src/main/
│       ├── java/com/gameai/
│       │   ├── MainActivity.java        # 主界面
│       │   ├── GameAIEngine.java        # AI引擎（触屏）
│       │   ├── FloatingWindowService.java # 悬浮窗
│       │   ├── NPUEngine.java           # NPU加速
│       │   └── OCREngine.java           # OCR识别
│       └── AndroidManifest.xml
├── build.gradle
└── README.md
```

---

## 🔗 链接

- [主项目](../README.md)
- [GitHub仓库](https://github.com/nithubagas6/gameai)
- [问题反馈](https://github.com/nithubagas6/gameai/issues)
