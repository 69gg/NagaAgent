# agent_app_launcher.py # 应用启动与管理Agent（综合版）
import os  # 操作系统 #
import platform  # 平台 #
import subprocess  # 子进程 #
import asyncio  # 异步 #
import json  # JSON #
import sys  # 系统 #

# 添加当前目录到Python路径 #
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comprehensive_app_scanner import get_comprehensive_scanner  # 综合扫描器 #

class AppLauncherAgent(object):
    """应用启动与管理Agent，支持从注册表和快捷方式获取应用列表并启动应用 #"""  # 类注释 #
    name = "AppLauncher Agent"  # Agent名称 #

    def __init__(self):
        # 初始化综合扫描器 #
        self.scanner = get_comprehensive_scanner()  # 获取扫描器 #
        print(f'✅ AppLauncherAgent初始化完成，综合应用数: {len(self.scanner.get_apps())}')  # 初始化信息 #

    async def handle_handoff(self, data: dict) -> str:
        """
        MCP标准接口，处理handoff请求
        智能应用启动：如果不提供app参数则返回应用列表，如果提供则启动应用
        """
        try:
            tool_name = data.get("tool_name")
            if not tool_name:
                return json.dumps({"success": False, "status": "error", "message": "缺少tool_name参数", "data": {}}, ensure_ascii=False)
            
            if tool_name == "open":
                # 智能应用启动工具 #
                app = data.get("app")
                args = data.get("args")
                
                if not app:
                    # 没有提供应用名称，返回应用列表 #
                    result = self._get_apps_list()
                else:
                    # 提供了应用名称，尝试启动应用 #
                    result = self._open_app(app, args)
                
                return json.dumps(result, ensure_ascii=False)
            
            else:
                return json.dumps({"success": False, "status": "error", "message": f"未知操作: {tool_name}", "data": {}}, ensure_ascii=False)
                
        except Exception as e:
            return json.dumps({"success": False, "status": "error", "message": str(e), "data": {}}, ensure_ascii=False)

    def _get_apps_list(self) -> dict:
        """获取应用列表供LLM选择 #"""
        try:
            app_info = self.scanner.get_app_info_for_llm()
            
            return {
                "success": True,
                "status": "apps_ready",
                "message": f"成功获取到 {app_info['total_count']} 个可用应用，请从列表中选择要启动的应用",
                "data": app_info
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"获取应用列表失败: {str(e)}",
                "data": {}
            }

    def _open_app(self, app_name: str, args: str = None) -> dict:
        """启动指定应用 #"""
        try:
            print(f"🔍 查找应用: {app_name}")
            
            # 从综合扫描器中查找应用 #
            app_info = self.scanner.find_app_by_name(app_name)
            
            if not app_info:
                # 如果没找到，返回可用应用列表供LLM重新选择 #
                available_apps = self.scanner.get_apps()
                app_names = [app["name"] for app in available_apps[:20]]  # 只显示前20个 #
                
                return {
                    "success": False,
                    "status": "app_not_found",
                    "message": f"未找到应用 '{app_name}'，请从以下可用应用中选择: {', '.join(app_names)}",
                    "data": {
                        "requested_app": app_name,
                        "available_apps": app_names,
                        "total_available": len(available_apps),
                        "suggestion": "请使用 'open' 工具（不提供app参数）获取完整应用列表"
                    }
                }
            
            # 找到应用，根据来源选择启动方式 #
            source = app_info["source"]
            print(f"🚀 启动应用: {app_name} (来源: {source}) -> {app_info['path']}")
            
            try:
                if source == "shortcut":
                    # 快捷方式启动 #
                    result = self._launch_shortcut(app_info, args)
                else:
                    # 注册表启动 #
                    result = self._launch_executable(app_info, args)
                
                return result
                
            except Exception as e:
                return {
                    "success": False,
                    "status": "start_failed",
                    "message": f"启动应用失败: {str(e)}",
                    "data": {
                        "app_name": app_name,
                        "exe_path": app_info["path"],
                        "source": source,
                        "error": str(e)
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"启动应用时发生错误: {str(e)}",
                "data": {}
            }
    
    def _launch_shortcut(self, app_info: dict, args: str = None) -> dict:
        """通过快捷方式启动应用 #"""
        try:
            shortcut_path = app_info["shortcut_path"]
            
            # 构建启动命令 #
            cmd = [shortcut_path]
            if args:
                if isinstance(args, str):
                    cmd.extend(args.split())
                elif isinstance(args, list):
                    cmd.extend(args)
            
            # 启动应用 #
            subprocess.Popen(cmd, shell=True)  # 快捷方式需要shell=True
            
            return {
                "success": True,
                "status": "app_started",
                "message": f"已成功通过快捷方式启动应用: {app_info['name']}",
                "data": {
                    "app_name": app_info["name"],
                    "shortcut_path": shortcut_path,
                    "exe_path": app_info["path"],
                    "args": args,
                    "source": "shortcut"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "status": "start_failed",
                "message": f"通过快捷方式启动应用失败: {str(e)}",
                "data": {
                    "app_name": app_info["name"],
                    "shortcut_path": shortcut_path,
                    "error": str(e)
                }
            }
    
    def _launch_executable(self, app_info: dict, args: str = None) -> dict:
        """直接启动可执行文件 #"""
        try:
            exe_path = app_info["path"]
            
            # 构建启动命令 #
            cmd = [exe_path]
            if args:
                if isinstance(args, str):
                    cmd.extend(args.split())
                elif isinstance(args, list):
                    cmd.extend(args)
            
            # 启动应用 #
            subprocess.Popen(cmd, shell=False)
            
            return {
                "success": True,
                "status": "app_started",
                "message": f"已成功启动应用: {app_info['name']}",
                "data": {
                    "app_name": app_info["name"],
                    "exe_path": exe_path,
                    "args": args,
                    "source": "registry"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "status": "start_failed",
                "message": f"启动应用失败: {str(e)}",
                "data": {
                    "app_name": app_info["name"],
                    "exe_path": exe_path,
                    "error": str(e)
                }
            }

# 工厂函数：动态创建Agent实例 #
def create_app_launcher_agent():
    """创建AppLauncherAgent实例 #"""
    return AppLauncherAgent()

# 获取Agent元数据 #
def get_agent_metadata():
    """获取Agent元数据 #"""
    import os
    manifest_path = os.path.join(os.path.dirname(__file__), "agent-manifest.json")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载元数据失败: {e}")
        return None

# 验证配置 #
def validate_agent_config(config):
    """验证Agent配置 #"""
    return True

# 获取依赖 #
def get_agent_dependencies():
    """获取Agent依赖 #"""
    return []
