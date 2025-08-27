# cross_platform_app_launcher.py - 跨平台应用启动器
import os
import subprocess
import asyncio
import json
import sys
import time
import logging
import signal
from typing import Dict, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from platform_utils import get_platform_utils, OperatingSystem
from cross_platform_app_scanner import get_cross_platform_scanner, AppInfo, AppSource

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LaunchResult(Enum):
    """启动结果枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    ALREADY_RUNNING = "already_running"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    INVALID_PATH = "invalid_path"
    TIMEOUT = "timeout"
    UNSUPPORTED_PLATFORM = "unsupported_platform"

@dataclass
class LaunchStatus:
    """启动状态数据类"""
    result: LaunchResult
    message: str
    app_name: Optional[str] = None
    process_id: Optional[int] = None
    start_time: Optional[float] = None
    error_code: Optional[int] = None
    error_details: Optional[str] = None
    launch_method: Optional[str] = None

class CrossPlatformAppLauncher:
    """跨平台应用启动器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        self.platform = get_platform_utils()
        self.scanner = get_cross_platform_scanner(self.config)
        self.launch_history = []
        self.running_processes = {}
        self._process_monitor_task = None
        
        # 启动进程监控
        if self.config.get("monitor_processes", True):
            self._start_process_monitor()
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            "launch_timeout": 30,
            "wait_for_startup": True,
            "startup_wait_time": 5,
            "check_already_running": True,
            "elevate_if_needed": False,
            "monitor_processes": True,
            "max_retries": 3,
            "debug_mode": False,
            "log_launch_details": True,
            "validate_executable": True,
            "use_shell_execute": False,
            "working_directory": None,
            # 平台特定配置
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
    
    def _start_process_monitor(self) -> None:
        """启动进程监控任务"""
        if self._process_monitor_task is None or self._process_monitor_task.done():
            # 在有事件循环时创建任务
            try:
                loop = asyncio.get_running_loop()
                self._process_monitor_task = loop.create_task(self._monitor_processes())
            except RuntimeError:
                # 没有运行的事件循环，稍后启动
                self._process_monitor_task = None
    
    async def _monitor_processes(self) -> None:
        """监控已启动的进程"""
        while True:
            try:
                # 检查运行的进程
                dead_processes = []
                for pid, info in self.running_processes.items():
                    if not self._is_process_running(pid):
                        dead_processes.append(pid)
                        logger.info(f"进程 {pid} ({info['name']}) 已退出")
                
                # 清理退出的进程
                for pid in dead_processes:
                    del self.running_processes[pid]
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"进程监控错误: {e}")
                await asyncio.sleep(10)
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行"""
        try:
            if self.platform.os_type == OperatingSystem.WINDOWS:
                import win32api
                import win32con
                handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
                if handle:
                    win32api.CloseHandle(handle)
                    return True
            else:
                # Unix-like系统
                os.kill(pid, 0)  # 发送信号0检查进程是否存在
                return True
        except:
            return False
        return False
    
    async def launch_app(self, app_name: str, args: Union[str, List[str]] = None, 
                        options: Dict = None) -> LaunchStatus:
        """启动应用程序"""
        start_time = time.time()
        options = options or {}
        
        logger.info(f"🚀 准备启动应用: {app_name}")
        
        # 查找应用
        app_info = await self._find_app_info(app_name)
        if not app_info:
            return LaunchStatus(
                result=LaunchResult.NOT_FOUND,
                message=f"未找到应用: {app_name}",
                app_name=app_name
            )
        
        # 验证可执行文件
        if self.config.get("validate_executable", True):
            validation = self._validate_executable(app_info.path)
            if not validation["valid"]:
                return LaunchStatus(
                    result=LaunchResult.INVALID_PATH,
                    message=f"可执行文件无效: {validation['reason']}",
                    app_name=app_name,
                    error_details=validation["details"]
                )
        
        # 检查是否已在运行
        if self.config["check_already_running"]:
            running = await self._check_if_running(app_info)
            if running:
                return LaunchStatus(
                    result=LaunchResult.ALREADY_RUNNING,
                    message=f"应用已在运行: {app_info.display_name}",
                    app_name=app_info.display_name,
                    process_id=running
                )
        
        # 准备启动参数
        launch_args = self._prepare_launch_args(app_info, args, options)
        
        # 根据平台选择启动方式
        try:
            if self.platform.os_type == OperatingSystem.WINDOWS:
                status = await self._launch_windows_app(app_info, launch_args)
            elif self.platform.os_type == OperatingSystem.LINUX:
                status = await self._launch_linux_app(app_info, launch_args)
            elif self.platform.os_type == OperatingSystem.MACOS:
                status = await self._launch_macos_app(app_info, launch_args)
            else:
                status = LaunchStatus(
                    result=LaunchResult.UNSUPPORTED_PLATFORM,
                    message=f"不支持的平台: {self.platform.os_type.value}",
                    app_name=app_info.display_name
                )
            
            # 记录启动历史
            self._record_launch(app_info, status, start_time)
            
            # 如果成功，监控新进程
            if status.result == LaunchResult.SUCCESS and status.process_id:
                if self.config["monitor_processes"]:
                    self.running_processes[status.process_id] = {
                        "name": app_info.display_name,
                        "path": app_info.path,
                        "start_time": time.time()
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"启动应用异常: {e}")
            return LaunchStatus(
                result=LaunchResult.FAILED,
                message=f"启动应用时发生异常: {str(e)}",
                app_name=app_info.display_name,
                error_details=str(e)
            )
    
    async def _find_app_info(self, app_name: str) -> Optional[AppInfo]:
        """查找应用信息"""
        # 首先尝试精确匹配
        app_info = await self.scanner.find_app(app_name, fuzzy=False)
        
        # 如果没找到，尝试模糊匹配
        if not app_info:
            app_info = await self.scanner.find_app(app_name, fuzzy=True)
            if app_info:
                logger.info(f"使用模糊匹配找到应用: {app_info.display_name}")
        
        return app_info
    
    def _validate_executable(self, exe_path: str) -> Dict:
        """验证可执行文件"""
        try:
            if not os.path.exists(exe_path):
                return {"valid": False, "reason": "文件不存在", "details": f"路径: {exe_path}"}
            
            if not os.path.isfile(exe_path):
                return {"valid": False, "reason": "不是文件", "details": f"路径: {exe_path}"}
            
            # 平台特定的验证
            if self.platform.os_type == OperatingSystem.WINDOWS:
                if not exe_path.lower().endswith(('.exe', '.bat', '.cmd', '.ps1')):
                    return {"valid": False, "reason": "不是Windows可执行文件", 
                           "details": f"扩展名: {os.path.splitext(exe_path)[1]}"}
            else:
                if not self.platform.is_executable(exe_path):
                    return {"valid": False, "reason": "文件没有执行权限", 
                           "details": f"文件: {exe_path}"}
            
            # 检查文件大小
            file_size = os.path.getsize(exe_path)
            if file_size == 0:
                return {"valid": False, "reason": "文件为空", "details": f"大小: {file_size} 字节"}
            
            return {"valid": True, "reason": "验证通过", "details": f"大小: {file_size} 字节"}
            
        except Exception as e:
            return {"valid": False, "reason": "验证过程出错", "details": str(e)}
    
    async def _check_if_running(self, app_info: AppInfo) -> Optional[int]:
        """检查应用是否已在运行"""
        try:
            import psutil
            
            exe_name = os.path.basename(app_info.path).lower()
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe'] and proc.info['exe'].lower() == app_info.path.lower():
                        return proc.info['pid']
                    
                    # 如果exe路径不可用，通过进程名匹配
                    if proc.info['name'] and proc.info['name'].lower() == exe_name:
                        return proc.info['pid']
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"检查运行状态失败: {e}")
            return None
    
    def _prepare_launch_args(self, app_info: AppInfo, args: Union[str, List[str]], 
                           options: Dict) -> Dict:
        """准备启动参数"""
        launch_args = {
            "exe_path": app_info.path,
            "args": [],
            "working_dir": options.get("working_dir") or 
                          (app_info.install_location if app_info.install_location else 
                           os.path.dirname(app_info.path)),
            "elevated": options.get("elevated", self.config["elevate_if_needed"]),
            "env": os.environ.copy()
        }
        
        # 处理参数
        if args:
            if isinstance(args, str):
                launch_args["args"] = args.split()
            elif isinstance(args, list):
                launch_args["args"] = args
        
        # 处理快捷方式特定参数
        if hasattr(app_info, 'shortcut_path') and app_info.shortcut_path:
            launch_args["shortcut_path"] = app_info.shortcut_path
        
        # 平台特定处理
        if self.platform.os_type == OperatingSystem.LINUX:
            # 设置显示环境变量
            if options.get("display"):
                launch_args["env"]["DISPLAY"] = options["display"]
            elif self.config["linux"]["display"]:
                launch_args["env"]["DISPLAY"] = self.config["linux"]["display"]
        
        return launch_args
    
    async def _launch_windows_app(self, app_info: AppInfo, launch_args: Dict) -> LaunchStatus:
        """启动Windows应用"""
        try:
            logger.debug(f"启动Windows应用: {app_info.path}")
            
            # 处理macOS .app文件（如果有的话）
            if app_info.path.endswith('.app'):
                return LaunchStatus(
                    result=LaunchResult.FAILED,
                    message=f"无法在Windows上运行macOS应用: {app_info.path}",
                    app_name=app_info.display_name
                )
            
            # 构建命令
            if launch_args["elevated"] and self.config["windows"]["use_runas_for_elevation"]:
                # 使用runas提升权限
                cmd = ["runas", "/user:Administrator", f'"{app_info.path}"']
                if launch_args["args"]:
                    cmd[-1] += " " + " ".join(f'"{arg}"' for arg in launch_args["args"])
                shell = True
            else:
                cmd = [app_info.path] + launch_args["args"]
                shell = False
            
            # 启动进程
            if self.config["windows"]["create_window"]:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_NORMAL
            else:
                startupinfo = None
            
            proc = subprocess.Popen(
                cmd,
                cwd=launch_args["working_dir"],
                shell=shell,
                startupinfo=startupinfo,
                env=launch_args["env"]
            )
            
            # 等待启动
            if self.config["wait_for_startup"]:
                await self._wait_for_process_startup(proc, app_info.display_name)
            
            return LaunchStatus(
                result=LaunchResult.SUCCESS,
                message=f"已成功启动应用: {app_info.display_name}",
                app_name=app_info.display_name,
                process_id=proc.pid,
                start_time=time.time(),
                launch_method="windows_direct"
            )
            
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return LaunchStatus(
                result=LaunchResult.ACCESS_DENIED,
                message=f"启动应用失败: 权限不足",
                app_name=app_info.display_name,
                error_details=str(e)
            )
        except Exception as e:
            logger.error(f"Windows应用启动失败: {e}")
            raise
    
    async def _launch_linux_app(self, app_info: AppInfo, launch_args: Dict) -> LaunchStatus:
        """启动Linux应用"""
        try:
            logger.debug(f"启动Linux应用: {app_info.path}")
            
            # 构建命令
            cmd = []
            
            # 处理提升权限
            if launch_args["elevated"]:
                cmd.extend(["pkexec", "--user", "root"])
            
            # 对于GUI应用，可能需要特殊处理
            if app_info.path.endswith('.desktop'):
                # 使用gtk-launch启动desktop文件
                cmd.extend(["gtk-launch", os.path.basename(app_info.path)[:-8]])
            else:
                cmd.append(app_info.path)
                cmd.extend(launch_args["args"])
            
            # 启动进程
            proc = subprocess.Popen(
                cmd,
                cwd=launch_args["working_dir"],
                env=launch_args["env"],
                start_new_session=True
            )
            
            # 等待启动
            if self.config["wait_for_startup"]:
                await self._wait_for_process_startup(proc, app_info.display_name)
            
            return LaunchStatus(
                result=LaunchResult.SUCCESS,
                message=f"已成功启动应用: {app_info.display_name}",
                app_name=app_info.display_name,
                process_id=proc.pid,
                start_time=time.time(),
                launch_method="linux_direct"
            )
            
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return LaunchStatus(
                result=LaunchResult.ACCESS_DENIED,
                message=f"启动应用失败: 权限不足",
                app_name=app_info.display_name,
                error_details=str(e)
            )
        except FileNotFoundError as e:
            logger.error(f"文件未找到: {e}")
            return LaunchStatus(
                result=LaunchResult.NOT_FOUND,
                message=f"找不到可执行文件: {app_info.path}",
                app_name=app_info.display_name,
                error_details=str(e)
            )
        except Exception as e:
            logger.error(f"Linux应用启动失败: {e}")
            raise
    
    async def _launch_macos_app(self, app_info: AppInfo, launch_args: Dict) -> LaunchStatus:
        """启动macOS应用"""
        try:
            logger.debug(f"启动macOS应用: {app_info.path}")
            
            # 处理.app包
            if app_info.path.endswith('.app'):
                if self.config["macos"]["open_with_open_command"]:
                    # 使用open命令
                    cmd = ["open", app_info.path]
                    if launch_args["args"]:
                        cmd.extend(["--args"] + launch_args["args"])
                else:
                    # 直接执行包内可执行文件
                    executable_path = Path(app_info.path) / "Contents" / "MacOS" / Path(app_info.path).stem
                    if executable_path.exists():
                        cmd = [str(executable_path)] + launch_args["args"]
                    else:
                        return LaunchStatus(
                            result=LaunchResult.INVALID_PATH,
                            message=f"无法找到可执行文件: {executable_path}",
                            app_name=app_info.display_name
                        )
            else:
                # 普通可执行文件
                cmd = [app_info.path] + launch_args["args"]
            
            # 处理提升权限
            if launch_args["elevated"]:
                # 使用osascript提升权限
                applescript = f'''
                do shell script "{' '.join(cmd)}" with administrator privileges
                '''
                cmd = ["osascript", "-e", applescript]
            
            # 启动进程
            proc = subprocess.Popen(
                cmd,
                cwd=launch_args["working_dir"],
                env=launch_args["env"],
                start_new_session=True
            )
            
            # 等待启动
            if self.config["wait_for_startup"]:
                await self._wait_for_process_startup(proc, app_info.display_name)
            
            return LaunchStatus(
                result=LaunchResult.SUCCESS,
                message=f"已成功启动应用: {app_info.display_name}",
                app_name=app_info.display_name,
                process_id=proc.pid,
                start_time=time.time(),
                launch_method="macos_direct"
            )
            
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return LaunchStatus(
                result=LaunchResult.ACCESS_DENIED,
                message=f"启动应用失败: 权限不足",
                app_name=app_info.display_name,
                error_details=str(e)
            )
        except Exception as e:
            logger.error(f"macOS应用启动失败: {e}")
            raise
    
    async def _wait_for_process_startup(self, proc: subprocess.Popen, app_name: str) -> None:
        """等待进程启动"""
        try:
            # 等待一小段时间让进程初始化
            await asyncio.sleep(self.config["startup_wait_time"])
            
            # 检查进程是否仍在运行
            if proc.poll() is not None:
                logger.warning(f"进程 {app_name} 启动后立即退出")
                
        except Exception as e:
            logger.debug(f"等待进程启动时出错: {e}")
    
    def _record_launch(self, app_info: AppInfo, status: LaunchStatus, start_time: float) -> None:
        """记录启动历史"""
        if not self.config["log_launch_details"]:
            return
        
        history_entry = {
            "timestamp": time.time(),
            "app_name": app_info.display_name,
            "app_path": app_info.path,
            "result": status.result.value,
            "process_id": status.process_id,
            "duration": time.time() - start_time,
            "launch_method": status.launch_method,
            "platform": self.platform.os_type.value
        }
        
        self.launch_history.append(history_entry)
        
        # 限制历史记录数量
        if len(self.launch_history) > 100:
            self.launch_history = self.launch_history[-50:]
        
        logger.info(f"启动记录: {app_info.display_name} -> {status.result.value} "
                   f"(PID: {status.process_id}, 耗时: {history_entry['duration']:.2f}s)")
    
    async def get_running_apps(self) -> List[Dict]:
        """获取正在运行的应用列表"""
        running_apps = []
        
        try:
            import psutil
            
            for pid, info in self.running_processes.items():
                if self._is_process_running(pid):
                    try:
                        proc = psutil.Process(pid)
                        running_apps.append({
                            "name": info["name"],
                            "pid": pid,
                            "path": info["path"],
                            "start_time": info["start_time"],
                            "cpu_percent": proc.cpu_percent(),
                            "memory_percent": proc.memory_percent()
                        })
                    except psutil.NoSuchProcess:
                        continue
        except Exception as e:
            logger.error(f"获取运行应用列表失败: {e}")
        
        return running_apps
    
    async def terminate_app(self, app_name: str) -> LaunchStatus:
        """终止应用程序"""
        app_info = await self._find_app_info(app_name)
        if not app_info:
            return LaunchStatus(
                result=LaunchResult.NOT_FOUND,
                message=f"未找到应用: {app_name}"
            )
        
        # 查找并终止进程
        terminated = False
        try:
            import psutil
            
            exe_name = os.path.basename(app_info.path).lower()
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if (proc.info['exe'] and proc.info['exe'].lower() == app_info.path.lower()) or \
                       (proc.info['name'] and proc.info['name'].lower() == exe_name):
                        # 根据平台选择终止方式
                        if self.platform.os_type == OperatingSystem.WINDOWS:
                            proc.terminate()
                        else:
                            proc.send_signal(signal.SIGTERM)
                        terminated = True
                        logger.info(f"已终止进程: {proc.pid} ({app_info.display_name})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if terminated:
                return LaunchStatus(
                    result=LaunchResult.SUCCESS,
                    message=f"已终止应用: {app_info.display_name}",
                    app_name=app_info.display_name
                )
            else:
                return LaunchStatus(
                    result=LaunchResult.FAILED,
                    message=f"未找到运行中的应用: {app_info.display_name}",
                    app_name=app_info.display_name
                )
                
        except Exception as e:
            return LaunchStatus(
                result=LaunchResult.FAILED,
                message=f"终止应用失败: {str(e)}",
                app_name=app_info.display_name,
                error_details=str(e)
            )
    
    def get_launch_history(self, limit: int = 10) -> List[Dict]:
        """获取启动历史"""
        return self.launch_history[-limit:]
    
    def get_stats(self) -> Dict:
        """获取启动器统计信息"""
        total_launches = len(self.launch_history)
        successful_launches = sum(1 for h in self.launch_history if h["result"] == "success")
        
        return {
            "total_launches": total_launches,
            "successful_launches": successful_launches,
            "success_rate": successful_launches / total_launches if total_launches > 0 else 0,
            "running_processes": len(self.running_processes),
            "platform": self.platform.os_type.value,
            "scanner_stats": self.scanner.get_scan_stats()
        }

# 创建跨平台应用启动器
def create_cross_platform_launcher(config: Dict = None) -> CrossPlatformAppLauncher:
    """创建跨平台应用启动器实例"""
    return CrossPlatformAppLauncher(config)