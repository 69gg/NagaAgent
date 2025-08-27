# debug_scan.py - 调试扫描问题
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def debug_scan():
    """调试扫描问题"""
    print("=== 调试应用扫描问题 ===\n")
    
    try:
        # 检查缓存
        cache_file = "app_cache.json"
        if os.path.exists(cache_file):
            print("1. 发现缓存文件，删除中...")
            os.remove(cache_file)
            print("   [OK] 缓存文件已删除")
        
        # 创建带调试的配置
        config = {
            "debug_mode": True,
            "cache_enabled": False,
            "max_apps": 100,
            "scan_registry": True,
            "scan_shortcuts": True,
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
            "log_launch_details": True,
            "use_shell_execute": False
        }
        
        # 导入和创建Agent
        from cross_platform_launcher_agent import create_cross_platform_launcher_agent
        
        print("2. 创建Agent实例...")
        agent = create_cross_platform_launcher_agent(config)
        print("   [OK] Agent创建成功")
        
        # 检查扫描器配置
        print("\n3. 检查扫描器配置...")
        scanner = agent.scanner
        print("   扫描器配置:")
        for key, value in scanner.config.items():
            print(f"     {key}: {value}")
        
        # 强制刷新扫描
        print("\n4. 强制刷新扫描...")
        await scanner.refresh_apps()
        print("   [OK] 刷新完成")
        
        # 检查应用缓存
        print("\n5. 检查应用缓存...")
        print(f"   应用数量: {len(scanner.apps_cache)}")
        if scanner.apps_cache:
            print("   应用列表:")
            for app in scanner.apps_cache[:5]:
                print(f"     - {app.name}: {app.path}")
        else:
            print("   [WARN] 应用列表为空")
        
        # 测试获取应用列表
        print("\n6. 测试获取应用列表...")
        request = {
            "tool_name": "获取应用列表",
            "limit": 10,
            "force_refresh": True
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        print(f"   结果: {result_data.get('success', False)}")
        if result_data.get("success"):
            apps = result_data.get("data", {}).get("apps", [])
            total = result_data.get("data", {}).get("total_count", 0)
            print(f"   应用数量: {total}")
            print(f"   应用列表: {apps}")
        else:
            print(f"   失败: {result_data.get('message')}")
        
        # 测试Windows注册表扫描
        print("\n7. 测试Windows注册表扫描...")
        try:
            registry_apps = await scanner._scan_windows_registry()
            print(f"   注册表应用数量: {len(registry_apps)}")
            if registry_apps:
                print("   注册表应用:")
                for app in registry_apps[:3]:
                    print(f"     - {app.name}: {app.path}")
        except Exception as e:
            print(f"   [ERROR] 注册表扫描失败: {e}")
        
        # 测试快捷方式扫描
        print("\n8. 测试快捷方式扫描...")
        try:
            shortcut_apps = await scanner._scan_windows_shortcuts()
            print(f"   快捷方式应用数量: {len(shortcut_apps)}")
            if shortcut_apps:
                print("   快捷方式应用:")
                for app in shortcut_apps[:3]:
                    print(f"     - {app.name}: {app.path}")
        except Exception as e:
            print(f"   [ERROR] 快捷方式扫描失败: {e}")
        
        print("\n=== 调试完成 ===")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 调试出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_scan())
    print(f"\n调试结果: {'成功' if success else '失败'}")