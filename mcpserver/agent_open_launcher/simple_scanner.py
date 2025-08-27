# simple_scanner.py - 简化的应用扫描器
import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict

class SimpleAppScanner:
    """简化的应用扫描器 - 不需要管理员权限"""
    
    def __init__(self):
        self.apps = []
    
    async def scan_apps(self) -> List[Dict]:
        """扫描常见应用"""
        apps = []
        
        # 扫描常见应用路径
        common_paths = [
            # 系统应用
            r"C:\Windows\System32\notepad.exe",
            r"C:\Windows\System32\cmd.exe",
            r"C:\Windows\System32\mspaint.exe",
            r"C:\Windows\System32\calc.exe",
            
            # 程序文件
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE",
            
            # 常见工具
            r"C:\Program Files\7-Zip\7zFM.exe",
            r"C:\Program Files\Bandizip\Bandizip.exe",
            r"C:\Program Files\Notepad++\notepad++.exe",
            
            # 用户目录
            os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
            os.path.expanduser("~/AppData/Local/Microsoft/WindowsApps/Microsoft.WindowsNotepad.exe"),
            
            # ToDesk常见安装路径
            r"C:\Program Files\ToDesk\ToDesk.exe",
            os.path.expanduser("~/AppData/Local/ToDesk/ToDesk.exe"),
        ]
        
        # 检查每个路径
        for path in common_paths:
            if os.path.exists(path):
                app_name = Path(path).stem
                apps.append({
                    "name": app_name,
                    "path": path,
                    "display_name": self._get_display_name(app_name)
                })
        
        # 扫描桌面快捷方式
        desktop_path = Path(os.path.expanduser("~/Desktop"))
        if desktop_path.exists():
            for shortcut in desktop_path.glob("*.lnk"):
                try:
                    # 这里可以解析.lnk文件，但需要额外的库
                    apps.append({
                        "name": shortcut.stem,
                        "path": str(shortcut),
                        "display_name": shortcut.stem,
                        "type": "shortcut"
                    })
                except:
                    pass
        
        return apps
    
    def _get_display_name(self, name: str) -> str:
        """获取显示名称"""
        name_map = {
            "chrome": "Chrome浏览器",
            "firefox": "Firefox浏览器",
            "notepad": "记事本",
            "calc": "计算器",
            "mspaint": "画图",
            "cmd": "命令提示符",
            "WINWORD": "Word",
            "EXCEL": "Excel",
            "POWERPNT": "PowerPoint",
            "7zFM": "7-Zip文件管理器",
            "Bandizip": "Bandizip压缩工具",
            "notepad++": "Notepad++",
            "ToDesk": "ToDesk远程控制"
        }
        return name_map.get(name.lower(), name)

# 创建简单的应用启动器
class SimpleAppLauncher:
    """简化的应用启动器"""
    
    def __init__(self):
        self.scanner = SimpleAppScanner()
        self.running_processes = {}
    
    async def get_apps(self) -> List[Dict]:
        """获取应用列表"""
        return await self.scanner.scan_apps()
    
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
                "available_apps": [a["display_name"] for a in apps[:5]]
            }
        
        try:
            import subprocess
            proc = subprocess.Popen([app["path"]])
            
            return {
                "success": True,
                "message": f"已启动应用: {app['display_name']}",
                "process_id": proc.pid,
                "app_name": app["display_name"]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"启动失败: {str(e)}",
                "app_name": app["display_name"]
            }

# 测试
async def test_simple():
    """测试简化版本"""
    launcher = SimpleAppLauncher()
    
    print("扫描应用...")
    apps = await launcher.get_apps()
    print(f"找到 {len(apps)} 个应用:")
    for app in apps:
        print(f"  - {app['display_name']}: {app['path']}")
    
    print("\n测试启动记事本...")
    result = await launcher.launch_app("notepad")
    print(f"结果: {result}")

if __name__ == "__main__":
    asyncio.run(test_simple())