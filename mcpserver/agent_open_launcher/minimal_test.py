# minimal_test.py - 最小化测试
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def minimal_test():
    """最小化测试"""
    print("=== 最小化测试应用启动器 ===\n")
    
    try:
        # 创建最小化配置
        config = {
            "debug_mode": False,
            "cache_enabled": False,
            "max_apps": 100,
            "scan_registry": True,
            "scan_shortcuts": False,
            "scan_desktop_entries": False,
            "scan_bin_directories": False,
            "scan_applications": False,
            "enable_incremental": False,
            "verify_executables": False,
            "launch_timeout": 30,
            "wait_for_startup": False,
            "check_already_running": False,
            "elevate_if_needed": False,
            "monitor_processes": False,
            "max_retries": 1,
            "log_launch_details": False,
            "use_shell_execute": False
        }
        
        # 导入和创建Agent
        from cross_platform_launcher_agent import create_cross_platform_launcher_agent
        
        print("1. 创建Agent实例...")
        agent = create_cross_platform_launcher_agent(config)
        print("   [OK] Agent创建成功")
        
        # 初始化
        print("\n2. 初始化Agent...")
        await agent.initialize()
        print("   [OK] 初始化完成")
        
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
            print(f"   [OK] 成功获取到 {total} 个应用")
            if apps:
                print(f"   应用: {apps}")
        else:
            print(f"   [FAIL] 获取失败: {result_data.get('message')}")
        
        print("\n=== 测试完成 ===")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 测试出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(minimal_test())
    print(f"\n测试结果: {'成功' if success else '失败'}")