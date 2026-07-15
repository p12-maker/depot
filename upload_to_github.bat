@echo off
chcp 65001 >nul
echo ================================================================================
echo 上传项目到 GitHub
echo ================================================================================
echo.

cd /d "%~dp0"

echo [1/6] 检查 Git 状态...
git --version
if errorlevel 1 (
    echo ❌ Git 未找到，请确保已安装 Git
    pause
    exit /b 1
)
echo ✅ Git 已安装
echo.

echo [2/6] 初始化 Git 仓库...
if not exist ".git" (
    git init
    echo ✅ Git 仓库已初始化
) else (
    echo ℹ️  Git 仓库已存在
)
echo.

echo [3/6] 添加所有文件...
git add .
echo ✅ 文件已添加
echo.

echo [4/6] 提交更改...
git commit -m "Add system monitor project with complete test suite

- Added SystemMonitor core module
- Added GUI components with PyQt5
- Added 58 test cases (unit + integration)
- Added comprehensive documentation
- Added test utilities and configurations"
if errorlevel 1 (
    echo ℹ️  没有需要提交的更改或提交失败
) else (
    echo ✅ 提交成功
)
echo.

echo [5/6] 检查远程仓库...
git remote -v
if errorlevel 1 (
    echo ℹ️  添加远程仓库...
    git remote add origin https://github.com/p12-maker/depot.git
    echo ✅ 远程仓库已添加
) else (
    echo ℹ️  远程仓库已配置
)
echo.

echo [6/6] 推送到 GitHub...
echo ⚠️  如果遇到网络错误，请检查网络连接或配置代理
echo.

REM 尝试拉取最新代码
echo 正在拉取最新代码...
git pull --rebase origin master
if errorlevel 1 (
    echo ⚠️  拉取失败，可能是网络问题或首次推送
    echo.
    echo 尝试直接推送...
)

REM 推送到 GitHub
git push -u origin master
if errorlevel 1 (
    echo.
    echo ❌ 推送失败！
    echo.
    echo 可能的原因：
    echo 1. 网络连接问题
    echo 2. 需要配置代理
    echo 3. 认证失败
    echo.
    echo 解决方案：
    echo - 检查网络连接
    echo - 配置代理：git config --global http.proxy http://127.0.0.1:7890
    echo - 使用 SSH：git remote set-url origin git@github.com:p12-maker/depot.git
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ================================================================================
    echo ✅ 成功推送到 GitHub！
    echo ================================================================================
    echo.
    echo 项目地址：https://github.com/p12-maker/depot
    echo.
)

pause
