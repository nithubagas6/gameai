"""
Game AI 本地版启动器
检查依赖是否安装，提示安装，然后运行 game_ai_local.py
"""
import subprocess
import sys
import os
import shutil
import importlib

REQUIRED_PACKAGES = {
    "openai": "openai",
    "transformers": "transformers",
    "torch": "torch",
    "PIL": "Pillow",
    "accelerate": "accelerate",
}


def get_python_exe():
    """获取真实Python解释器路径（兼容PyInstaller打包环境）"""
    # PyInstaller打包后 sys.executable 指向exe自身，需要找到系统Python
    if getattr(sys, 'frozen', False):
        # 优先找 python3，再找 python
        for name in ["python3", "python", "python3.exe", "python.exe"]:
            path = shutil.which(name)
            if path and "game_ai_local" not in path.lower():
                return path
        # 最后兜底
        return "python"
    return sys.executable


def check_dependencies():
    """检查哪些依赖缺失"""
    missing = []
    for module, package in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    return missing


def main():
    print("=" * 50)
    print("  Game AI - 本地版启动器")
    print("=" * 50)

    missing = check_dependencies()
    if missing:
        print(f"\n[提示] 缺少以下依赖: {', '.join(missing)}")
        python_exe = get_python_exe()
        print(f"[提示] 使用Python: {python_exe}")
        print("[提示] 正在安装缺失依赖，请耐心等待...\n")

        try:
            ret = subprocess.call([python_exe, "-m", "pip", "install", *missing])
            if ret != 0:
                print(f"\n[错误] 依赖安装失败（返回码 {ret}）")
                print(f"请手动运行: {python_exe} -m pip install {' '.join(missing)}")
                sys.exit(1)
        except FileNotFoundError:
            print(f"\n[错误] 找不到Python解释器: {python_exe}")
            print("请确保Python已安装并添加到PATH环境变量")
            sys.exit(1)

        print("\n[提示] 依赖安装完成！\n")

    # 运行主程序（使用sys.executable获取exe所在目录，兼容PyInstaller）
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(script_dir, "game_ai_local.py")
    if not os.path.exists(script):
        print(f"[错误] 找不到主程序: {script}")
        print("请确保 game_ai_local.py 与本程序在同一目录")
        sys.exit(1)

    python_exe = get_python_exe()
    print(f"[启动] 运行 game_ai_local.py ...")
    ret = subprocess.call([python_exe, script] + sys.argv[1:])
    sys.exit(ret)


if __name__ == "__main__":
    main()
