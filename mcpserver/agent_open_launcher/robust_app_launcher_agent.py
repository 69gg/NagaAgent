# robust_app_launcher_agent.py - 稳健版应用启动Agent
import os
import json
import asyncio
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Optional, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_app_launcher import create_enhanced_launcher, LaunchStatus, LaunchResult
from enhanced_app_scanner import get_enhanced_scanner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

class RobustAppLauncherAgent:
    """稳健版应用启动Agent - 提供可靠的应用启动服务和详细的调试信息"""
    
    name = "Robust AppLauncher Agent"
    version = "3.0.0"
    
    def __init__(self, config: Dict = None):
        """初始化Agent"""
        self.config = config or self._load_config()
        self.launcher = create_enhanced_launcher(self.config)
        self.scanner = get_enhanced_scanner(self.config)
        self.initialized = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_error": None,
            "startup_time": None
        }
        
        # 初始化日志
        self._setup_logging()
        
        logger.info(f"✅ {self.name} v{self.version} 初始化完成")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config_path = os.path.join(os.path.dirname(__file__), "config.env")
        config = {}
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            # 转换值类型
                            if value.lower() in ('true', 'false'):
                                config[key] = value.lower() == 'true'
                            elif value.isdigit():
                                config[key] = int(value)
                            else:
                                config[key] = value
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
        
        # 默认配置
        defaults = {
            "debug_mode": False,
            "cache_enabled": True,
            "cache_ttl": 3600,
            "max_apps": 1000,
            "launch_timeout": 30,
            "wait_for_startup": True,
            "check_already_running": True,
            "monitor_processes": True,
            "max_retries": 3,
            "log_level": "INFO"
        }
        
        # 合并配置
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def _setup_logging(self) -> None:
        """设置日志配置"""
        # 根据配置设置日志级别
        log_level = getattr(logging, self.config.get("log_level", "INFO").upper())
        logger.setLevel(log_level)
        
        # 创建文件处理器
        if self.config.get("debug_mode"):
            log_file = os.path.join(os.path.dirname(__file__), "debug.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    async def initialize(self) -> None:
        """异步初始化"""
        if self.initialized:
            return
        
        try:
            logger.info("🔧 开始异步初始化...")
            
            # 预热扫描器（不阻塞）
            asyncio.create_task(self.scanner.ensure_scan_completed())
            
            self.stats["startup_time"] = datetime.now()
            self.initialized = True
            
            logger.info("✅ Agent初始化完成")
            
        except Exception as e:
            logger.error(f"❌ Agent初始化失败: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def handle_handoff(self, data: Dict) -> str:
        """处理MCP handoff请求"""
        self.stats["total_requests"] += 1
        request_id = data.get("request_id", f"req_{self.stats['total_requests']}")
        
        logger.info(f"📥 收到请求 [{request_id}]: {data.get('tool_name', 'Unknown')}")
        
        try:
            # 确保已初始化
            if not self.initialized:
                await self.initialize()
            
            # 验证请求数据
            validation = self._validate_request(data)
            if not validation["valid"]:
                self.stats["failed_requests"] += 1
                return self._create_error_response(
                    validation["message"],
                    request_id,
                    error_code="INVALID_REQUEST"
                )
            
            # 处理请求
            tool_name = data.get("tool_name")
            result = await self._process_request(tool_name, data, request_id)
            
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
            
            logger.error(f"❌ 处理请求失败 [{request_id}]: {e}")
            logger.debug(traceback.format_exc())
            
            return self._create_error_response(
                f"处理请求时发生内部错误: {str(e)}",
                request_id,
                error_code="INTERNAL_ERROR",
                details=traceback.format_exc() if self.config.get("debug_mode") else None
            )
    
    def _validate_request(self, data: Dict) -> Dict:
        """验证请求数据"""
        if not isinstance(data, dict):
            return {"valid": False, "message": "请求数据必须是JSON对象"}
        
        tool_name = data.get("tool_name")
        if not tool_name:
            return {"valid": False, "message": "缺少tool_name参数"}
        
        if not isinstance(tool_name, str):
            return {"valid": False, "message": "tool_name必须是字符串"}
        
        return {"valid": True, "message": "验证通过"}
    
    async def _process_request(self, tool_name: str, data: Dict, request_id: str) -> Dict:
        """处理具体请求"""
        if tool_name == "启动应用":
            return await self._handle_launch_app(data, request_id)
        elif tool_name == "获取应用列表":
            return await self._handle_get_apps(data, request_id)
        elif tool_name == "终止应用":
            return await self._handle_terminate_app(data, request_id)
        elif tool_name == "获取运行中的应用":
            return await self._handle_get_running_apps(data, request_id)
        elif tool_name == "刷新应用列表":
            return await self._handle_refresh_apps(data, request_id)
        elif tool_name == "获取启动历史":
            return await self._handle_get_launch_history(data, request_id)
        elif tool_name == "获取统计信息":
            return await self._handle_get_stats(data, request_id)
        else:
            return {
                "success": False,
                "status": "error",
                "message": f"未知的操作: {tool_name}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_launch_app(self, data: Dict, request_id: str) -> Dict:
        """处理启动应用请求"""
        app_name = data.get("app")
        args = data.get("args")
        options = data.get("options", {})
        
        logger.info(f"🚀 启动应用请求: {app_name}")
        
        if not app_name:
            # 返回应用列表供选择
            return await self._get_app_list_for_selection(request_id)
        
        # 启动应用
        try:
            status = await self.launcher.launch_app(app_name, args, options)
            
            if status.result == LaunchResult.SUCCESS:
                response = {
                    "success": True,
                    "status": "app_started",
                    "message": status.message,
                    "request_id": request_id,
                    "data": {
                        "app_name": status.app_name,
                        "process_id": status.process_id,
                        "start_time": status.start_time,
                        "launch_method": status.launch_method,
                        "duration": time.time() - status.start_time if status.start_time else 0
                    }
                }
            else:
                response = {
                    "success": False,
                    "status": status.result.value,
                    "message": status.message,
                    "request_id": request_id,
                    "data": {
                        "app_name": status.app_name,
                        "error_code": status.error_code,
                        "error_details": status.error_details,
                        "suggestion": self._get_error_suggestion(status.result)
                    }
                }
            
            return response
            
        except Exception as e:
            logger.error(f"启动应用异常: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"启动应用时发生异常: {str(e)}",
                "request_id": request_id,
                "data": {
                    "app_name": app_name,
                    "error_details": traceback.format_exc() if self.config.get("debug_mode") else None
                }
            }
    
    async def _handle_get_apps(self, data: Dict, request_id: str) -> Dict:
        """处理获取应用列表请求"""
        force_refresh = data.get("force_refresh", False)
        limit = data.get("limit", 100)
        
        try:
            app_info = await self.scanner.get_app_info_for_llm()
            
            response = {
                "success": True,
                "status": "apps_list",
                "message": f"✅ 已获取到 {app_info['total_count']} 个可用应用",
                "request_id": request_id,
                "data": {
                    "total_count": app_info["total_count"],
                    "apps": app_info["apps"][:limit],
                    "has_more": len(app_info["apps"]) > limit,
                    "scan_stats": app_info.get("scan_stats", {}),
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"获取应用列表失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"获取应用列表失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_terminate_app(self, data: Dict, request_id: str) -> Dict:
        """处理终止应用请求"""
        app_name = data.get("app")
        
        if not app_name:
            return {
                "success": False,
                "status": "error",
                "message": "缺少app参数",
                "request_id": request_id,
                "data": {}
            }
        
        try:
            status = await self.launcher.terminate_app(app_name)
            
            response = {
                "success": status.result == LaunchResult.SUCCESS,
                "status": status.result.value,
                "message": status.message,
                "request_id": request_id,
                "data": {
                    "app_name": status.app_name,
                    "error_details": status.error_details
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"终止应用失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"终止应用失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_get_running_apps(self, data: Dict, request_id: str) -> Dict:
        """处理获取运行中应用请求"""
        try:
            running_apps = await self.launcher.get_running_apps()
            
            response = {
                "success": True,
                "status": "running_apps",
                "message": f"✅ 当前有 {len(running_apps)} 个应用在运行",
                "request_id": request_id,
                "data": {
                    "running_apps": running_apps,
                    "total_count": len(running_apps)
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"获取运行应用失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"获取运行应用失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_refresh_apps(self, data: Dict, request_id: str) -> Dict:
        """处理刷新应用列表请求"""
        try:
            await self.scanner.refresh_apps()
            
            response = {
                "success": True,
                "status": "refreshed",
                "message": "✅ 应用列表已刷新",
                "request_id": request_id,
                "data": {
                    "refresh_time": datetime.now().isoformat(),
                    "scan_stats": self.scanner.get_scan_stats()
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"刷新应用列表失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"刷新应用列表失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_get_launch_history(self, data: Dict, request_id: str) -> Dict:
        """处理获取启动历史请求"""
        limit = data.get("limit", 10)
        
        try:
            history = self.launcher.get_launch_history(limit)
            
            response = {
                "success": True,
                "status": "launch_history",
                "message": f"✅ 获取到 {len(history)} 条启动记录",
                "request_id": request_id,
                "data": {
                    "history": history,
                    "total_records": len(self.launcher.launch_history)
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"获取启动历史失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"获取启动历史失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _handle_get_stats(self, data: Dict, request_id: str) -> Dict:
        """处理获取统计信息请求"""
        try:
            launcher_stats = self.launcher.get_stats()
            
            response = {
                "success": True,
                "status": "stats",
                "message": "✅ 统计信息已获取",
                "request_id": request_id,
                "data": {
                    "agent_stats": self.stats,
                    "launcher_stats": launcher_stats,
                    "uptime": (datetime.now() - self.stats["startup_time"]).total_seconds() 
                              if self.stats["startup_time"] else 0
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"获取统计信息失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    async def _get_app_list_for_selection(self, request_id: str) -> Dict:
        """获取应用列表供选择"""
        try:
            app_info = await self.scanner.get_app_info_for_llm()
            
            response = {
                "success": True,
                "status": "app_selection",
                "message": f"✅ 已获取到 {app_info['total_count']} 个可用应用。请从下方列表中选择要启动的应用：",
                "request_id": request_id,
                "data": {
                    "total_count": app_info["total_count"],
                    "apps": app_info["apps"][:50],  # 限制显示数量
                    "has_more": len(app_info["apps"]) > 50,
                    "usage_format": {
                        "tool_name": "启动应用",
                        "app": "应用名称（必填，从上述列表中选择）",
                        "args": "启动参数（可选）",
                        "options": {
                            "elevated": "是否以管理员权限运行（可选，默认false）",
                            "working_dir": "工作目录（可选）"
                        }
                    },
                    "example": {
                        "tool_name": "启动应用",
                        "app": "Chrome",
                        "args": "--incognito",
                        "options": {
                            "elevated": false
                        }
                    }
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"获取应用选择列表失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"获取应用列表失败: {str(e)}",
                "request_id": request_id,
                "data": {}
            }
    
    def _get_error_suggestion(self, result: LaunchResult) -> str:
        """根据错误结果提供建议"""
        suggestions = {
            LaunchResult.NOT_FOUND: "请检查应用名称是否正确，或使用'获取应用列表'查看可用应用",
            LaunchResult.ALREADY_RUNNING: "应用已在运行中，如需重新启动请先终止当前进程",
            LaunchResult.ACCESS_DENIED: "尝试以管理员权限运行应用",
            LaunchResult.INVALID_PATH: "应用文件可能已损坏或被移动，请重新安装应用",
            LaunchResult.TIMEOUT: "应用启动超时，请稍后重试或检查系统资源",
            LaunchResult.FAILED: "启动失败，请检查系统日志或重启后重试"
        }
        return suggestions.get(result, "请重试或联系技术支持")
    
    def _create_error_response(self, message: str, request_id: str, 
                             error_code: str = "ERROR", details: str = None) -> str:
        """创建错误响应"""
        response = {
            "success": False,
            "status": "error",
            "message": message,
            "request_id": request_id,
            "error_code": error_code,
            "data": {}
        }
        
        if details and self.config.get("debug_mode"):
            response["data"]["error_details"] = details
        
        return json.dumps(response, ensure_ascii=False)
    
    async def shutdown(self) -> None:
        """关闭Agent"""
        logger.info("🔄 正在关闭Agent...")
        
        # 保存统计信息
        if self.config.get("debug_mode"):
            stats_file = os.path.join(os.path.dirname(__file__), "agent_stats.json")
            try:
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(self.stats, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存统计信息失败: {e}")
        
        logger.info("✅ Agent已关闭")

# 工厂函数
def create_robust_app_launcher_agent(config: Dict = None) -> RobustAppLauncherAgent:
    """创建稳健版应用启动Agent实例"""
    return RobustAppLauncherAgent(config)

def get_agent_metadata() -> Dict:
    """获取Agent元数据"""
    manifest_path = os.path.join(os.path.dirname(__file__), "agent-manifest.json")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载元数据失败: {e}")
        return None

def validate_agent_config(config: Dict) -> bool:
    """验证Agent配置"""
    return True

def get_agent_dependencies() -> List[str]:
    """获取Agent依赖"""
    return [
        "psutil",
        "pywin32",
        "win32api",
        "win32con",
        "win32event",
        "win32com"
    ]

# 导入time（之前忘记导入了）
import time