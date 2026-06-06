<div align="center">

# 🎮 GameAI

### AI游戏自动化工具

![GitHub Stars](https://img.shields.io/github/stars/nithubagas6/gameai?style=social)
![GitHub Forks](https://img.shields.io/github/forks/nithubagas6/gameai?style=social)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow?style=flat-square&logo=python)
![Android](https://img.shields.io/badge/Android-8.0%2B-green?style=flat-square&logo=android)

**让AI帮你玩游戏 - 输入目标，自动完成**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [PC版](#-pc版) • [安卓版](#-安卓版) • [API提供方](#-api提供方) • [贡献](#-贡献)

</div>

---

## 📖 项目简介

GameAI 是一个智能游戏AI工具，能够：
- 🎯 **自动执行游戏目标**：输入目标，AI自动完成
- 🔍 **OCR识别游戏画面**：自动识别屏幕文字
- 🖥️ **Web可视化界面**：浏览器操作，简单易用
- 📱 **安卓版支持**：手机上也能用
- 🧠 **经验学习系统**：AI会学习并积累经验

<div align="center">

```
┌─────────────────────────────────────────────────────────┐
│                      GameAI 工作流程                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    📸 截图  →  🔍 OCR识别  →  🤖 AI决策  →  🎮 执行    │
│                                                         │
│    ┌─────┐    ┌─────┐     ┌─────┐     ┌─────┐         │
│    │游戏 │ →  │截图 │ →   │ AI  │ →   │操作 │         │
│    │画面 │    │识别 │     │决策 │     │执行 │         │
│    └─────┘    └─────┘     └─────┘     └─────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

</div>

---

## ✨ 功能特性

<div align="center">

| 功能 | PC版 | 安卓版 |
|------|:----:|:------:|
| 🎯 目标驱动 | ✅ | ✅ |
| 🔍 OCR识别 | ✅ | ✅ |
| 🖥️ Web界面 | ✅ | - |
| 📱 悬浮窗 | - | ✅ |
| 🎮 键盘鼠标操作 | ✅ | - |
| 👆 触屏操作 | - | ✅ |
| ⚡ NPU加速 | ✅ | ✅ |
| 🧠 经验系统 | ✅ | ✅ |
| 🤖 API模式 | ✅ | ✅ |
| 💻 本地模式 | ✅ | ✅ |

</div>

---

## 🚀 快速开始

### PC版

```bash
# 1. 克隆仓库
git clone https://github.com/nithubagas6/gameai.git
cd gameai

# 2. 安装依赖
pip install -r requirements_api.txt

# 3. 运行Web界面
python web_server.py

# 4. 打开浏览器访问 http://localhost:8080
```

### 安卓版

1. 下载 `GameAI.apk`
2. 安装并打开
3. 配置API Key
4. 开始使用

---

## 🖥️ PC版

### 系统配置要求

| 配置 | API模式 | 本地模式 |
|------|---------|----------|
| **最低配置** | Windows 10/Linux, 4GB RAM, 网络连接 | Windows 10/Linux, 8GB RAM, GTX 1060 6GB |
| **推荐配置** | Windows 11/Linux, 8GB RAM, 稳定网络 | Windows 11/Linux, 16GB RAM, RTX 3060 12GB |
| **NPU加速** | - | Intel NPU / 华为昇腾 NPU |
| **Python** | 3.8+ | 3.8+ |
| **磁盘空间** | 500MB | 2GB+（含模型） |

### 操作类型（键盘鼠标）

| 操作 | 说明 | 示例 |
|------|------|------|
| `key_press` | 单键按下 | `{"type": "key_press", "key": "space"}` |
| `key_combo` | 组合键 | `{"type": "key_combo", "keys": ["shift", "w"]}` |
| `key_hold` | 长按按键 | `{"type": "key_hold", "key": "w", "duration": 1000}` |
| `mouse_click` | 鼠标点击 | `{"type": "mouse_click", "position": "500,300"}` |
| `mouse_drag` | 鼠标拖拽 | `{"type": "mouse_drag", "start": "100,100", "end": "500,500"}` |
| `scroll` | 滚轮 | `{"type": "scroll", "direction": "down"}` |

### 常见按键参考

- **移动**: `W/A/S/D`
- **跳跃**: `space`
- **攻击**: 鼠标左键 / `J`
- **技能**: `Q/E/R/F`
- **交互**: `E/F`
- **背包**: `I/Tab`
- **地图**: `M`
- **菜单**: `Esc`

---

## 📱 安卓版

### 触屏操作类型

| 操作 | 说明 | 示例 |
|------|------|------|
| `tap` | 点击屏幕 | `{"type": "tap", "x": 500, "y": 300}` |
| `long_press` | 长按 | `{"type": "long_press", "x": 500, "y": 300, "duration": 1000}` |
| `double_tap` | 双击 | `{"type": "double_tap", "x": 500, "y": 300}` |
| `swipe` | 滑动 | `{"type": "swipe", "x": 500, "y": 1500, "endX": 500, "endY": 500}` |
| `drag` | 拖拽 | `{"type": "drag", "x": 200, "y": 300, "endX": 800, "endY": 300}` |
| `pinch` | 缩放 | `{"type": "pinch", "scale": 1.5}` |

### 系统配置要求

| 配置 | API模式 | 本地模式（NPU） |
|------|---------|-----------------|
| **最低配置** | Android 8.0, 3GB RAM, 网络 | Android 10, 6GB RAM, 骁龙888 |
| **推荐配置** | Android 12+, 4GB RAM, 5G/WiFi | Android 13+, 8GB RAM, 骁龙8 Gen2 |
| **芯片要求** | 任意 | 骁龙888+ / 天玑9000+ / 麒麟9000 |
| **NPU** | 不需要 | Hexagon / APU / Da Vinci |
| **存储空间** | 100MB | 1GB+（含模型） |
| **权限** | 悬浮窗、截图、无障碍 | 同左 + 存储读写 |

详细说明请查看 [android/README.md](android/README.md)

---

## 🤖 API提供方

| 提供方 | Base URL |
|--------|----------|
| DeepSeek | `https://api.deepseek.com/v1` |
| 硅基流动 | `https://api.siliconflow.cn/v1` |
| OpenAI | `https://api.openai.com/v1` |
| 智谱AI | `https://open.bigmodel.cn/api/paas/v4` |
| 月之暗面 | `https://api.moonshot.cn/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 百川智能 | `https://api.baichuan-ai.com/v1` |

---

## 📁 项目结构

```
gameai/
├── 📄 README.md                    # 项目说明
├── 🐍 game_ai_api.py               # PC版 - API模式
├── 🐍 game_ai_local.py             # PC版 - 本地模式
├── 🌐 web_server.py                # PC版 - Web服务器
├── 📁 static/                      # Web界面
│   ├── index.html
│   ├── style.css
│   └── app.js
├── 📱 android/                     # 安卓版
│   ├── README.md
│   └── app/src/main/
│       └── java/com/gameai/
│           ├── MainActivity.java
│           ├── GameAIEngine.java
│           ├── FloatingWindowService.java
│           ├── NPUEngine.java
│           └── OCREngine.java
├── 📋 requirements_api.txt         # API版依赖
└── 📋 requirements_local.txt       # 本地版依赖
```

---

## ⚡ NPU加速支持

| 芯片 | NPU | 框架 |
|------|-----|------|
| 骁龙8 Gen2/3 | Hexagon | QNN/SNPE |
| 天玑9000/9200 | APU | NeuroPilot |
| 麒麟9000 | Da Vinci | HiAI |

---

## 🛠️ 配置说明

### 环境变量

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export MODEL_NAME="deepseek-chat"
```

### 本地模式依赖

```bash
# 安装PyTorch（CUDA版本）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 安装transformers
pip install transformers accelerate
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件

---

## 🔗 链接

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-仓库-blue?style=for-the-badge&logo=github)](https://github.com/nithubagas6/gameai)
[![Issues](https://img.shields.io/badge/Issues-反馈-red?style=for-the-badge&logo=github)](https://github.com/nithubagas6/gameai/issues)

</div>

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star！**

</div>
