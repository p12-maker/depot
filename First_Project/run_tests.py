"""
测试运行器
用于运行所有测试并生成报告
"""
import sys
import os
import unittest
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("系统监控程序 - 测试套件")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 发现所有测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试模块
    test_modules = [
        'tests.test_system_monitor',
        'tests.test_gui',
        'tests.test_integration',
    ]
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"✓ 加载测试模块: {module_name}")
        except Exception as e:
            print(f"✗ 加载测试模块失败 {module_name}: {e}")
    
    print("=" * 80)
    print(f"总共加载 {suite.countTestCases()} 个测试用例")
    print("=" * 80)
    
    # 运行测试
    start_time = time.time()
    
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        failfast=False,
        buffer=False,
        catchbreak=True
    )
    
    result = runner.run(suite)
    
    elapsed_time = time.time() - start_time
    
    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print(f"耗时: {elapsed_time:.2f} 秒")
    print("=" * 80)
    
    # 如果有失败或错误，打印详细信息
    if result.failures:
        print("\n失败的测试:")
        print("-" * 80)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\n错误的测试:")
        print("-" * 80)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    # 返回退出码
    exit_code = 0 if result.wasSuccessful() else 1
    print(f"\n{'✅ 所有测试通过!' if result.wasSuccessful() else '❌ 存在失败的测试'}")
    
    return exit_code


def run_specific_test(test_name):
    """运行指定的测试"""
    print(f"运行指定测试: {test_name}")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 运行指定测试
        test_name = sys.argv[1]
        exit_code = run_specific_test(test_name)
    else:
        # 运行所有测试
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
