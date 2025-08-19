# comprehensive_app_scanner.py # 综合应用扫描器（注册表+快捷方式）
import winreg  # Windows注册表 #
import os  # 操作系统 #
import glob  # 文件匹配 #
from typing import List, Dict, Optional  # 类型 #
import json  # JSON #

class ComprehensiveAppScanner:
    """综合应用扫描器：结合注册表扫描和快捷方式扫描 #"""
    
    def __init__(self):
        self.apps_cache = []  # 应用缓存 #
        self._scan_all_sources()  # 扫描所有来源 #
    
    def _scan_all_sources(self):
        """扫描所有应用来源 #"""
        apps = []
        
        # 1. 扫描注册表 #
        registry_apps = self._scan_registry()
        apps.extend(registry_apps)
        
        # 2. 扫描快捷方式 #
        shortcut_apps = self._scan_shortcuts()
        apps.extend(shortcut_apps)
        
        # 3. 去重并合并，优先选择快捷方式 #
        unique_apps = self._merge_and_deduplicate(apps)
        
        self.apps_cache = unique_apps
        print(f"✅ 综合扫描完成，共找到 {len(self.apps_cache)} 个应用")
    
    def _scan_registry(self) -> List[Dict]:
        """扫描Windows注册表获取应用信息 #"""
        apps = []
        
        # 扫描HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        app_name = winreg.EnumKey(key, i)
                        if app_name.endswith('.exe'):
                            app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{app_name}"
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, app_key_path) as app_key:
                                try:
                                    # 获取默认值（通常是可执行文件路径）
                                    exe_path, _ = winreg.QueryValueEx(app_key, "")
                                    if exe_path and os.path.exists(exe_path):
                                        # 获取应用名称（去掉.exe后缀）
                                        display_name = app_name[:-4] if app_name.endswith('.exe') else app_name
                                        
                                        # 尝试从注册表获取更友好的显示名称
                                        try:
                                            friendly_name, _ = winreg.QueryValueEx(app_key, "FriendlyAppName")
                                            if friendly_name:
                                                display_name = friendly_name
                                        except:
                                            pass
                                        
                                        apps.append({
                                            "name": display_name,
                                            "path": exe_path,
                                            "type": "registry",
                                            "source": "registry",
                                            "description": f"从注册表扫描到的应用: {display_name}"
                                        })
                                except:
                                    pass
                    except:
                        continue
        except Exception as e:
            print(f"扫描App Paths注册表失败: {e}")
        
        # 扫描HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{subkey_name}"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path) as subkey:
                            try:
                                # 获取显示名称
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                # 获取安装位置
                                install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                
                                if display_name and install_location:
                                    # 查找可执行文件
                                    exe_files = self._find_exe_files(install_location)
                                    for exe_path in exe_files:
                                        apps.append({
                                            "name": display_name,
                                            "path": exe_path,
                                            "type": "uninstall_registry",
                                            "source": "registry",
                                            "description": f"从卸载注册表扫描到的应用: {display_name}"
                                        })
                            except:
                                pass
                    except:
                        continue
        except Exception as e:
            print(f"扫描Uninstall注册表失败: {e}")
        
        # 扫描HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{subkey_name}"
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path) as subkey:
                            try:
                                # 获取显示名称
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                # 获取安装位置
                                install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                
                                if display_name and install_location:
                                    # 查找可执行文件
                                    exe_files = self._find_exe_files(install_location)
                                    for exe_path in exe_files:
                                        apps.append({
                                            "name": display_name,
                                            "path": exe_path,
                                            "type": "user_uninstall_registry",
                                            "source": "registry",
                                            "description": f"从用户卸载注册表扫描到的应用: {display_name}"
                                        })
                            except:
                                pass
                    except:
                        continue
        except Exception as e:
            print(f"扫描用户Uninstall注册表失败: {e}")
        
        return apps
    
    def _scan_shortcuts(self) -> List[Dict]:
        """扫描快捷方式获取应用信息 #"""
        apps = []
        
        # 扫描开始菜单快捷方式
        start_menu_paths = [
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expanduser(r"~\Desktop")
        ]
        
        for start_menu_path in start_menu_paths:
            if os.path.exists(start_menu_path):
                lnk_files = self._find_lnk_files(start_menu_path)
                for lnk_path in lnk_files:
                    try:
                        app_info = self._parse_shortcut(lnk_path)
                        if app_info:
                            apps.append(app_info)
                    except Exception as e:
                        print(f"解析快捷方式失败 {lnk_path}: {e}")
        
        return apps
    
    def _find_lnk_files(self, directory: str) -> List[str]:
        """在指定目录中查找.lnk文件 #"""
        lnk_files = []
        try:
            # 递归查找所有.lnk文件
            pattern = os.path.join(directory, "**", "*.lnk")
            lnk_files = glob.glob(pattern, recursive=True)
        except Exception as e:
            print(f"查找快捷方式失败 {directory}: {e}")
        
        return lnk_files
    
    def _parse_shortcut(self, lnk_path: str) -> Optional[Dict]:
        """解析快捷方式文件 #"""
        try:
            import win32com.client
            
            # 使用WScript.Shell解析快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target_path = shortcut.TargetPath
            
            if target_path and os.path.exists(target_path) and target_path.lower().endswith('.exe'):
                # 获取应用名称（从快捷方式文件名）
                app_name = os.path.splitext(os.path.basename(lnk_path))[0]
                
                # 尝试获取更友好的显示名称
                try:
                    description = shortcut.Description
                    if description:
                        app_name = description
                except:
                    pass
                
                return {
                    "name": app_name,
                    "path": target_path,
                    "type": "shortcut",
                    "source": "shortcut",
                    "shortcut_path": lnk_path,
                    "description": f"从快捷方式扫描到的应用: {app_name}"
                }
        except ImportError:
            print("win32com模块未安装，跳过快捷方式解析")
        except Exception as e:
            print(f"解析快捷方式失败 {lnk_path}: {e}")
        
        return None
    
    def _find_exe_files(self, directory: str) -> List[str]:
        """在指定目录中查找可执行文件 #"""
        exe_files = []
        if not os.path.exists(directory):
            return exe_files
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.exe'):
                        exe_path = os.path.join(root, file)
                        if os.path.exists(exe_path):
                            exe_files.append(exe_path)
        except:
            pass
        
        return exe_files
    
    def _merge_and_deduplicate(self, apps: List[Dict]) -> List[Dict]:
        """合并和去重应用列表，优先选择快捷方式 #"""
        unique_apps = {}
        
        for app in apps:
            name = app["name"]
            
            # 如果应用不存在，直接添加
            if name not in unique_apps:
                unique_apps[name] = app
            else:
                # 如果已存在，优先选择快捷方式
                existing_app = unique_apps[name]
                if app["source"] == "shortcut" and existing_app["source"] == "registry":
                    unique_apps[name] = app
        
        # 转换为列表并排序
        result = list(unique_apps.values())
        result.sort(key=lambda x: x["name"].lower())
        
        return result
    
    def get_apps(self) -> List[Dict]:
        """获取扫描到的应用列表 #"""
        return self.apps_cache.copy()
    
    def find_app_by_name(self, name: str) -> Optional[Dict]:
        """根据名称查找应用，支持智能匹配 #"""
        name_lower = name.lower()
        
        # 精确匹配
        for app in self.apps_cache:
            if app["name"].lower() == name_lower:
                return app
        
        # 模糊匹配（包含关系）
        for app in self.apps_cache:
            if name_lower in app["name"].lower() or app["name"].lower() in name_lower:
                return app
        
        return None
    
    def refresh_apps(self):
        """刷新应用列表 #"""
        self._scan_all_sources()
    
    def get_app_info_for_llm(self) -> Dict:
        """获取供LLM选择的应用信息格式 #"""
        apps = self.get_apps()
        app_list = []
        
        for app in apps:
            app_list.append({
                "name": app["name"],
                "description": app["description"],
                "type": app["type"],
                "source": app["source"]
            })
        
        return {
            "total_count": len(app_list),
            "apps": app_list,
            "usage_format": {
                "tool_name": "open",
                "app": "应用名称（从上述列表中选择）",
                "args": "启动参数（可选）"
            },
            "example": {
                "tool_name": "open",
                "app": "notepad",
                "args": ""
            }
        }

# 全局实例 #
_comprehensive_scanner = None

def get_comprehensive_scanner() -> ComprehensiveAppScanner:
    """获取全局综合扫描器实例 #"""
    global _comprehensive_scanner
    if _comprehensive_scanner is None:
        _comprehensive_scanner = ComprehensiveAppScanner()
    return _comprehensive_scanner

def refresh_comprehensive_apps():
    """刷新综合应用列表 #"""
    scanner = get_comprehensive_scanner()
    scanner.refresh_apps()
