# enhanced_app_launcher.py - 增强版应用启动器
import os
import subprocess
import asyncio
import json
import sys
import time
import logging
import psutil
import win32api
import win32con
import win32event
from typing import Dict, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_app_scanner import get_enhanced_scanner, AppInfo, AppSource

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

class EnhancedAppLauncher:
    """增强版应用启动器 - 提供稳定的应用启动功能和详细的错误处理"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        self.scanner = get_enhanced_scanner(self.config)
        self.launch_history = []
        self.running_processes = {}
        self._process_monitor_task = None
        
        # 启动进程监控
        if self.config["monitor_processes"]:
            self._start_process_monitor()
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            "launch_timeout": 30,  # 启动超时时间（秒）
            "wait_for_startup": True,  # 是否等待应用启动
            "startup_wait_time": 5,  # 启动等待时间
            "check_already_running": True,  # 检查是否已在运行
            "elevate_if_needed": False,  # 是否需要提升权限
            "monitor_processes": True,  # 监控进程
            "max_retries": 3,  # 最大重试次数
            "debug_mode": False,  # 调试模式
            "log_launch_details": True,  # 记录启动详情
            "validate_executable": True,  # 验证可执行文件
            "use_shell_execute": False,  # 是否使用shell执行
            "working_directory": None  # 工作目录
        }
    
    def _start_process_monitor(self) -> None:
        """启动进程监控任务"""
        if self._process_monitor_task is None or self._process_monitor_task.done():
            self._process_monitor_task = asyncio.create_task(self._monitor_processes())
    
    async def _monitor_processes(self) -> None:
        """监控已启动的进程"""
        while True:
            try:
                # 检查运行的进程
                dead_processes = []
                for pid, info in self.running_processes.items():
                    if not psutil.pid_exists(pid):
                        dead_processes.append(pid)
                        logger.info(f"进程 {pid} ({info['name']}) 已退出")
                
                # 清理退出的进程
                for pid in dead_processes:
                    del self.running_processes[pid]
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"进程监控错误: {e}")
                await asyncio.sleep(10)
    
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
        if self.config["validate_executable"]:
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
        
        # 尝试启动
        retry_count = 0
        last_error = None
        
        while retry_count < self.config["max_retries"]:
            try:
                logger.debug(f"尝试启动 {app_info.display_name} (第 {retry_count + 1} 次)")
                
                # 根据来源选择启动方式
                if app_info.source in [AppSource.SHORTCUT_START_MENU, 
                                     AppSource.SHORTCUT_DESKTOP, 
                                     AppSource.SHORTCUT_COMMON]:
                    status = await self._launch_via_shortcut(app_info, launch_args)
                else:
                    status = await self._launch_via_executable(app_info, launch_args)
                
                # 记录启动历史
                self._record_launch(app_info, status, start_time)
                
                # 如果成功或不是临时错误，返回结果
                if status.result == LaunchResult.SUCCESS:
                    # 监控新进程
                    if status.process_id and self.config["monitor_processes"]:
                        self.running_processes[status.process_id] = {
                            "name": app_info.display_name,
                            "path": app_info.path,
                            "start_time": time.time()
                        }
                
                return status
                
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(f"启动失败 (尝试 {retry_count}/{self.config['max_retries']}): {e}")
                
                if retry_count < self.config["max_retries"]:
                    await asyncio.sleep(1)  # 等待后重试
        
        # 所有重试都失败
        return LaunchStatus(
            result=LaunchResult.FAILED,
            message=f"启动应用失败，已重试 {self.config['max_retries']} 次",
            app_name=app_info.display_name,
            error_details=str(last_error)
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
            
            # 检查文件扩展名
            if not exe_path.lower().endswith('.exe'):
                return {"valid": False, "reason": "不是可执行文件", "details": f"扩展名: {os.path.splitext(exe_path)[1]}"}
            
            # 检查文件权限
            if not os.access(exe_path, os.X_OK):
                return {"valid": False, "reason": "没有执行权限", "details": f"文件: {exe_path}"}
            
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
            "show_cmd": win32con.SW_NORMAL,
            "elevated": options.get("elevated", self.config["elevate_if_needed"])
        }
        
        # 处理参数
        if args:
            if isinstance(args, str):
                launch_args["args"] = args.split()
            elif isinstance(args, list):
                launch_args["args"] = args
        
        # 处理快捷方式特定参数
        if app_info.shortcut_path:
            launch_args["shortcut_path"] = app_info.shortcut_path
        
        return launch_args
    
    async def _launch_via_shortcut(self, app_info: AppInfo, launch_args: Dict) -> LaunchStatus:
        """通过快捷方式启动应用"""
        try:
            logger.debug(f"通过快捷方式启动: {app_info.shortcut_path}")
            
            # 构建命令
            cmd = [app_info.shortcut_path]
            cmd.extend(launch_args["args"])
            
            # 启动进程
            if self.config["use_shell_execute"]:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=launch_args["working_dir"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    cwd=launch_args["working_dir"]
                )
            
            # 等待启动
            if self.config["wait_for_startup"]:
                await self._wait_for_process_startup(proc, app_info.display_name)
            
            return LaunchStatus(
                result=LaunchResult.SUCCESS,
                message=f"已通过快捷方式启动应用: {app_info.display_name}",
                app_name=app_info.display_name,
                process_id=proc.pid,
                start_time=time.time(),
                launch_method="shortcut"
            )
            
        except Exception as e:
            logger.error(f"快捷方式启动失败: {e}")
            raise
    
    async def _launch_via_executable(self, app_info: AppInfo, launch_args: Dict) -> LaunchStatus:
        """直接启动可执行文件"""
        try:
            logger.debug(f"直接启动可执行文件: {app_info.path}")
            
            # 构建命令
            cmd = [app_info.path]
            cmd.extend(launch_args["args"])
            
            # 准备启动参数
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = launch_args["show_cmd"]
            
            # 如果需要提升权限
            if launch_args["elevated"]:
                logger.info("请求提升权限启动应用")
                # 使用ShellExecute来提升权限
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.Run(' '.join(cmd), 1, True)
                return LaunchStatus(
                    result=LaunchResult.SUCCESS,
                    message=f"已以管理员权限启动应用: {app_info.display_name}",
                    app_name=app_info.display_name,
                    launch_method="elevated"
                )
            
            # 正常启动
            proc = subprocess.Popen(
                cmd,
                cwd=launch_args["working_dir"],
                startupinfo=startup_info
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
                launch_method="direct"
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
            logger.error(f"可执行文件启动失败: {e}")
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
            "launch_method": status.launch_method
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
            for pid, info in self.running_processes.items():
                if psutil.pid_exists(pid):
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
            exe_name = os.path.basename(app_info.path).lower()
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if (proc.info['exe'] and proc.info['exe'].lower() == app_info.path.lower()) or \
                       (proc.info['name'] and proc.info['name'].lower() == exe_name):
                        proc.terminate()
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
            "scanner_stats": self.scanner.get_scan_stats()
        }

# 创建增强版应用启动器
def create_enhanced_launcher(config: Dict = None) -> EnhancedAppLauncher:
    """创建增强版应用启动器实例"""
    return EnhancedAppLauncher(config)