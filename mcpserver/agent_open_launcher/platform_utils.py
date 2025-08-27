# platform_utils.py - 跨平台工具函数
import os
import sys
import platform
import subprocess
import logging
from typing import List, Dict, Optional, Union
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class OperatingSystem(Enum):
    """操作系统枚举"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"

class PlatformUtils:
    """跨平台工具类"""
    
    def __init__(self):
        self.os_type = self._detect_os()
        self.home_dir = Path.home()
        self.config_dirs = self._get_config_dirs()
        self.app_dirs = self._get_app_dirs()
    
    def _detect_os(self) -> OperatingSystem:
        """检测操作系统类型"""
        system = platform.system().lower()
        
        if system == "windows":
            return OperatingSystem.WINDOWS
        elif system == "linux":
            return OperatingSystem.LINUX
        elif system == "darwin":
            return OperatingSystem.MACOS
        else:
            return OperatingSystem.UNKNOWN
    
    def _get_config_dirs(self) -> Dict[str, Path]:
        """获取配置目录"""
        dirs = {}
        
        if self.os_type == OperatingSystem.WINDOWS:
            dirs["app_data"] = Path(os.environ.get("APPDATA", ""))
            dirs["local_app_data"] = Path(os.environ.get("LOCALAPPDATA", ""))
            dirs["program_data"] = Path(os.environ.get("PROGRAMDATA", ""))
        elif self.os_type in [OperatingSystem.LINUX, OperatingSystem.MACOS]:
            dirs["config"] = Path.home() / ".config"
            dirs["local_config"] = Path.home() / ".local" / "share"
            if self.os_type == OperatingSystem.LINUX:
                dirs["applications"] = Path("/usr/share/applications")
                dirs["desktop_entries"] = Path.home() / ".local" / "share" / "applications"
        
        return dirs
    
    def _get_app_dirs(self) -> Dict[str, List[Path]]:
        """获取应用程序目录"""
        dirs = {
            "desktop": [],
            "start_menu": [],
            "applications": []
        }
        
        if self.os_type == OperatingSystem.WINDOWS:
            # Windows
            dirs["desktop"].append(self.home_dir / "Desktop")
            dirs["desktop"].append(Path("C:\\Users\\Public\\Desktop"))
            
            dirs["start_menu"].append(self.config_dirs["app_data"] / "Microsoft" / "Windows" / "Start Menu" / "Programs")
            dirs["start_menu"].append(self.config_dirs["program_data"] / "Microsoft" / "Windows" / "Start Menu" / "Programs")
            
        elif self.os_type == OperatingSystem.LINUX:
            # Linux
            dirs["desktop"].append(self.home_dir / "Desktop")
            dirs["desktop"].append(self.home_dir / "桌面")
            
            dirs["applications"].extend([
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path("/opt"),
                self.home_dir / ".local" / "bin"
            ])
            
            if "desktop_entries" in self.config_dirs:
                dirs["start_menu"].append(self.config_dirs["desktop_entries"])
            
        elif self.os_type == OperatingSystem.MACOS:
            # macOS
            dirs["desktop"].append(self.home_dir / "Desktop")
            
            dirs["applications"].extend([
                Path("/Applications"),
                Path("/System/Applications"),
                self.home_dir / "Applications"
            ])
            
            dirs["start_menu"].append(self.home_dir / "Applications")
        
        # 过滤不存在的目录
        for key in dirs:
            dirs[key] = [d for d in dirs[key] if d.exists()]
        
        return dirs
    
    def get_executable_extensions(self) -> List[str]:
        """获取可执行文件扩展名"""
        if self.os_type == OperatingSystem.WINDOWS:
            return [".exe", ".bat", ".cmd", ".ps1"]
        elif self.os_type == OperatingSystem.LINUX:
            return ["", ".sh", ".bin"]
        elif self.os_type == OperatingSystem.MACOS:
            return ["", ".app", ".sh"]
        else:
            return [""]
    
    def is_executable(self, file_path: Union[str, Path]) -> bool:
        """检查文件是否可执行"""
        path = Path(file_path)
        
        if not path.exists():
            return False
        
        # Windows: 检查扩展名
        if self.os_type == OperatingSystem.WINDOWS:
            return path.suffix.lower() in self.get_executable_extensions()
        
        # Unix-like: 检查权限
        else:
            return os.access(path, os.X_OK)
    
    def find_executable(self, name: str) -> Optional[Path]:
        """查找可执行文件"""
        # 如果是完整路径
        if Path(name).is_absolute():
            path = Path(name)
            if self.is_executable(path):
                return path
            return None
        
        # 在PATH中查找
        if self.os_type == OperatingSystem.WINDOWS:
            # Windows也使用PATH环境变量
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                exe_path = Path(path_dir) / name
                if exe_path.exists():
                    # 尝试各种扩展名
                    for ext in self.get_executable_extensions():
                        test_path = exe_path.with_suffix(ext)
                        if test_path.exists():
                            return test_path
                else:
                    # 直接检查
                    if self.is_executable(exe_path):
                        return exe_path
        else:
            # Unix-like系统
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                exe_path = Path(path_dir) / name
                if self.is_executable(exe_path):
                    return exe_path
        
        return None
    
    def get_installed_apps(self) -> List[Dict]:
        """获取已安装的应用列表"""
        apps = []
        
        if self.os_type == OperatingSystem.WINDOWS:
            apps.extend(self._get_windows_apps())
        elif self.os_type == OperatingSystem.LINUX:
            apps.extend(self._get_linux_apps())
        elif self.os_type == OperatingSystem.MACOS:
            apps.extend(self._get_macos_apps())
        
        return apps
    
    def _get_windows_apps(self) -> List[Dict]:
        """获取Windows应用列表"""
        apps = []
        
        try:
            # 使用winreg获取注册表中的应用
            import winreg
            
            # App Paths
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            app_name = winreg.EnumKey(key, i)
                            if app_name.endswith('.exe'):
                                app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{app_name}"
                                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, app_key_path) as app_key:
                                    try:
                                        exe_path, _ = winreg.QueryValueEx(app_key, "")
                                        if exe_path and Path(exe_path).exists():
                                            apps.append({
                                                "name": app_name[:-4],
                                                "path": exe_path,
                                                "source": "registry_app_paths"
                                            })
                                    except:
                                        pass
                        except:
                            continue
            except Exception as e:
                logger.debug(f"扫描Windows注册表失败: {e}")
                
        except ImportError:
            logger.warning("winreg模块不可用，跳过Windows注册表扫描")
        
        return apps
    
    def _get_linux_apps(self) -> List[Dict]:
        """获取Linux应用列表"""
        apps = []
        
        # 扫描.desktop文件
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path.home() / ".local" / "share" / "applications"
        ]
        
        for desktop_dir in desktop_dirs:
            if desktop_dir.exists():
                for desktop_file in desktop_dir.glob("*.desktop"):
                    try:
                        app_info = self._parse_desktop_file(desktop_file)
                        if app_info:
                            apps.append(app_info)
                    except Exception as e:
                        logger.debug(f"解析desktop文件失败 {desktop_file}: {e}")
        
        # 扫描bin目录
        bin_dirs = [
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path.home() / ".local" / "bin"
        ]
        
        for bin_dir in bin_dirs:
            if bin_dir.exists():
                for exe_file in bin_dir.iterdir():
                    if exe_file.is_file() and self.is_executable(exe_file):
                        apps.append({
                            "name": exe_file.name,
                            "path": str(exe_file),
                            "source": "bin_directory"
                        })
        
        return apps
    
    def _get_macos_apps(self) -> List[Dict]:
        """获取macOS应用列表"""
        apps = []
        
        # 扫描Applications目录
        app_dirs = [
            Path("/Applications"),
            Path("/System/Applications"),
            Path.home() / "Applications"
        ]
        
        for app_dir in app_dirs:
            if app_dir.exists():
                for app_file in app_dir.glob("*.app"):
                    try:
                        # .app实际上是目录
                        info_file = app_file / "Contents" / "Info.plist"
                        if info_file.exists():
                            app_info = self._parse_plist_file(info_file)
                            if app_info:
                                app_info["path"] = str(app_file)
                                app_info["source"] = "applications_directory"
                                apps.append(app_info)
                    except Exception as e:
                        logger.debug(f"解析.app文件失败 {app_file}: {e}")
        
        return apps
    
    def _parse_desktop_file(self, desktop_path: Path) -> Optional[Dict]:
        """解析Linux desktop文件"""
        try:
            with open(desktop_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            app_info = {
                "source": "desktop_entry",
                "desktop_file": str(desktop_path)
            }
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Name='):
                    app_info["name"] = line[5:]
                elif line.startswith('Exec='):
                    exec_line = line[5:]
                    # 移除字段代码（%f, %U等）
                    exec_line = exec_line.split()[0]
                    app_info["path"] = exec_line
                elif line.startswith('Icon='):
                    app_info["icon"] = line[5:]
                elif line.startswith('Comment='):
                    app_info["description"] = line[8:]
            
            if "name" in app_info and "path" in app_info:
                return app_info
            
        except Exception as e:
            logger.debug(f"解析desktop文件失败: {e}")
        
        return None
    
    def _parse_plist_file(self, plist_path: Path) -> Optional[Dict]:
        """解析macOS plist文件"""
        try:
            import plistlib
            
            with open(plist_path, 'rb') as f:
                plist = plistlib.load(f)
            
            app_info = {
                "source": "plist"
            }
            
            if "CFBundleDisplayName" in plist:
                app_info["name"] = plist["CFBundleDisplayName"]
            elif "CFBundleName" in plist:
                app_info["name"] = plist["CFBundleName"]
            
            if "CFBundleExecutable" in plist:
                executable_path = plist_path.parent.parent / "MacOS" / plist["CFBundleExecutable"]
                if executable_path.exists():
                    app_info["path"] = str(executable_path)
            
            return app_info
            
        except ImportError:
            logger.debug("plistlib模块不可用，跳过plist解析")
        except Exception as e:
            logger.debug(f"解析plist文件失败: {e}")
        
        return None
    
    def launch_application(self, app_path: str, args: List[str] = None, 
                          working_dir: str = None, elevated: bool = False) -> subprocess.Popen:
        """启动应用程序"""
        if args is None:
            args = []
        
        cmd = [app_path] + args
        
        if self.os_type == OperatingSystem.WINDOWS:
            # Windows
            if elevated:
                # 使用runas命令提升权限
                cmd = ["runas", "/user:Administrator", " ".join(cmd)]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            return subprocess.Popen(
                cmd,
                cwd=working_dir,
                startupinfo=startupinfo,
                shell=elevated
            )
        
        elif self.os_type in [OperatingSystem.LINUX, OperatingSystem.MACOS]:
            # Unix-like系统
            if elevated:
                # 使用sudo提升权限
                cmd = ["sudo"] + cmd
            
            return subprocess.Popen(
                cmd,
                cwd=working_dir,
                start_new_session=True
            )
        
        else:
            raise NotImplementedError(f"不支持的操作系统: {self.os_type}")
    
    def terminate_process(self, pid: int) -> bool:
        """终止进程"""
        try:
            if self.os_type == OperatingSystem.WINDOWS:
                import win32api
                import win32con
                handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, False, pid)
                win32api.TerminateProcess(handle, -1)
                win32api.CloseHandle(handle)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
            return True
        except Exception as e:
            logger.error(f"终止进程失败 {pid}: {e}")
            return False
    
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """获取进程信息"""
        try:
            import psutil
            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "cmdline": proc.cmdline(),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent(),
                "status": proc.status()
            }
        except Exception as e:
            logger.debug(f"获取进程信息失败 {pid}: {e}")
            return None

# 全局实例
_platform_utils = None

def get_platform_utils() -> PlatformUtils:
    """获取全局平台工具实例"""
    global _platform_utils
    if _platform_utils is None:
        _platform_utils = PlatformUtils()
    return _platform_utils