"""
打包脚本：将 game_ai_api.py 和 game_ai_local.py 打包为 exe
使用 PyInstaller 进行打包
"""
import subprocess
import sys
import os
import shutil

DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")
BUILD_DIR = os.path.join(os.path.dirname(__file__), "build")


def check_pyinstaller():
    try:
        import PyInstaller
        print(f"[打包] PyInstaller {PyInstaller.__version__} 已安装")
        return True
    except ImportError:
        print("[打包] PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])
        return True


def build_api_version():
    print("\n" + "=" * 50)
    print("  打包 API 版本 (game_ai_api.exe)")
    print("=" * 50)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "game_ai_api",
        "--console",
        "--clean",
        "--noconfirm",
        # 隐式导入
        "--hidden-import", "openai",
        "--hidden-import", "pytesseract",
        "--hidden-import", "PIL",
        "--hidden-import", "easyocr",
        "--hidden-import", "json",
        "--hidden-import", "re",
        "game_ai_api.py",
    ]
    subprocess.check_call(cmd)
    print("[打包] game_ai_api.exe 打包完成")


def build_local_version():
    print("\n" + "=" * 50)
    print("  打包 本地版本 (game_ai_local.exe)")
    print("  使用轻量启动器模式（自动检查并安装依赖）")
    print("=" * 50)

    # 本地版本依赖torch（2.5GB+），不适合打包进exe
    # 使用轻量启动器：自动检查依赖、安装缺失包、运行主脚本
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "game_ai_local",
        "--console",
        "--clean",
        "--noconfirm",
        "--hidden-import", "json",
        "--hidden-import", "re",
        "game_ai_local_launcher.py",
    ]
    subprocess.check_call(cmd)
    print("[打包] game_ai_local.exe 打包完成（轻量启动器模式）")


def main():
    print("=" * 50)
    print("  Game AI - 打包工具")
    print("=" * 50)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    check_pyinstaller()

    build_api_version()
    build_local_version()

    # 汇总
    dist = os.path.join(os.path.dirname(__file__), "dist")
    print("\n" + "=" * 50)
    print("  打包完成！")
    print("=" * 50)

    # 复制本地版主程序到dist目录（启动器需要）
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_ai_local.py")
    dst = os.path.join(dist, "game_ai_local.py")
    if os.path.exists(src) and os.path.exists(dist):
        shutil.copy2(src, dst)
        print(f"[复制] game_ai_local.py -> {dist}")

    print(f"输出目录: {dist}")
    if os.path.exists(dist):
        for f in sorted(os.listdir(dist)):
            if f.endswith((".exe", ".py")):
                size = os.path.getsize(os.path.join(dist, f))
                print(f"  {f}  ({size / 1024 / 1024:.1f} MB)")

    print("\n使用方式:")
    print(f"  API版本:  {dist}\\game_ai_api.exe --api-key sk-xxx --base-url https://api.openai.com/v1")
    print(f"  本地版本: {dist}\\game_ai_local.exe --mode local")
    print(f"  本地版本: {dist}\\game_ai_local.exe --mode api --api-key sk-xxx")
    print("\n注意:")
    print("  - game_ai_api.exe 包含所有API版本依赖，可直接运行")
    print("  - game_ai_local.exe 是轻量启动器，首次运行会自动安装缺失依赖")
    print("  - 本地版本需要 Python 环境，且需下载 Qwen 模型（首次约1GB）")


if __name__ == "__main__":
    main()
