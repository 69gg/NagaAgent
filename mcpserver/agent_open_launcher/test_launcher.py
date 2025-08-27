# test_launcher.py - 测试应用启动器功能
import asyncio
import sys
import os
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

from mcpserver.mcp_manager import get_mcp_manager

async def test_app_launcher():
    """测试应用启动器功能"""
    print("=== 测试跨平台应用启动器 ===\n")
    
    # 获取MCP管理器
    mcp_manager = get_mcp_manager()
    
    # 测试1: 获取应用列表
    print("1. 测试获取应用列表...")
    try:
        result = await mcp_manager.unified_call(
            "跨平台应用启动服务",
            "获取应用列表",
            {"limit": 10}
        )
        
        if result.get("success"):
            apps = result.get("data", {}).get("apps", [])
            total = result.get("data", {}).get("total_count", 0)
            print(f"   ✓ 成功获取到 {total} 个应用")
            print(f"   前10个应用: {apps[:5]}..." if len(apps) > 5 else f"   应用列表: {apps}")
        else:
            print(f"   ✗ 获取失败: {result.get('message')}")
    except Exception as e:
        print(f"   ✗ 异常: {e}")
    
    print()
    
    # 测试2: 启动记事本（Windows）
    print("2. 测试启动记事本...")
    try:
        result = await mcp_manager.unified_call(
            "跨平台应用启动服务",
            "启动应用",
            {"app": "notepad"}
        )
        
        if result.get("success"):
            print(f"   ✓ 启动成功")
            print(f"   进程ID: {result.get('data', {}).get('process_id')}")
        else:
            print(f"   ✗ 启动失败: {result.get('message')}")
            if "data" in result and result["data"].get("available_apps"):
                print(f"   可用应用示例: {result['data']['available_apps'][:5]}")
    except Exception as e:
        print(f"   ✗ 异常: {e}")
    
    print()
    
    # 测试3: 获取平台信息
    print("3. 测试获取平台信息...")
    try:
        result = await mcp_manager.unified_call(
            "跨平台应用启动服务",
            "获取平台信息",
            {}
        )
        
        if result.get("success"):
            platform_info = result.get("data", {})
            print(f"   ✓ 平台: {platform_info.get('os')}")
            print(f"   架构: {platform_info.get('architecture')}")
            print(f"   支持的功能: {', '.join(platform_info.get('supported_features', [])[:3])}...")
        else:
            print(f"   ✗ 获取失败: {result.get('message')}")
    except Exception as e:
        print(f"   ✗ 异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_app_launcher())