"""
打包分发脚本：将所有文件打包为可分发的 zip 文件
其他电脑解压后运行 installer.bat 即可完成安装
"""
import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path


def ensure_build():
    """确保 exe 已构建"""
    dist = Path(__file__).parent / "dist"
    if not (dist / "game_ai_api.exe").exists():
        print("[打包] exe 未找到，先执行构建...")
        subprocess.check_call([sys.executable, "build.py"])
    else:
        print("[打包] exe 已存在，跳过构建")


def create_distribution():
    """创建分发包"""
    base = Path(__file__).parent
    dist = base / "dist"
    release_dir = base / "release"

    # 清理旧的 release 目录
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()

    # 创建分发目录结构
    release_dist = release_dir / "dist"
    release_scripts = release_dir / "scripts"
    release_dist.mkdir()
    release_scripts.mkdir()

    # 复制 exe 文件
    print("[打包] 复制 exe 文件...")
    for f in dist.glob("*.exe"):
        shutil.copy2(f, release_dist / f.name)
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.1f} MB)")

    # 复制 Python 脚本到 scripts 目录
    print("[打包] 复制 Python 脚本...")
    for name in ["game_ai_local.py", "game_ai_api.py"]:
        src = base / name
        if src.exists():
            shutil.copy2(src, release_scripts / name)
            print(f"  {name}")

    # 复制 game_ai_local.py 到 dist（启动器需要）
    local_py = base / "game_ai_local.py"
    if local_py.exists():
        shutil.copy2(local_py, release_dist / "game_ai_local.py")

    # 复制安装器
    print("[打包] 复制安装器...")
    installer = base / "installer.bat"
    if installer.exists():
        shutil.copy2(installer, release_dir / "installer.bat")
        print("  installer.bat")

    # 复制 requirements 文件
    for req in ["requirements_api.txt", "requirements_local.txt"]:
        src = base / req
        if src.exists():
            shutil.copy2(src, release_dir / req)
            print(f"  {req}")

    # 创建 README.txt
    readme_content = """Game AI - 安装说明
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
  dist\\game_ai_api.exe --api-key sk-xxx --base-url https://api.openai.com/v1

本地版本使用：
  dist\\game_ai_local.exe --mode local
  dist\\game_ai_local.exe --mode api --api-key sk-xxx

系统要求：
  - Windows 10/11 64位
  - API版本：无额外要求（已自包含）
  - 本地版本：Python 3.8+，NVIDIA GPU 推荐（支持 CUDA/NPU/CPU）

卸载：
  运行 uninstall.bat 或手动删除本目录
"""
    (release_dir / "README.txt").write_text(readme_content, encoding="utf-8")
    print("  README.txt")

    # 打包为 zip
    print("\n[打包] 创建 zip 分发包...")
    zip_name = base / "GameAI_Setup.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(release_dir):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(release_dir)
                zf.write(file_path, arcname)

    size_mb = zip_name.stat().st_size / (1024 * 1024)
    print(f"\n[完成] 分发包: {zip_name} ({size_mb:.1f} MB)")
    print(f"[完成] 解压后运行 installer.bat 即可安装")
    return zip_name


def main():
    print("=" * 50)
    print("  Game AI - 分发包打包工具")
    print("=" * 50)
    print()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ensure_build()
    zip_path = create_distribution()

    print()
    print("=" * 50)
    print("  打包完成！")
    print("=" * 50)
    print(f"  分发包: {zip_path}")
    print(f"  大小: {zip_path.stat().st_size / (1024*1024):.1f} MB")
    print()
    print("  将此 zip 发送给其他人，对方解压后运行 installer.bat 即可")


if __name__ == "__main__":
    main()
