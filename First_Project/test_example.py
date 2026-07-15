"""
快速测试示例 - 演示如何运行测试
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("系统监控程序 - 测试运行指南")
print("=" * 80)
print()

print("📋 可用的测试模块:")
print("  1. tests.test_system_monitor  - SystemMonitor 单元测试")
print("  2. tests.test_gui             - GUI 组件单元测试")
print("  3. tests.test_integration     - 集成测试")
print()

print("=" * 80)
print("🚀 运行测试的方法:")
print("=" * 80)
print()

print("方法 1: 使用 pytest（推荐）")
print("-" * 80)
print("# 运行所有测试")
print("pytest tests/ -v")
print()
print("# 运行指定模块")
print("pytest tests/test_system_monitor.py -v")
print()
print("# 运行带覆盖率报告")
print("pytest tests/ --cov=. --cov-report=term-missing")
print()

print("方法 2: 使用 unittest")
print("-" * 80)
print("# 运行所有测试")
print("python -m unittest discover tests -v")
print()
print("# 运行指定模块")
print("python -m unittest tests.test_system_monitor -v")
print()

print("方法 3: 使用自定义运行器")
print("-" * 80)
print("# 运行所有测试")
print("python run_tests.py")
print()
print("# 运行指定模块")
print("python run_tests.py tests.test_system_monitor")
print()

print("=" * 80)
print("📊 查看测试覆盖率")
print("=" * 80)
print()
print("# 生成 HTML 覆盖率报告")
print("pytest tests/ --cov=. --cov-report=html")
print("# 然后打开 htmlcov/index.html 查看报告")
print()

print("=" * 80)
print("💡 提示")
print("=" * 80)
print()
print("• GUI 测试需要显示服务器（Windows 上通常没问题）")
print("• 某些测试会被自动跳过如果 PyQt5 不可用")
print("• 所有外部依赖都已被 Mock，不需要真实硬件")
print("• 详细文档请查看: tests/README_TESTS.md")
print()

print("=" * 80)
print("现在尝试运行一个简单测试:")
print("=" * 80)
print()

# 尝试运行一个简单的测试
try:
    import unittest
    from tests.test_system_monitor import TestUtilityFunctions
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtilityFunctions)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    if result.wasSuccessful():
        print("✅ 示例测试通过！您可以开始运行完整的测试套件。")
    else:
        print("❌ 示例测试失败，请检查错误信息。")
        
except Exception as e:
    print(f"⚠️  运行示例测试时出错: {e}")
    print("但这不影响其他测试，您可以尝试运行其他测试模块。")

print()
print("=" * 80)
