Game AI - 安装说明
====================

目录结构：
  dist/           - 可执行文件和运行时文件
  scripts/        - Python 源码
  installer.bat   - 一键安装器（推荐）
  requirements_*  - 依赖列表

快速开始：
  1. 双击运行 installer.bat 进行一键安装
  2. 或者直接运行 dist/game_ai_api.exe（API版本，无需安装）

API版本使用：
  dist\game_ai_api.exe --api-key sk-xxx --base-url https://api.openai.com/v1

本地版本使用：
  dist\game_ai_local.exe --mode local
  dist\game_ai_local.exe --mode api --api-key sk-xxx

系统要求：
  - Windows 10/11 64位
  - API版本：无额外要求（已自包含）
  - 本地版本：Python 3.8+，NVIDIA GPU 推荐（支持 CUDA/NPU/CPU）

卸载：
  运行 uninstall.bat 或手动删除本目录
