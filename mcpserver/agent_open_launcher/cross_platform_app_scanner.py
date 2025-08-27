# cross_platform_app_scanner.py - 跨平台应用扫描器
import os
import asyncio
import json
import time
import logging
import hashlib
from typing import List, Dict, Optional, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from platform_utils import get_platform_utils, OperatingSystem

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppSource(Enum):
    """应用来源枚举"""
    REGISTRY_APP_PATHS = "registry_app_paths"
    REGISTRY_UNINSTALL = "registry_uninstall"
    REGISTRY_USER_UNINSTALL = "registry_user_uninstall"
    DESKTOP_ENTRY = "desktop_entry"  # Linux .desktop文件
    APPLICATIONS_DIR = "applications_directory"  # macOS Applications目录
    BIN_DIRECTORY = "bin_directory"  # Unix bin目录
    SHORTCUT_START_MENU = "shortcut_start_menu"
    SHORTCUT_DESKTOP = "shortcut_desktop"
    SHORTCUT_COMMON = "shortcut_common"

@dataclass
class AppInfo:
    """应用信息数据类"""
    name: str
    path: str
    source: AppSource
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    install_location: Optional[str] = None
    publisher: Optional[str] = None
    version: Optional[str] = None
    last_modified: Optional[float] = None
    file_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name
        if not self.description:
            self.description = f"应用: {self.display_name}"

class CrossPlatformAppScanner:
    """跨平台应用扫描器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        self.platform = get_platform_utils()
        self.apps_cache: List[AppInfo] = []
        self.app_name_map: Dict[str, AppInfo] = {}
        self._scan_completed = False
        self._scan_lock = asyncio.Lock()
        self._cache_file = os.path.join(os.path.dirname(__file__), "app_cache.json")
        self._last_scan_time = 0
        self._scan_stats = {
            "total_scanned": 0,
            "registry_count": 0,
            "desktop_entry_count": 0,
            "bin_count": 0,
            "shortcut_count": 0,
            "error_count": 0,
            "scan_duration": 0
        }
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            "cache_enabled": True,
            "cache_ttl": 3600,
            "max_apps": 1000,
            # Windows扫描配置
            "scan_registry": True,
            "scan_shortcuts": True,
            # Linux扫描配置
            "scan_desktop_entries": True,
            "scan_bin_directories": True,
            # macOS扫描配置
            "scan_applications": True,
            # 通用配置
            "debug_mode": False,
            "enable_incremental": True,
            "verify_executables": True
        }
    
    async def ensure_scan_completed(self, force_refresh: bool = False) -> None:
        """确保扫描已完成"""
        current_time = time.time()
        
        need_scan = (
            not self._scan_completed or 
            force_refresh or
            (self.config["cache_enabled"] and 
             current_time - self._last_scan_time > self.config["cache_ttl"])
        )
        
        if need_scan:
            async with self._scan_lock:
                need_scan = (
                    not self._scan_completed or 
                    force_refresh or
                    (self.config["cache_enabled"] and 
                     current_time - self._last_scan_time > self.config["cache_ttl"])
                )
                
                if need_scan:
                    await self._scan_all_sources()
                    self._scan_completed = True
                    self._last_scan_time = current_time
    
    async def _scan_all_sources(self) -> None:
        """扫描所有应用来源"""
        start_time = time.time()
        logger.info(f"🔍 开始扫描 {self.platform.os_type.value} 系统应用...")
        
        apps = []
        tasks = []
        
        # 根据平台创建扫描任务
        try:
            if self.platform.os_type == OperatingSystem.WINDOWS:
                if self.config.get("scan_registry", False):
                    tasks.append(self._scan_windows_registry())
                if self.config.get("scan_shortcuts", False):
                    tasks.append(self._scan_windows_shortcuts())
            
            elif self.platform.os_type == OperatingSystem.LINUX:
                if self.config.get("scan_desktop_entries", False):
                    tasks.append(self._scan_linux_desktop_entries())
                if self.config.get("scan_bin_directories", False):
                    tasks.append(self._scan_linux_bin_directories())
            
            elif self.platform.os_type == OperatingSystem.MACOS:
                if self.config.get("scan_applications", False):
                    tasks.append(self._scan_macos_applications())
        except Exception as e:
            logger.error(f"创建扫描任务失败: {e}")
            self._scan_stats["error_count"] += 1
          
        # 并行执行扫描任务
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"扫描任务失败: {result}")
                    self._scan_stats["error_count"] += 1
                elif isinstance(result, list):
                    apps.extend(result)
        
        # 处理和去重
        unique_apps = self._process_and_deduplicate(apps)
        
        # 更新缓存
        self.apps_cache = unique_apps
        self._build_name_map()
        
        # 更新统计信息
        self._scan_stats["total_scanned"] = len(apps)
        self._scan_stats["scan_duration"] = time.time() - start_time
        self._update_scan_stats()
        
        # 保存缓存
        if self.config["cache_enabled"]:
            await self._save_cache()
        
        logger.info(f"✅ 扫描完成，共找到 {len(unique_apps)} 个应用 "
                   f"(原始: {len(apps)}, 耗时: {self._scan_stats['scan_duration']:.2f}s)")
    
    async def _scan_windows_registry(self) -> List[AppInfo]:
        """扫描Windows注册表"""
        apps = []
        
        if self.platform.os_type != OperatingSystem.WINDOWS:
            return apps
        
        try:
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
                                        if exe_path and os.path.exists(exe_path):
                                            # 获取友好名称
                                            try:
                                                friendly_name, _ = winreg.QueryValueEx(app_key, "FriendlyAppName")
                                                display_name = friendly_name if friendly_name else app_name[:-4]
                                            except:
                                                display_name = app_name[:-4]
                                            
                                            file_info = self._get_file_info(exe_path)
                                            
                                            app = AppInfo(
                                                name=app_name[:-4],
                                                path=exe_path,
                                                source=AppSource.REGISTRY_APP_PATHS,
                                                display_name=display_name,
                                                last_modified=file_info["modified"],
                                                file_hash=file_info["hash"]
                                            )
                                            apps.append(app)
                                    except Exception as e:
                                        logger.debug(f"处理App Path项失败 {app_name}: {e}")
                        except Exception as e:
                            logger.debug(f"枚举App Path键失败 {i}: {e}")
            except PermissionError as e:
                logger.warning(f"权限不足，无法访问App Paths注册表: {e}")
                self._scan_stats["error_count"] += 1
            except Exception as e:
                logger.error(f"扫描App Paths注册表失败: {e}")
                self._scan_stats["error_count"] += 1
            
            # 也尝试扫描CurrentUser的注册表
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            app_name = winreg.EnumKey(key, i)
                            if app_name.endswith('.exe'):
                                app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{app_name}"
                                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, app_key_path) as app_key:
                                    try:
                                        exe_path, _ = winreg.QueryValueEx(app_key, "")
                                        if exe_path and os.path.exists(exe_path):
                                            display_name = app_name[:-4]
                                            file_info = self._get_file_info(exe_path)
                                            
                                            app = AppInfo(
                                                name=app_name[:-4],
                                                path=exe_path,
                                                source=AppSource.REGISTRY_APP_PATHS,
                                                display_name=display_name,
                                                last_modified=file_info["modified"],
                                                file_hash=file_info["hash"]
                                            )
                                            apps.append(app)
                                    except Exception as e:
                                        logger.debug(f"处理CurrentUser App Path项失败 {app_name}: {e}")
                        except Exception as e:
                            logger.debug(f"枚举CurrentUser App Path键失败 {i}: {e}")
            except PermissionError as e:
                logger.warning(f"权限不足，无法访问CurrentUser App Paths注册表: {e}")
            except Exception as e:
                logger.debug(f"扫描CurrentUser App Paths注册表失败: {e}")
            
            self._scan_stats["registry_count"] += len(apps)
            
        except ImportError:
            logger.warning("winreg模块不可用，跳过Windows注册表扫描")
        
        return apps
    
    async def _scan_windows_shortcuts(self) -> List[AppInfo]:
        """扫描Windows快捷方式"""
        apps = []
        
        if self.platform.os_type != OperatingSystem.WINDOWS:
            return apps
        
        try:
            import win32com.client
            
            # 扫描快捷方式目录
            shortcut_dirs = self.platform.app_dirs["start_menu"] + self.platform.app_dirs["desktop"]
            
            for shortcut_dir in shortcut_dirs:
                if shortcut_dir.exists():
                    for lnk_path in shortcut_dir.rglob("*.lnk"):
                        try:
                            app_info = self._parse_windows_shortcut(lnk_path)
                            if app_info:
                                apps.append(app_info)
                        except Exception as e:
                            logger.debug(f"解析快捷方式失败 {lnk_path}: {e}")
            
            self._scan_stats["shortcut_count"] += len(apps)
            
        except ImportError:
            logger.warning("win32com模块不可用，跳过快捷方式扫描")
        
        return apps
    
    def _parse_windows_shortcut(self, lnk_path: Path) -> Optional[AppInfo]:
        """解析Windows快捷方式"""
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(lnk_path))
            target_path = shortcut.TargetPath
            
            if not target_path or not os.path.exists(target_path):
                return None
            
            # 只处理.exe文件
            if not target_path.lower().endswith('.exe'):
                return None
            
            # 获取应用名称
            app_name = lnk_path.stem
            
            # 获取描述
            try:
                description = shortcut.Description
                if description and description.strip():
                    app_name = description
            except:
                pass
            
            # 获取文件信息
            file_info = self._get_file_info(target_path)
            
            return AppInfo(
                name=app_name,
                path=target_path,
                source=AppSource.SHORTCUT_START_MENU,
                display_name=app_name,
                shortcut_path=str(lnk_path),
                last_modified=file_info["modified"],
                file_hash=file_info["hash"]
            )
            
        except Exception as e:
            logger.debug(f"解析快捷方式失败 {lnk_path}: {e}")
            return None
    
    async def _scan_linux_desktop_entries(self) -> List[AppInfo]:
        """扫描Linux desktop文件"""
        apps = []
        
        if self.platform.os_type != OperatingSystem.LINUX:
            return apps
        
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path.home() / ".local" / "share" / "applications"
        ]
        
        for desktop_dir in desktop_dirs:
            if desktop_dir.exists():
                for desktop_file in desktop_dir.glob("*.desktop"):
                    try:
                        app_info = self._parse_linux_desktop_entry(desktop_file)
                        if app_info:
                            apps.append(app_info)
                    except Exception as e:
                        logger.debug(f"解析desktop文件失败 {desktop_file}: {e}")
        
        self._scan_stats["desktop_entry_count"] += len(apps)
        
        return apps
    
    def _parse_linux_desktop_entry(self, desktop_path: Path) -> Optional[AppInfo]:
        """解析Linux desktop文件"""
        try:
            with open(desktop_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            app_info = {
                "source": AppSource.DESKTOP_ENTRY,
                "desktop_file": str(desktop_path)
            }
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Name='):
                    app_info["name"] = line[5:]
                elif line.startswith('Name['):  # 本地化名称
                    continue
                elif line.startswith('Exec='):
                    exec_line = line[5:]
                    # 移除字段代码
                    exec_line = exec_line.split()[0]
                    if exec_line.startswith('/') and os.path.exists(exec_line):
                        app_info["path"] = exec_line
                    else:
                        # 在PATH中查找
                        exe_path = self.platform.find_executable(exec_line)
                        if exe_path:
                            app_info["path"] = str(exe_path)
                        else:
                            continue
                elif line.startswith('Icon='):
                    app_info["icon"] = line[5:]
                elif line.startswith('Comment='):
                    app_info["description"] = line[8:]
            
            if "name" in app_info and "path" in app_info:
                file_info = self._get_file_info(app_info["path"])
                return AppInfo(
                    name=app_info["name"],
                    path=app_info["path"],
                    source=AppSource.DESKTOP_ENTRY,
                    display_name=app_info["name"],
                    description=app_info.get("description"),
                    icon=app_info.get("icon"),
                    last_modified=file_info["modified"],
                    file_hash=file_info["hash"]
                )
            
        except Exception as e:
            logger.debug(f"解析desktop文件失败: {e}")
        
        return None
    
    async def _scan_linux_bin_directories(self) -> List[AppInfo]:
        """扫描Linux bin目录"""
        apps = []
        
        if self.platform.os_type != OperatingSystem.LINUX:
            return apps
        
        bin_dirs = [
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path.home() / ".local" / "bin"
        ]
        
        for bin_dir in bin_dirs:
            if bin_dir.exists():
                for exe_file in bin_dir.iterdir():
                    if exe_file.is_file() and self.platform.is_executable(exe_file):
                        try:
                            file_info = self._get_file_info(str(exe_file))
                            
                            app = AppInfo(
                                name=exe_file.name,
                                path=str(exe_file),
                                source=AppSource.BIN_DIRECTORY,
                                last_modified=file_info["modified"],
                                file_hash=file_info["hash"]
                            )
                            apps.append(app)
                        except Exception as e:
                            logger.debug(f"处理bin文件失败 {exe_file}: {e}")
        
        self._scan_stats["bin_count"] += len(apps)
        
        return apps
    
    async def _scan_macos_applications(self) -> List[AppInfo]:
        """扫描macOS Applications目录"""
        apps = []
        
        if self.platform.os_type != OperatingSystem.MACOS:
            return apps
        
        app_dirs = [
            Path("/Applications"),
            Path("/System/Applications"),
            Path.home() / "Applications"
        ]
        
        for app_dir in app_dirs:
            if app_dir.exists():
                for app_file in app_dir.glob("*.app"):
                    try:
                        app_info = self._parse_macos_app(app_file)
                        if app_info:
                            apps.append(app_info)
                    except Exception as e:
                        logger.debug(f"解析.app文件失败 {app_file}: {e}")
        
        return apps
    
    def _parse_macos_app(self, app_path: Path) -> Optional[AppInfo]:
        """解析macOS .app文件"""
        try:
            # 查找Info.plist
            info_plist = app_path / "Contents" / "Info.plist"
            if not info_plist.exists():
                return None
            
            # 解析plist
            try:
                import plistlib
                with open(info_plist, 'rb') as f:
                    plist = plistlib.load(f)
            except ImportError:
                logger.debug("plistlib不可用，跳过plist解析")
                return None
            
            # 获取应用信息
            if "CFBundleDisplayName" in plist:
                display_name = plist["CFBundleDisplayName"]
            elif "CFBundleName" in plist:
                display_name = plist["CFBundleName"]
            else:
                display_name = app_path.stem
            
            # 查找可执行文件
            if "CFBundleExecutable" in plist:
                executable_path = app_path / "Contents" / "MacOS" / plist["CFBundleExecutable"]
                if executable_path.exists():
                    file_info = self._get_file_info(str(executable_path))
                    
                    return AppInfo(
                        name=app_path.stem,
                        path=str(executable_path),
                        source=AppSource.APPLICATIONS_DIR,
                        display_name=display_name,
                        install_location=str(app_path),
                        version=plist.get("CFBundleShortVersionString"),
                        last_modified=file_info["modified"],
                        file_hash=file_info["hash"]
                    )
            
        except Exception as e:
            logger.debug(f"解析.app文件失败 {app_path}: {e}")
        
        return None
    
    def _get_file_info(self, file_path: str) -> Dict:
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            file_hash = None
            
            # 计算文件哈希（仅用于调试）
            if self.config["debug_mode"]:
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read(8192)).hexdigest()[:8]
                except:
                    pass
            
            return {
                "modified": stat.st_mtime,
                "size": stat.st_size,
                "hash": file_hash
            }
        except Exception as e:
            logger.debug(f"获取文件信息失败 {file_path}: {e}")
            return {"modified": 0, "size": 0, "hash": None}
    
    def _process_and_deduplicate(self, apps: List[AppInfo]) -> List[AppInfo]:
        """处理和去重应用列表"""
        unique_apps = {}
        seen_paths = set()
        
        for app in apps:
            # 跳过无效路径
            if not app.path or not os.path.exists(app.path):
                continue
            
            # 检查是否已存在相同路径
            if app.path in seen_paths:
                continue
            seen_paths.add(app.path)
            
            # 去重逻辑
            key = app.name.lower()
            if key not in unique_apps:
                unique_apps[key] = app
            else:
                # 根据来源优先级选择
                existing = unique_apps[key]
                if self._get_source_priority(app.source) > self._get_source_priority(existing.source):
                    unique_apps[key] = app
        
        # 转换为列表并排序
        result = list(unique_apps.values())
        result.sort(key=lambda x: x.display_name.lower())
        
        # 限制数量
        max_apps = self.config.get("max_apps", 1000)
        if len(result) > max_apps:
            result = result[:max_apps]
            logger.warning(f"应用数量超过限制，已截断至 {max_apps} 个")
        
        return result
    
    def _get_source_priority(self, source: AppSource) -> int:
        """获取来源优先级"""
        priorities = {
            AppSource.DESKTOP_ENTRY: 5,
            AppSource.APPLICATIONS_DIR: 5,
            AppSource.SHORTCUT_START_MENU: 4,
            AppSource.SHORTCUT_DESKTOP: 4,
            AppSource.SHORTCUT_COMMON: 4,
            AppSource.REGISTRY_APP_PATHS: 3,
            AppSource.REGISTRY_UNINSTALL: 2,
            AppSource.REGISTRY_USER_UNINSTALL: 1,
            AppSource.BIN_DIRECTORY: 2
        }
        return priorities.get(source, 0)
    
    def _build_name_map(self) -> None:
        """构建应用名称映射"""
        self.app_name_map.clear()
        for app in self.apps_cache:
            # 主名称
            self.app_name_map[app.name.lower()] = app
            # 显示名称
            if app.display_name.lower() != app.name.lower():
                self.app_name_map[app.display_name.lower()] = app
            # 不带扩展名的名称
            if app.name.lower().endswith('.exe'):
                name_no_ext = app.name[:-4].lower()
                if name_no_ext not in self.app_name_map:
                    self.app_name_map[name_no_ext] = app
    
    def _update_scan_stats(self) -> None:
        """更新扫描统计"""
        logger.info(
            f"扫描统计: 总计={self._scan_stats['total_scanned']}, "
            f"注册表={self._scan_stats['registry_count']}, "
            f"desktop={self._scan_stats['desktop_entry_count']}, "
            f"bin={self._scan_stats['bin_count']}, "
            f"快捷方式={self._scan_stats['shortcut_count']}, "
            f"错误={self._scan_stats['error_count']}, "
            f"耗时={self._scan_stats['scan_duration']:.2f}s"
        )
    
    async def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            cache_data = {
                "timestamp": self._last_scan_time,
                "apps": [asdict(app) for app in self.apps_cache],
                "stats": self._scan_stats
            }
            
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"缓存已保存到 {self._cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    async def _load_cache(self) -> bool:
        """从文件加载缓存"""
        if not os.path.exists(self._cache_file):
            return False
        
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            if time.time() - cache_data["timestamp"] > self.config["cache_ttl"]:
                return False
            
            # 加载应用数据
            self.apps_cache = []
            for app_data in cache_data["apps"]:
                app_data["source"] = AppSource(app_data["source"])
                self.apps_cache.append(AppInfo(**app_data))
            
            self._build_name_map()
            self._scan_stats = cache_data.get("stats", self._scan_stats)
            
            logger.info(f"已从缓存加载 {len(self.apps_cache)} 个应用")
            return True
            
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return False
    
    async def get_apps(self, force_refresh: bool = False) -> List[AppInfo]:
        """获取应用列表"""
        await self.ensure_scan_completed(force_refresh)
        return self.apps_cache.copy()
    
    async def find_app(self, name: str, fuzzy: bool = True) -> Optional[AppInfo]:
        """查找应用"""
        await self.ensure_scan_completed()
        
        name_lower = name.lower()
        
        # 精确匹配
        if name_lower in self.app_name_map:
            return self.app_name_map[name_lower]
        
        # 模糊匹配
        if fuzzy:
            for app_name, app in self.app_name_map.items():
                if (name_lower in app_name or 
                    app_name in name_lower or
                    name_lower in app.display_name.lower() or
                    app.display_name.lower() in name_lower):
                    return app
        
        return None
    
    async def refresh_apps(self) -> None:
        """刷新应用列表"""
        async with self._scan_lock:
            self._scan_completed = False
            await self._scan_all_sources()
            self._scan_completed = True
    
    async def get_app_info_for_llm(self) -> Dict:
        """获取供LLM使用的应用信息"""
        await self.ensure_scan_completed()
        
        app_names = [app.display_name for app in self.apps_cache]
        
        return {
            "total_count": len(app_names),
            "apps": app_names[:100],  # 限制返回数量
            "has_more": len(app_names) > 100,
            "scan_stats": {
                "last_scan": self._last_scan_time,
                "duration": self._scan_stats["scan_duration"],
                "platform": self.platform.os_type.value
            }
        }
    
    def get_scan_stats(self) -> Dict:
        """获取扫描统计信息"""
        return self._scan_stats.copy()

# 全局实例
_cross_platform_scanner = None

def get_cross_platform_scanner(config: Dict = None) -> CrossPlatformAppScanner:
    """获取全局扫描器实例"""
    global _cross_platform_scanner
    if _cross_platform_scanner is None:
        _cross_platform_scanner = CrossPlatformAppScanner(config)
    return _cross_platform_scanner

async def refresh_cross_platform_apps():
    """刷新跨平台应用列表"""
    scanner = get_cross_platform_scanner()
    await scanner.refresh_apps()