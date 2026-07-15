@echo off
chcp 65001 >nul
echo ================================================================================
echo 系统监控程序 - 测试运行脚本
echo ================================================================================
echo.

echo [1] 运行所有测试（pytest）
echo [2] 运行所有测试（unittest）
echo [3] 运行 SystemMonitor 测试
echo [4] 运行 GUI 测试
echo [5] 运行集成测试
echo [6] 运行测试并生成覆盖率报告
echo [7] 查看测试文档
echo [0] 退出
echo.

set /p choice="请选择操作 (0-7): "

if "%choice%"=="1" goto run_all_pytest
if "%choice%"=="2" goto run_all_unittest
if "%choice%"=="3" goto run_system_monitor
if "%choice%"=="4" goto run_gui
if "%choice%"=="5" goto run_integration
if "%choice%"=="6" goto run_coverage
if "%choice%"=="7" goto view_docs
if "%choice%"=="0" goto end

echo 无效选择，请重新运行脚本
pause
goto end

:run_all_pytest
echo.
echo ================================================================================
echo 运行所有测试（pytest）
echo ================================================================================
pytest tests/ -v --tb=short
goto pause_and_exit

:run_all_unittest
echo.
echo ================================================================================
echo 运行所有测试（unittest）
echo ================================================================================
python -m unittest discover tests -v
goto pause_and_exit

:run_system_monitor
echo.
echo ================================================================================
echo 运行 SystemMonitor 测试
echo ================================================================================
pytest tests/test_system_monitor.py -v
goto pause_and_exit

:run_gui
echo.
echo ================================================================================
echo 运行 GUI 测试
echo ================================================================================
pytest tests/test_gui.py -v
goto pause_and_exit

:run_integration
echo.
echo ================================================================================
echo 运行集成测试
echo ================================================================================
pytest tests/test_integration.py -v
goto pause_and_exit

:run_coverage
echo.
echo ================================================================================
echo 运行测试并生成覆盖率报告
echo ================================================================================
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html
echo.
echo HTML 报告已生成，打开 htmlcov/index.html 查看详细报告
start htmlcov\index.html
goto pause_and_exit

:view_docs
echo.
echo ================================================================================
echo 打开测试文档
echo ================================================================================
if exist "tests\README_TESTS.md" (
    start tests\README_TESTS.md
    echo 已打开测试文档
) else (
    echo 测试文档不存在
)
if exist "TEST_SUMMARY.md" (
    start TEST_SUMMARY.md
    echo 已打开测试总结
)
goto pause_and_exit

:pause_and_exit
echo.
pause
goto end

:end
echo.
echo 感谢使用！
