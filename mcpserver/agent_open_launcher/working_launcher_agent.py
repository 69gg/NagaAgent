# working_launcher_agent.py - 工作版应用启动器Agent
import os
import json
import asyncio
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Optional, Any, List

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

# 导入简化版扫描器（工作版本）
from simple_scanner import SimpleAppLauncher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkingAppLauncherAgent:
    """工作版应用启动器Agent - 使用简化版扫描器"""
    
    name = "Working App Launcher Agent"
    version = "3.2.0"
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.launcher = SimpleAppLauncher()
        self.initialized = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_error": None,
            "startup_time": None,
            "platform": "windows"
        }
        
        # 初始化日志
        self._setup_logging()
        
        logger.info(f"{self.name} v{self.version} 初始化完成")
    
    def _setup_logging(self) -> None:
        """设置日志配置"""
        log_level = self.config.get("log_level", "INFO")
        logger.setLevel(getattr(logging, log_level.upper()))
    
    async def initialize(self) -> None:
        """初始化"""
        if self.initialized:
            return
        
        try:
            logger.info("开始异步初始化...")
            
            # 预扫描应用
            await self.launcher.get_apps()
            
            self.stats["startup_time"] = datetime.now()
            self.initialized = True
            
            logger.info("Agent初始化完成")
            
        except Exception as e:
            logger.error(f"Agent初始化失败: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def handle_handoff(self, data: Dict) -> str:
        """处理MCP handoff请求"""
        self.stats["total_requests"] += 1
        request_id = data.get("request_id", f"req_{self.stats['total_requests']}")
        
        tool_name = data.get("tool_name")
        
        logger.info(f"收到请求 [{request_id}]: {tool_name}")
        
        try:
            # 确保已初始化
            if not self.initialized:
                await self.initialize()
            
            # 处理请求
            if tool_name == "启动应用":
                result = await self._handle_launch_app(data, request_id)
            elif tool_name == "获取应用列表":
                result = await self._handle_get_apps(data, request_id)
            elif tool_name == "终止应用":
                result = await self._handle_terminate_app(data, request_id)
            elif tool_name == "获取运行中的应用":
                result = await self._handle_get_running_apps(data, request_id)
            elif tool_name == "获取平台信息":
                result = await self._handle_get_platform_info(data, request_id)
            elif tool_name == "获取启动历史":
                result = await self._handle_get_launch_history(data, request_id)
            elif tool_name == "获取统计信息":
                result = await self._handle_get_stats(data, request_id)
            else:
                result = {
                    "success": False,
                    "status": "error",
                    "message": f"未知的操作: {tool_name}",
                    "request_id": request_id,
                    "data": {}
                }
            
            # 更新统计
            if result.get("success", False):
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
                self.stats["last_error"] = result.get("message", "Unknown error")
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.stats["last_error"] = str(e)
            
            logger.error(f"处理请求失败 [{request_id}]: {e}")
            logger.debug(traceback.format_exc())
            
            return self._create_error_response(
                f"处理请求时发生内部错误: {str(e)}",
                request_id,
                "INTERNAL_ERROR",
                details=traceback.format_exc() if self.config.get("debug_mode") else None
            )
    
    async def _handle_launch_app(self, data: Dict, request_id: str) -> Dict:
        """处理启动应用"""
        app_name = data.get("app")
        args = data.get("args")
        
        if not app_name:
            # 返回应用列表供选择
            apps = await self.launcher.get_apps()
            return {
                "success": True,
                "status": "app_selection",
                "message": f"已获取到 {len(apps)} 个可用应用。请选择要启动的应用：",
                "request_id": request_id,
                "data": {
                    "total_count": len(apps),
                    "apps": [app["display_name"] for app in apps],
                    "available_apps": [app["display_name"] for app in apps[:10]],
                    "platform": "windows",
                    "usage_format": {
                        "tool_name": "启动应用",
                        "app": "应用名称（必填，从上述列表中选择）",
                        "args": "启动参数（可选）"
                    },
                    "example": {
                        "tool_name": "启动应用",
                        "app": "Chrome浏览器",
                        "args": "--incognito"
                    }
                }
            }
        
        # 启动应用
        result = await self.launcher.launch_app(app_name)
        
        response = {
            "success": result["success"],
            "status": "app_started" if result["success"] else "failed",
            "message": result["message"],
            "request_id": request_id,
            "data": {
                "app_name": result.get("app_name"),
                "process_id": result.get("process_id"),
                "platform": "windows",
                "duration": 0
            }
        }
        
        return response
    
    async def _handle_get_apps(self, data: Dict, request_id: str) -> Dict:
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
                "last_updated": datetime.now().isoformat()
            }
        }
        
        return response
    
    async def _handle_terminate_app(self, data: Dict, request_id: str) -> Dict:
        """处理终止应用"""
        app_name = data.get("app")
        
        # 简化版本暂不支持终止应用
        return {
            "success": False,
            "status": "not_implemented",
            "message": "终止应用功能暂未实现",
            "request_id": request_id,
            "data": {
                "platform": "windows",
                "suggestion": "可以通过任务管理器手动终止应用"
            }
        }
    
    async def _handle_get_running_apps(self, data: Dict, request_id: str) -> Dict:
        """处理获取运行中的应用"""
        # 简化版本暂不支持获取运行应用
        return {
            "success": False,
            "status": "not_implemented",
            "message": "获取运行应用功能暂未实现",
            "request_id": request_id,
            "data": {
                "platform": "windows",
                "suggestion": "可以通过任务管理器查看运行的应用"
            }
        }
    
    async def _handle_get_platform_info(self, data: Dict, request_id: str) -> Dict:
        """处理获取平台信息"""
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
                    "应用列表",
                    "跨平台支持（简化版）"
                ]
            }
        }
        
        return response
    
    async def _handle_get_launch_history(self, data: Dict, request_id: str) -> Dict:
        """处理获取启动历史"""
        # 简化版本暂不支持历史记录
        return {
            "success": False,
            "status": "not_implemented",
            "message": "启动历史功能暂未实现",
            "request_id": request_id,
            "data": {
                "platform": "windows"
            }
        }
    
    async def _handle_get_stats(self, data: Dict, request_id: str) -> Dict:
        """处理获取统计信息"""
        response = {
            "success": True,
            "status": "stats",
            "message": "统计信息获取成功",
            "request_id": request_id,
            "data": {
                "agent_stats": self.stats,
                "platform": "windows",
                "uptime": (datetime.now() - self.stats["startup_time"]).total_seconds() 
                          if self.stats["startup_time"] else 0,
                "note": "使用简化版应用启动器"
            }
        }
        
        return response
    
    def _create_error_response(self, message: str, request_id: str, 
                             error_code: str = "ERROR", details: str = None) -> str:
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
        
        if details and self.config.get("debug_mode"):
            response["data"]["error_details"] = details
        
        return json.dumps(response, ensure_ascii=False)
    
    async def shutdown(self) -> None:
        """关闭Agent"""
        logger.info("正在关闭Agent...")
        
        # 保存统计信息
        if self.config.get("debug_mode"):
            stats_file = os.path.join(os.path.dirname(__file__), "agent_stats.json")
            try:
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(self.stats, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存统计信息失败: {e}")
        
        logger.info("Agent已关闭")

# 工厂函数
def create_working_app_launcher_agent(config: Dict = None) -> WorkingAppLauncherAgent:
    """创建工作版应用启动Agent实例"""
    return WorkingAppLauncherAgent(config)

# 导出函数
def get_agent_metadata() -> Dict:
    """获取Agent元数据"""
    return {
        "name": "工作版应用启动服务",
        "displayName": "Working App Launcher Service",
        "version": "3.2.0",
        "description": "智能获取应用列表并启动指定应用 - 工作版，确保稳定可靠的应用启动功能",
        "author": "pyl(1708213363@qq.com)",
        "agentType": "mcp",
        "entryPoint": {
            "module": "mcpserver.agent_open_launcher.working_launcher_agent",
            "class": "WorkingAppLauncherAgent"
        },
        "factory": {
            "create_instance": "create_working_app_launcher_agent",
            "validate_config": "validate_agent_config",
            "get_dependencies": "get_agent_dependencies"
        }
    }

def validate_agent_config(config: Dict) -> bool:
    """验证Agent配置"""
    return True

def get_agent_dependencies() -> List[str]:
    """获取Agent依赖"""
    return [
        "psutil"
    ]

# 测试函数
async def test_working():
    """测试工作版"""
    print("=== 测试工作版应用启动器 ===\n")
    
    # 创建Agent
    agent = create_working_app_launcher_agent()
    await agent.initialize()
    
    # 测试获取应用列表
    print("1. 测试获取应用列表...")
    result = await agent.handle_handoff({"tool_name": "获取应用列表"})
    data = json.loads(result)
    print(f"   结果: {data['success']}")
    print(f"   应用数量: {data['data']['total_count']}")
    print(f"   应用示例: {data['data']['apps'][:5]}")
    
    # 测试启动记事本
    print("\n2. 测试启动记事本...")
    result = await agent.handle_handoff({"tool_name": "启动应用", "app": "记事本"})
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
    
    print("\n=== 工作版测试完成 ===")

if __name__ == "__main__":
    import platform
    asyncio.run(test_working())