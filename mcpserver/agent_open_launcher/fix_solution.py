# fix_solution.py - 应用启动器修复方案
import asyncio
import sys
import os
import json
from typing import List, Dict, Optional, Any

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

from simple_scanner import SimpleAppScanner, SimpleAppLauncher

class FixedAppLauncherAgent:
    """修复版应用启动器Agent"""
    
    name = "Fixed App Launcher Agent"
    version = "3.2.0"
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.launcher = SimpleAppLauncher()
        self.initialized = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }
    
    async def initialize(self) -> None:
        """初始化"""
        if self.initialized:
            return
        
        # 预扫描应用
        await self.launcher.get_apps()
        self.initialized = True
    
    async def handle_handoff(self, data: Dict) -> str:
        """处理请求"""
        self.stats["total_requests"] += 1
        request_id = data.get("request_id", f"req_{self.stats['total_requests']}")
        
        tool_name = data.get("tool_name")
        
        try:
            if tool_name == "启动应用":
                return await self._handle_launch_app(data, request_id)
            elif tool_name == "获取应用列表":
                return await self._handle_get_apps(data, request_id)
            elif tool_name == "终止应用":
                return await self._handle_terminate_app(data, request_id)
            elif tool_name == "获取运行中的应用":
                return await self._handle_get_running_apps(data, request_id)
            elif tool_name == "获取平台信息":
                return await self._handle_get_platform_info(data, request_id)
            else:
                return self._create_error_response(
                    f"未知的操作: {tool_name}",
                    request_id,
                    "UNKNOWN_TOOL"
                )
        except Exception as e:
            self.stats["failed_requests"] += 1
            return self._create_error_response(
                f"处理请求时发生错误: {str(e)}",
                request_id,
                "INTERNAL_ERROR"
            )
    
    async def _handle_launch_app(self, data: Dict, request_id: str) -> str:
        """处理启动应用"""
        app_name = data.get("app")
        args = data.get("args")
        
        if not app_name:
            # 返回应用列表供选择
            apps = await self.launcher.get_apps()
            return json.dumps({
                "success": True,
                "status": "app_selection",
                "message": f"已获取到 {len(apps)} 个可用应用。请选择要启动的应用：",
                "request_id": request_id,
                "data": {
                    "total_count": len(apps),
                    "apps": [app["display_name"] for app in apps],
                    "available_apps": [app["display_name"] for app in apps[:10]]
                }
            }, ensure_ascii=False)
        
        # 启动应用
        result = await self.launcher.launch_app(app_name)
        
        if result["success"]:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        response = {
            "success": result["success"],
            "status": "app_started" if result["success"] else "failed",
            "message": result["message"],
            "request_id": request_id,
            "data": {
                "app_name": result.get("app_name"),
                "process_id": result.get("process_id"),
                "platform": "windows"
            }
        }
        
        return json.dumps(response, ensure_ascii=False)
    
    async def _handle_get_apps(self, data: Dict, request_id: str) -> str:
        """处理获取应用列表"""
        force_refresh = data.get("force_refresh", False)
        limit = data.get("limit", 100)
        
        apps = await self.launcher.get_apps()
        
        response = {
            "success": True,
            "status": "apps_list",
            "message": f"已获取到 {len(apps)} 个可用应用",
            "request_id": request_id,
            "data": {
                "total_count": len(apps),
                "apps": [app["display_name"] for app in apps[:limit]],
                "has_more": len(apps) > limit,
                "platform": "windows",
                "last_updated": "2025-08-27T12:56:18"
            }
        }
        
        return json.dumps(response, ensure_ascii=False)
    
    async def _handle_terminate_app(self, data: Dict, request_id: str) -> str:
        """处理终止应用"""
        app_name = data.get("app")
        
        # 简化版本暂不支持终止应用
        return json.dumps({
            "success": False,
            "status": "not_implemented",
            "message": "终止应用功能暂未实现",
            "request_id": request_id,
            "data": {}
        }, ensure_ascii=False)
    
    async def _handle_get_running_apps(self, data: Dict, request_id: str) -> str:
        """处理获取运行中的应用"""
        # 简化版本暂不支持获取运行应用
        return json.dumps({
            "success": False,
            "status": "not_implemented",
            "message": "获取运行应用功能暂未实现",
            "request_id": request_id,
            "data": {}
        }, ensure_ascii=False)
    
    async def _handle_get_platform_info(self, data: Dict, request_id: str) -> str:
        """处理获取平台信息"""
        import platform
        
        response = {
            "success": True,
            "status": "platform_info",
            "message": "平台信息获取成功",
            "request_id": request_id,
            "data": {
                "os": "windows",
                "os_version": platform.platform(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "supported_features": [
                    "应用扫描",
                    "应用启动",
                    "应用列表"
                ]
            }
        }
        
        return json.dumps(response, ensure_ascii=False)
    
    def _create_error_response(self, message: str, request_id: str, error_code: str) -> str:
        """创建错误响应"""
        response = {
            "success": False,
            "status": "error",
            "message": message,
            "request_id": request_id,
            "error_code": error_code,
            "data": {
                "platform": "windows"
            }
        }
        
        return json.dumps(response, ensure_ascii=False)

# 创建修复版的Agent
def create_fixed_app_launcher_agent(config: Dict = None) -> FixedAppLauncherAgent:
    """创建修复版应用启动Agent"""
    return FixedAppLauncherAgent(config)

# 测试修复版
async def test_fixed():
    """测试修复版"""
    print("=== 测试修复版应用启动器 ===\n")
    
    # 创建Agent
    agent = create_fixed_app_launcher_agent()
    await agent.initialize()
    
    # 测试获取应用列表
    print("1. 测试获取应用列表...")
    result = await agent.handle_handoff({"tool_name": "获取应用列表"})
    data = json.loads(result)
    print(f"   结果: {data['success']}")
    print(f"   应用数量: {data['data']['total_count']}")
    print(f"   应用示例: {data['data']['apps'][:5]}")
    
    # 测试启动应用
    print("\n2. 测试启动记事本...")
    result = await agent.handle_handoff({"tool_name": "启动应用", "app": "notepad"})
    data = json.loads(result)
    print(f"   结果: {data['success']}")
    print(f"   消息: {data['message']}")
    if data['success']:
        print(f"   进程ID: {data['data']['process_id']}")
    
    # 测试启动ToDesk
    print("\n3. 测试启动ToDesk...")
    result = await agent.handle_handoff({"tool_name": "启动应用", "app": "ToDesk"})
    data = json.loads(result)
    print(f"   结果: {data['success']}")
    print(f"   消息: {data['message']}")
    
    print("\n=== 修复版测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_fixed())