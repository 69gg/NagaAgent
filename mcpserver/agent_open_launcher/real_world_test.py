# real_world_test.py - 真实世界场景测试
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def real_world_test():
    """真实世界场景测试"""
    print("=== 真实世界场景测试 ===\n")
    
    try:
        # 模拟实际系统中的配置创建方式
        print("1. 模拟实际系统配置...")
        
        # 方式1: 不传配置（使用默认配置）
        print("\n2. 测试方式1: 不传配置...")
        from cross_platform_launcher_agent import create_cross_platform_launcher_agent
        agent1 = create_cross_platform_launcher_agent()
        print("   [OK] Agent1创建成功")
        
        await agent1.initialize()
        print("   [OK] Agent1初始化完成")
        
        # 检查配置
        print("\n3. 检查Agent1配置...")
        print("   scanner配置:")
        for key, value in agent1.scanner.config.items():
            if 'scan' in key:
                print(f"     {key}: {value}")
        
        # 测试扫描
        print("\n4. 测试Agent1扫描...")
        apps1 = await agent1.scanner.get_apps()
        print(f"   Agent1扫描结果: {len(apps1)} 个应用")
        
        # 方式2: 传入部分配置
        print("\n5. 测试方式2: 传入部分配置...")
        config2 = {
            "debug_mode": False,
            "cache_enabled": True,
            "max_apps": 1000
        }
        agent2 = create_cross_platform_launcher_agent(config2)
        print("   [OK] Agent2创建成功")
        
        await agent2.initialize()
        print("   [OK] Agent2初始化完成")
        
        # 检查配置
        print("\n6. 检查Agent2配置...")
        print("   scanner配置:")
        for key, value in agent2.scanner.config.items():
            if 'scan' in key:
                print(f"     {key}: {value}")
        
        # 测试扫描
        print("\n7. 测试Agent2扫描...")
        apps2 = await agent2.scanner.get_apps()
        print(f"   Agent2扫描结果: {len(apps2)} 个应用")
        
        # 方式3: 使用完整配置
        print("\n8. 测试方式3: 使用完整配置...")
        config3 = {
            "debug_mode": False,
            "cache_enabled": True,
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
        agent3 = create_cross_platform_launcher_agent(config3)
        print("   [OK] Agent3创建成功")
        
        await agent3.initialize()
        print("   [OK] Agent3初始化完成")
        
        # 测试扫描
        print("\n9. 测试Agent3扫描...")
        apps3 = await agent3.scanner.get_apps()
        print(f"   Agent3扫描结果: {len(apps3)} 个应用")
        
        # 测试通过handle_handoff调用
        print("\n10. 测试通过handle_handoff调用...")
        request = {
            "tool_name": "获取应用列表",
            "force_refresh": True
        }
        result = await agent3.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            apps = result_data.get("data", {}).get("apps", [])
            total = result_data.get("data", {}).get("total_count", 0)
            print(f"   [OK] 通过handle_handoff获取到 {total} 个应用")
            if apps:
                print(f"   应用示例: {apps[:5]}")
        else:
            print(f"   [FAIL] 通过handle_handoff获取失败: {result_data.get('message')}")
        
        # 测试启动应用
        print("\n11. 测试启动记事本...")
        request = {
            "tool_name": "启动应用",
            "app": "notepad"
        }
        result = await agent3.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"   [OK] 启动成功")
            pid = result_data.get('data', {}).get('process_id')
            if pid:
                print(f"   进程ID: {pid}")
        else:
            print(f"   [FAIL] 启动失败: {result_data.get('message')}")
        
        print("\n=== 测试完成 ===")
        
        # 总结
        print("\n总结:")
        print(f"  Agent1 (默认配置): {len(apps1)} 个应用")
        print(f"  Agent2 (部分配置): {len(apps2)} 个应用")
        print(f"  Agent3 (完整配置): {len(apps3)} 个应用")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 测试出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(real_world_test())
    print(f"\n测试结果: {'成功' if success else '失败'}")