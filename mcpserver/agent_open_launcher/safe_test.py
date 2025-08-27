# safe_test.py - 安全测试应用启动器
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def safe_test():
    """安全测试"""
    print("=== 安全测试应用启动器 ===\n")
    
    try:
        # 直接导入和创建Agent
        from cross_platform_launcher_agent import create_cross_platform_launcher_agent
        
        print("1. 创建Agent实例...")
        # 使用完整配置
        config = {
            "debug_mode": False,
            "cache_enabled": False,
            "cache_ttl": 3600,
            "max_apps": 1000,
            "scan_registry": True,
            "scan_shortcuts": True,
            "scan_desktop_entries": True,
            "scan_bin_directories": True,
            "scan_applications": True,
            "enable_incremental": True,
            "verify_executables": True,
            "launch_timeout": 30,
            "wait_for_startup": True,
            "startup_wait_time": 5,
            "check_already_running": True,
            "elevate_if_needed": False,
            "monitor_processes": True,
            "max_retries": 3,
            "log_launch_details": True,
            "validate_executable": True,
            "use_shell_execute": False,
            "working_directory": None,
            "windows": {
                "use_runas_for_elevation": True,
                "create_window": True
            },
            "linux": {
                "use_terminal_for_gui": False,
                "display": None
            },
            "macos": {
                "open_with_open_command": True,
                "bundle_execution": True
            }
        }
        agent = create_cross_platform_launcher_agent(config)
        print("   ✓ Agent创建成功")
        
        # 初始化
        print("\n2. 初始化Agent...")
        await agent.initialize()
        print("   ✓ 初始化完成")
        
        # 测试获取应用列表
        print("\n3. 测试获取应用列表...")
        request = {
            "tool_name": "获取应用列表",
            "limit": 5
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            apps = result_data.get("data", {}).get("apps", [])
            total = result_data.get("data", {}).get("total_count", 0)
            print(f"   ✓ 成功获取到 {total} 个应用")
            print(f"   应用列表: {apps}")
        else:
            print(f"   ✗ 获取失败: {result_data.get('message')}")
            print(f"   错误代码: {result_data.get('error_code')}")
        
        # 测试启动计算器
        print("\n4. 测试启动计算器...")
        request = {
            "tool_name": "启动应用",
            "app": "calc"
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"   ✓ 启动成功")
            print(f"   进程ID: {result_data.get('data', {}).get('process_id')}")
        else:
            print(f"   ✗ 启动失败: {result_data.get('message')}")
            if "available_apps" in result_data.get("data", {}):
                apps = result_data["data"]["available_apps"]
                print(f"   可用应用: {apps[:5] if len(apps) > 5 else apps}")
        
        # 测试获取平台信息
        print("\n5. 测试获取平台信息...")
        request = {
            "tool_name": "获取平台信息"
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            platform_info = result_data.get("data", {})
            print(f"   ✓ 平台: {platform_info.get('os')}")
            print(f"   架构: {platform_info.get('architecture')}")
            features = platform_info.get("supported_features", [])
            print(f"   支持功能: {len(features)} 个")
        else:
            print(f"   ✗ 获取失败: {result_data.get('message')}")
        
        print("\n=== 测试完成 ===")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(safe_test())
    sys.exit(0 if success else 1)