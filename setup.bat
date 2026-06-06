@echo off
chcp 65001 >nul
echo ==========================================
echo   Game AI - 一键安装依赖并打包
echo ==========================================
echo.

:: 检测 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 安装 API版本依赖...
pip install -r requirements_api.txt
if %errorlevel% neq 0 (
    echo [警告] 部分API依赖安装失败，继续...
)

echo.
echo [2/4] 安装 本地版本依赖...
pip install -r requirements_local.txt
if %errorlevel% neq 0 (
    echo [警告] 部分本地依赖安装失败，继续...
)

echo.
echo [3/4] 安装 PyInstaller...
pip install pyinstaller>=6.0
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo.
echo [4/4] 开始打包...
python build.py

echo.
echo ==========================================
echo   全部完成！exe 文件在 dist 目录下
echo ==========================================
pause
