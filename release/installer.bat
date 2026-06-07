@echo off
chcp 65001 >nul 2>nul
setlocal enabledelayedexpansion

title Game AI 安装器

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║           Game AI - 一键安装程序               ║
echo  ║     支持 API 版本和本地版本（Qwen3.5）       ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ============================================================
::  检测安装目录
:: ============================================================
set "INSTALL_DIR=%~dp0"
set "SCRIPTS_DIR=%INSTALL_DIR%scripts"
set "SHORTCUT_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Game AI"

:: ============================================================
::  步骤1: 检测 Python
:: ============================================================
echo [1/5] 检测 Python 环境...
set "PYTHON_CMD="

:: 检查 PATH 中的 python
where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do (
        set "PYVER=%%v"
    )
    echo       发现 Python !PYVER!
    set "PYTHON_CMD=python"
    goto :python_found
)

:: 检查 py launcher
where py >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do (
        set "PYVER=%%v"
    )
    echo       发现 Python !PYVER! (via py launcher)
    set "PYTHON_CMD=py"
    goto :python_found
)

:: Python 未找到
echo.
echo  [警告] 未检测到 Python！
echo.
echo  本地版本需要 Python 3.10+ 才能运行。
echo  API版本（game_ai_api.exe）不需要 Python，可直接使用。
echo.
set /p "INSTALL_PYTHON=是否自动下载安装 Python 3.11？(Y/N): "
if /i "!INSTALL_PYTHON!"=="Y" (
    echo.
    echo  正在下载 Python 3.11...
    echo  请在浏览器中完成下载并安装。
    echo  安装时请务必勾选 "Add Python to PATH"！
    echo.
    start "" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    echo  安装完成后请重新运行本安装器。
    pause
    exit /b 0
) else (
    echo.
    echo  跳过 Python 安装。本地版本将不可用。
    echo  API版本仍可正常使用。
    goto :skip_local_deps
)

:python_found
echo       Python 路径: !PYTHON_CMD!

:: ============================================================
::  步骤2: 安装 API 版本依赖
:: ============================================================
echo.
echo [2/5] 安装 API 版本依赖...
!PYTHON_CMD! -m pip install --upgrade pip -q 2>nul
!PYTHON_CMD! -m pip install openai pytesseract Pillow easyocr -q
if %errorlevel% equ 0 (
    echo       API 版本依赖安装完成
) else (
    echo       [警告] 部分依赖安装失败，API版本可能不完整
)

:: ============================================================
::  步骤3: 安装本地版本依赖
:: ============================================================
echo.
echo [3/5] 安装本地版本依赖（需要下载较大文件，请耐心等待）...

:: 检测是否有 NVIDIA GPU
echo       检测 GPU...
!PYTHON_CMD! -c "import torch; print('CUDA:', torch.cuda.is_available())" >nul 2>nul
if %errorlevel% neq 0 (
    echo       安装 PyTorch（CUDA 12.4版本）...
    !PYTHON_CMD! -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 -q
) else (
    echo       PyTorch 已安装
)

echo       安装 transformers 5.2.x（Qwen3.5 官方推荐）...
!PYTHON_CMD! -m pip install "transformers>=5.2.0,<5.3.0" accelerate Pillow "qwen-vl-utils>=0.0.14" -q
if %errorlevel% equ 0 (
    echo       本地版本依赖安装完成
) else (
    echo       [警告] 部分依赖安装失败
)

:skip_local_deps

:: ============================================================
::  步骤4: 预下载 Qwen 模型（可选）
:: ============================================================
echo.
echo [4/5] Qwen3.5-0.8B 模型下载...
echo       模型约 1.6GB，首次运行时会自动下载。
echo       是否现在预下载？(Y/N)
set /p "DOWNLOAD_MODEL="
if /i "!DOWNLOAD_MODEL!"=="Y" (
    echo       正在下载模型，请耐心等待...
    !PYTHON_CMD! -c "from transformers import AutoModelForImageTextToText, AutoProcessor; AutoModelForImageTextToText.from_pretrained('Qwen/Qwen3.5-0.8B', trust_remote_code=True); AutoProcessor.from_pretrained('Qwen/Qwen3.5-0.8B', trust_remote_code=True); print('模型下载完成')" 2>nul
    if %errorlevel% equ 0 (
        echo       模型下载完成
    ) else (
        echo       [提示] 模型下载失败或被跳过，首次运行时会自动下载
    )
) else (
    echo       跳过模型下载，首次运行时会自动下载
)

:: ============================================================
::  步骤5: 创建快捷方式和开始菜单
:: ============================================================
echo.
echo [5/5] 创建快捷方式...

:: 创建开始菜单文件夹
if not exist "%SHORTCUT_DIR%" mkdir "%SHORTCUT_DIR%"

:: 创建桌面快捷方式（API版本 - 直接可运行）
echo       创建桌面快捷方式...

:: 使用 PowerShell 创建快捷方式
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Game AI (API版).lnk'); ^
     $s.TargetPath = '%INSTALL_DIR%dist\game_ai_api.exe'; ^
     $s.WorkingDirectory = '%INSTALL_DIR%dist'; ^
     $s.Description = 'Game AI - API版本'; ^
     $s.Save()"

if exist "%SCRIPTS_DIR%\game_ai_local.py" (
    powershell -Command ^
        "$ws = New-Object -ComObject WScript.Shell; ^
         $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Game AI (本地版).lnk'); ^
         $s.TargetPath = '%INSTALL_DIR%dist\game_ai_local.exe'; ^
         $s.WorkingDirectory = '%INSTALL_DIR%dist'; ^
         $s.Description = 'Game AI - 本地版本'; ^
         $s.Save()"
)

:: 创建开始菜单快捷方式
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('%SHORTCUT_DIR%\Game AI (API版).lnk'); ^
     $s.TargetPath = '%INSTALL_DIR%dist\game_ai_api.exe'; ^
     $s.WorkingDirectory = '%INSTALL_DIR%dist'; ^
     $s.Save()"

if exist "%SCRIPTS_DIR%\game_ai_local.py" (
    powershell -Command ^
        "$ws = New-Object -ComObject WScript.Shell; ^
         $s = $ws.CreateShortcut('%SHORTCUT_DIR%\Game AI (本地版).lnk'); ^
         $s.TargetPath = '%INSTALL_DIR%dist\game_ai_local.exe'; ^
         $s.WorkingDirectory = '%INSTALL_DIR%dist'; ^
         $s.Save()"
)

:: 创建卸载器
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo echo 正在卸载 Game AI...
    echo del /q "%USERPROFILE%\Desktop\Game AI*.lnk" 2^>nul
    echo rmdir /s /q "%SHORTCUT_DIR%" 2^>nul
    echo echo 卸载完成！
    echo pause
) > "%INSTALL_DIR%uninstall.bat"

echo       快捷方式创建完成

:: ============================================================
::  完成
:: ============================================================
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║             安装完成！                          ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║                                                ║
echo  ║  桌面快捷方式已创建：                          ║
echo  ║    - Game AI (API版)    双击直接运行           ║
echo  ║    - Game AI (本地版)   双击运行               ║
echo  ║                                                ║
echo  ║  API版本使用：                                 ║
echo  ║    game_ai_api.exe --api-key sk-xxx            ║
echo  ║                                                ║
echo  ║  本地版本使用：                                ║
echo  ║    game_ai_local.exe --mode local              ║
echo  ║    game_ai_local.exe --mode api --api-key xxx  ║
echo  ║                                                ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
