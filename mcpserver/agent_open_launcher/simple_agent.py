# simple_agent.py - 简单通用的应用启动器Agent
import os
import json
import asyncio
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Optional, Any, List

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

from universal_scanner import UniversalAppLauncher

class SimpleAppLauncherAgent:
    """简单通用的应用启动器Agent"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.launcher = UniversalAppLauncher()
        self.initialized = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Simple App Launcher Agent 初始化完成")
    
    async def initialize(self) -> None:
        """初始化"""
        if self.initialized:
            return
        
        try:
            self.logger.info("开始初始化...")
            await self.launcher.get_apps()
            self.initialized = True
            self.logger.info("初始化完成")
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            raise
    
    async def handle_handoff(self, data: Dict) -> str:
        """处理请求"""
        self.stats["total_requests"] += 1
        request_id = data.get("request_id", f"req_{self.stats['total_requests']}")
        
        tool_name = data.get("tool_name")
        
        try:
            if not self.initialized:
                await self.initialize()
            
            if tool_name == "启动应用":
                result = await self._handle_launch_app(data, request_id)
            elif tool_name == "获取应用列表":
                result = await self._handle_get_apps(data, request_id)
            else:
                result = {
                    "success": False,
                    "status": "error",
                    "message": f"不支持的操作: {tool_name}",
                    "request_id": request_id
                }
            
            if result.get("success"):
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"处理请求失败: {e}")
            
            error_response = {
                "success": False,
                "status": "error",
                "message": f"内部错误: {str(e)}",
                "request_id": request_id
            }
            
            return json.dumps(error_response, ensure_ascii=False)
    
    async def _handle_launch_app(self, data: Dict, request_id: str) -> Dict:
        """处理启动应用"""
        app_name = data.get("app")
        
        if not app_name:
            apps = await self.launcher.get_apps()
            return {
                "success": True,
                "status": "app_selection",
                "message": f"请选择应用（共{len(apps)}个）",
                "request_id": request_id,
                "data": {
                    "apps": [app["display_name"] for app in apps[:20]],
                    "total": len(apps)
                }
            }
        
        result = await self.launcher.launch_app(app_name)
        
        return {
            "success": result["success"],
            "status": "launched" if result["success"] else "failed",
            "message": result["message"],
            "request_id": request_id,
            "data": {
                "app_name": result.get("app_name"),
                "process_id": result.get("process_id")
            }
        }
    
    async def _handle_get_apps(self, data: Dict, request_id: str) -> Dict:
        """处理获取应用列表"""
        apps = await self.launcher.get_apps()
        
        return {
            "success": True,
            "status": "apps_list",
            "message": f"找到{len(apps)}个应用",
            "request_id": request_id,
            "data": {
                "apps": [app["display_name"] for app in apps[:50]],
                "total": len(apps)
            }
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"]
        }

# 工厂函数
def create_simple_app_launcher_agent(config: Dict = None) -> SimpleAppLauncherAgent:
    """创建Agent实例"""
    return SimpleAppLauncherAgent(config)

# 测试
async def test_simple():
    """测试"""
    print("=== 测试简单Agent ===")
    
    agent = create_simple_app_launcher_agent()
    await agent.initialize()
    
    # 测试获取应用列表
    result = await agent.handle_handoff({"tool_name": "获取应用列表"})
    data = json.loads(result)
    print(f"应用数量: {data['data']['total']}")
    
    # 测试启动记事本
    result = await agent.handle_handoff({"tool_name": "启动应用", "app": "notepad"})
    data = json.loads(result)
    print(f"启动记事本: {data['success']}")

if __name__ == "__main__":
    asyncio.run(test_simple())