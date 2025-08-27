# universal_scanner.py - 通用应用扫描器
import os
import asyncio
import json
import subprocess
from pathlib import Path
from typing import List, Dict
import platform

class UniversalAppScanner:
    """通用应用扫描器 - 不绑定特定路径"""
    
    def __init__(self):
        self.apps = []
        self.system = platform.system().lower()
    
    async def scan_apps(self) -> List[Dict]:
        """扫描应用"""
        apps = []
        
        if self.system == "windows":
            apps = await self._scan_windows()
        elif self.system == "linux":
            apps = await self._scan_linux()
        elif self.system == "darwin":
            apps = await self._scan_macos()
        
        return apps
    
    async def _scan_windows(self) -> List[Dict]:
        """扫描Windows应用"""
        apps = []
        
        # 1. 扫描系统目录（只包含常用工具）
        system_apps = {
            "notepad": "记事本",
            "calc": "计算器",
            "mspaint": "画图",
            "cmd": "命令提示符",
            "write": "写字板"
        }
        
        system_dirs = [
            r"C:\Windows\System32",
            r"C:\Windows\SysWOW64"
        ]
        
        for dir_path in system_dirs:
            if os.path.exists(dir_path):
                for file in Path(dir_path).glob("*.exe"):
                    if file.stem in system_apps:
                        try:
                            apps.append({
                                "name": file.stem,
                                "path": str(file),
                                "display_name": system_apps[file.stem],
                                "type": "system"
                            })
                        except:
                            continue
        
        # 2. 扫描Program Files（只扫描常见应用）
        program_dirs = [
            r"C:\Program Files",
            r"C:\Program Files (x86)"
        ]
        
        # 常见应用名称
        common_apps = {
            "chrome": "Chrome",
            "firefox": "Firefox",
            "word": "Word",
            "excel": "Excel",
            "powerpnt": "PowerPoint",
            "winword": "Word",
            "excel": "Excel",
            "POWERPNT": "PowerPoint",
            "todesk": "ToDesk"
        }
        
        for dir_path in program_dirs:
            if os.path.exists(dir_path):
                for app_dir in Path(dir_path).iterdir():
                    if app_dir.is_dir():
                        # 检查目录名是否包含常见应用名
                        dir_name = app_dir.name.lower()
                        for app_key, app_display in common_apps.items():
                            if app_key in dir_name:
                                # 查找主执行文件
                                for exe_file in app_dir.glob("*.exe"):
                                    if exe_file.name.lower() == f"{app_key}.exe":
                                        try:
                                            apps.append({
                                                "name": app_key,
                                                "path": str(exe_file),
                                                "display_name": app_display,
                                                "type": "program"
                                            })
                                        except:
                                            continue
                                break
        
        # 3. 扫描用户桌面快捷方式
        desktop = Path(os.path.expanduser("~/Desktop"))
        if desktop.exists():
            for shortcut in desktop.glob("*.lnk"):
                try:
                    apps.append({
                        "name": shortcut.stem,
                        "path": str(shortcut),
                        "display_name": shortcut.stem,
                        "type": "shortcut"
                    })
                except:
                    continue
        
        # 4. 扫描开始菜单
        start_menu = Path(os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"))
        if start_menu.exists():
            for shortcut in start_menu.rglob("*.lnk"):
                try:
                    apps.append({
                        "name": shortcut.stem,
                        "path": str(shortcut),
                        "display_name": shortcut.stem.replace(".lnk", ""),
                        "type": "start_menu"
                    })
                except:
                    continue
        
        return apps
    
    async def _scan_linux(self) -> List[Dict]:
        """扫描Linux应用"""
        apps = []
        
        # 1. 扫描/usr/bin和/usr/local/bin
        bin_dirs = ["/usr/bin", "/usr/local/bin", "/opt/bin"]
        
        for dir_path in bin_dirs:
            if os.path.exists(dir_path):
                for file in Path(dir_path).glob("*"):
                    if file.is_file() and os.access(file, os.X_OK):
                        try:
                            apps.append({
                                "name": file.name,
                                "path": str(file),
                                "display_name": file.name,
                                "type": "binary"
                            })
                        except:
                            continue
        
        # 2. 扫描桌面文件
        desktop_dirs = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications")
        ]
        
        for dir_path in desktop_dirs:
            if os.path.exists(dir_path):
                for desktop_file in Path(dir_path).glob("*.desktop"):
                    try:
                        app_info = self._parse_desktop_file(desktop_file)
                        if app_info:
                            apps.append(app_info)
                    except:
                        continue
        
        return apps
    
    async def _scan_macos(self) -> List[Dict]:
        """扫描macOS应用"""
        apps = []
        
        # 1. 扫描/Applications
        app_dirs = [
            "/Applications",
            "/System/Applications",
            os.path.expanduser("~/Applications")
        ]
        
        for dir_path in app_dirs:
            if os.path.exists(dir_path):
                for app_file in Path(dir_path).glob("*.app"):
                    try:
                        app_info = self._parse_macos_app(app_file)
                        if app_info:
                            apps.append(app_info)
                    except:
                        continue
        
        return apps
    
    def _is_main_executable(self, exe_file: Path) -> bool:
        """判断是否是主执行文件"""
        name = exe_file.stem.lower()
        
        # 排除一些明显不是主程序的文件
        exclude_patterns = [
            "uninstall", "setup", "install", "crash", "error",
            "helper", "service", "daemon", "updater"
        ]
        
        for pattern in exclude_patterns:
            if pattern in name:
                return False
        
        # 优先包含的文件
        include_patterns = [
            exe_file.name,  # 完全匹配
            exe_file.stem,  # 不带扩展名
            exe_file.parent.name  # 目录名
        ]
        
        return True
    
    def _parse_desktop_file(self, desktop_file: Path) -> Dict:
        """解析Linux desktop文件"""
        try:
            with open(desktop_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            app_info = {"type": "desktop"}
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Name='):
                    app_info["name"] = line[5:].strip()
                    app_info["display_name"] = line[5:].strip()
                elif line.startswith('Exec='):
                    exec_line = line[5:].strip()
                    # 移除参数
                    exec_line = exec_line.split()[0]
                    app_info["path"] = exec_line
                elif line.startswith('Icon='):
                    app_info["icon"] = line[5:].strip()
            
            if "name" in app_info and "path" in app_info:
                return app_info
            
        except Exception:
            pass
        
        return None
    
    def _parse_macos_app(self, app_file: Path) -> Dict:
        """解析macOS应用"""
        try:
            # 查找Info.plist
            info_plist = app_file / "Contents" / "Info.plist"
            if not info_plist.exists():
                return None
            
            # 尝试解析plist
            try:
                import plistlib
                with open(info_plist, 'rb') as f:
                    plist = plistlib.load(f)
                
                app_info = {
                    "name": app_file.stem,
                    "path": str(app_file),
                    "display_name": plist.get("CFBundleDisplayName", app_file.stem),
                    "type": "app"
                }
                
                return app_info
                
            except ImportError:
                # 如果没有plistlib，返回基本信息
                return {
                    "name": app_file.stem,
                    "path": str(app_file),
                    "display_name": app_file.stem,
                    "type": "app"
                }
                
        except Exception:
            pass
        
        return None

class UniversalAppLauncher:
    """通用应用启动器"""
    
    def __init__(self):
        self.scanner = UniversalAppScanner()
        self.running_processes = {}
        self.launch_history = []
    
    async def get_apps(self) -> List[Dict]:
        """获取应用列表"""
        if not self.scanner.apps:
            self.scanner.apps = await self.scanner.scan_apps()
        return self.scanner.apps
    
    async def launch_app(self, app_name: str) -> Dict:
        """启动应用"""
        apps = await self.get_apps()
        
        # 查找应用
        app = None
        for a in apps:
            if (app_name.lower() in a["name"].lower() or 
                app_name.lower() in a["display_name"].lower()):
                app = a
                break
        
        if not app:
            return {
                "success": False,
                "message": f"未找到应用: {app_name}",
                "available_apps": [a["display_name"] for a in apps[:10]]
            }
        
        try:
            # 启动应用
            if app["type"] == "shortcut" and app["path"].endswith(".lnk"):
                # Windows快捷方式
                proc = subprocess.Popen([app["path"]], shell=True)
            elif app["type"] == "desktop":
                # Linux desktop文件
                proc = subprocess.Popen(["gtk-launch", app["name"]])
            elif app["type"] == "app":
                # macOS应用
                proc = subprocess.Popen(["open", app["path"]])
            else:
                # 普通可执行文件
                proc = subprocess.Popen([app["path"]])
            
            # 记录启动历史
            self.launch_history.append({
                "app_name": app["display_name"],
                "path": app["path"],
                "success": True,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return {
                "success": True,
                "message": f"已启动应用: {app['display_name']}",
                "process_id": proc.pid,
                "app_name": app["display_name"]
            }
            
        except Exception as e:
            # 记录失败历史
            self.launch_history.append({
                "app_name": app["display_name"],
                "path": app["path"],
                "success": False,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return {
                "success": False,
                "message": f"启动失败: {str(e)}",
                "app_name": app["display_name"]
            }

# 测试
async def test_universal():
    """测试通用版本"""
    launcher = UniversalAppLauncher()
    
    print("=== 通用应用扫描器测试 ===")
    print(f"系统: {platform.system()}")
    
    apps = await launcher.get_apps()
    print(f"找到 {len(apps)} 个应用")
    
    if apps:
        print("\n前10个应用:")
        for i, app in enumerate(apps[:10], 1):
            print(f"{i}. {app['display_name']} ({app['type']})")
        
        print("\n测试启动记事本...")
        result = await launcher.launch_app("notepad")
        print(f"结果: {result}")

if __name__ == "__main__":
    asyncio.run(test_universal())