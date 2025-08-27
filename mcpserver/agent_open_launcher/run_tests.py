# run_tests.py - 运行所有测试
import sys
import os
import unittest
import asyncio
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """运行所有测试"""
    print("🧪 开始运行应用启动器测试套件...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 发现并运行测试
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"耗时: {time.time() - start_time:.2f} 秒")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！代码质量良好。")
        return 0
    else:
        print("\n❌ 存在失败的测试，请检查代码。")
        return 1

def run_individual_test(test_module):
    """运行单个测试模块"""
    print(f"🧪 运行测试模块: {test_module}")
    
    try:
        # 导入测试模块
        module = __import__(test_module)
        
        # 运行测试
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return 0 if result.wasSuccessful() else 1
        
    except ImportError as e:
        print(f"❌ 无法导入测试模块 {test_module}: {e}")
        return 1

if __name__ == "__main__":
    start_time = time.time()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 运行指定的测试模块
        test_module = sys.argv[1]
        exit_code = run_individual_test(test_module)
    else:
        # 运行所有测试
        exit_code = run_tests()
    
    sys.exit(exit_code)