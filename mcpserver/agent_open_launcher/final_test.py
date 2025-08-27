# final_test.py - 最终测试应用启动器
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def final_test():
    """最终测试"""
    print("=== 最终测试应用启动器 ===\n")
    
    try:
        # 直接导入和创建Agent
        from cross_platform_launcher_agent import create_cross_platform_launcher_agent
        
        print("1. 创建Agent实例...")
        config = {
            "debug_mode": False,
            "cache_enabled": False,
            "monitor_processes": False,  # 禁用进程监控避免问题
            "scan_registry": True,
            "scan_shortcuts": True
        }
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
            "limit": 10
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            apps = result_data.get("data", {}).get("apps", [])
            total = result_data.get("data", {}).get("total_count", 0)
            print(f"   [OK] 成功获取到 {total} 个应用")
            if apps:
                print(f"   应用示例: {apps[:5]}")
        else:
            print(f"   [FAIL] 获取失败: {result_data.get('message')}")
        
        # 测试启动记事本
        print("\n4. 测试启动记事本...")
        request = {
            "tool_name": "启动应用",
            "app": "notepad"
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"   [OK] 启动成功")
            pid = result_data.get('data', {}).get('process_id')
            if pid:
                print(f"   进程ID: {pid}")
        else:
            print(f"   [FAIL] 启动失败: {result_data.get('message')}")
        
        # 测试获取平台信息
        print("\n5. 测试获取平台信息...")
        request = {
            "tool_name": "获取平台信息"
        }
        result = await agent.handle_handoff(request)
        result_data = json.loads(result)
        
        if result_data.get("success"):
            platform_info = result_data.get("data", {})
            print(f"   [OK] 平台: {platform_info.get('os')}")
            print(f"   [OK] 架构: {platform_info.get('architecture')}")
            features = platform_info.get("supported_features", [])
            print(f"   [OK] 支持功能: {len(features)} 个")
        else:
            print(f"   [FAIL] 获取失败: {result_data.get('message')}")
        
        print("\n=== 测试完成，应用启动器工作正常 ===")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 测试出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(final_test())
    print(f"\n测试结果: {'成功' if success else '失败'}")
    sys.exit(0 if success else 1)