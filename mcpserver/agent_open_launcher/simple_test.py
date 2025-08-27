# simple_test.py - 简单测试应用启动器
import asyncio
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

async def simple_test():
    """简单测试"""
    print("=== 简单测试应用启动器 ===\n")
    
    # 直接导入和创建Agent
    from cross_platform_launcher_agent import create_cross_platform_launcher_agent
    
    print("1. 创建Agent实例...")
    agent = create_cross_platform_launcher_agent()
    print(f"   ✓ Agent创建成功: {agent.name}")
    
    # 初始化
    print("\n2. 初始化Agent...")
    await agent.initialize()
    print("   ✓ 初始化完成")
    
    # 测试获取应用列表
    print("\n3. 测试获取应用列表...")
    result = await agent.handle_handoff({
        "tool_name": "获取应用列表",
        "limit": 5
    })
    
    result_data = json.loads(result)
    if result_data.get("success"):
        apps = result_data.get("data", {}).get("apps", [])
        total = result_data.get("data", {}).get("total_count", 0)
        print(f"   ✓ 成功获取到 {total} 个应用")
        print(f"   应用列表: {apps}")
    else:
        print(f"   ✗ 获取失败: {result_data.get('message')}")
    
    # 测试启动计算器
    print("\n4. 测试启动计算器...")
    result = await agent.handle_handoff({
        "tool_name": "启动应用",
        "app": "calc"
    })
    
    result_data = json.loads(result)
    if result_data.get("success"):
        print(f"   ✓ 启动成功")
        print(f"   进程ID: {result_data.get('data', {}).get('process_id')}")
    else:
        print(f"   ✗ 启动失败: {result_data.get('message')}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    import json
    asyncio.run(simple_test())