# test_config.py - 测试配置
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cross_platform_app_scanner import get_cross_platform_scanner

def test_config():
    """测试配置"""
    print("测试配置...")
    
    # 创建扫描器
    scanner = get_cross_platform_scanner()
    
    # 打印配置
    print("当前配置:")
    for key, value in scanner.config.items():
        print(f"  {key}: {value}")
    
    # 检查必要的配置
    required_configs = ["scan_registry", "scan_shortcuts", "scan_desktop_entries", 
                       "scan_bin_directories", "scan_applications"]
    
    print("\n检查必要配置:")
    for config in required_configs:
        if config in scanner.config:
            print(f"  ✓ {config}: {scanner.config[config]}")
        else:
            print(f"  ✗ {config}: 缺失")
    
    return scanner

if __name__ == "__main__":
    scanner = test_config()