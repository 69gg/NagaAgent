# enhanced_app_scanner.py - 增强版应用扫描器
import winreg  # Windows注册表
import os  # 操作系统
import glob  # 文件匹配
import asyncio  # 异步
import json  # JSON
import time  # 时间
import logging  # 日志
import hashlib  # 哈希
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppSource(Enum):
    """应用来源枚举"""
    REGISTRY_APP_PATHS = "registry_app_paths"
    REGISTRY_UNINSTALL = "registry_uninstall"
    REGISTRY_USER_UNINSTALL = "registry_user_uninstall"
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
    shortcut_path: Optional[str] = None
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

class EnhancedAppScanner:
    """增强版应用扫描器 - 支持增量扫描、缓存优化和详细日志"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        self.apps_cache: List[AppInfo] = []
        self.app_name_map: Dict[str, AppInfo] = {}
        self._scan_completed = False
        self._scan_lock = asyncio.Lock()
        self._cache_file = os.path.join(os.path.dirname(__file__), "app_cache.json")
        self._last_scan_time = 0
        self._scan_stats = {
            "total_scanned": 0,
            "registry_count": 0,
            "shortcut_count": 0,
            "error_count": 0,
            "scan_duration": 0
        }
        
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            "cache_enabled": True,
            "cache_ttl": 3600,  # 1小时
            "max_apps": 1000,
            "scan_app_paths": True,
            "scan_uninstall": True,
            "scan_user_uninstall": True,
            "scan_shortcuts": True,
            "scan_start_menu": True,
            "scan_desktop": True,
            "debug_mode": False,
            "enable_incremental": True,
            "verify_executables": True
        }
    
    async def ensure_scan_completed(self, force_refresh: bool = False) -> None:
        """确保扫描已完成，支持强制刷新"""
        current_time = time.time()
        
        # 检查是否需要重新扫描
        need_scan = (
            not self._scan_completed or 
            force_refresh or
            (self.config["cache_enabled"] and 
             current_time - self._last_scan_time > self.config["cache_ttl"])
        )
        
        if need_scan:
            async with self._scan_lock:
                # 双重检查
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
        logger.info("🔍 开始扫描所有应用来源...")
        
        apps = []
        tasks = []
        
        # 创建扫描任务
        if self.config["scan_app_paths"]:
            tasks.append(self._scan_registry_app_paths())
        
        if self.config["scan_uninstall"]:
            tasks.append(self._scan_registry_uninstall())
        
        if self.config["scan_user_uninstall"]:
            tasks.append(self._scan_registry_user_uninstall())
        
        if self.config["scan_shortcuts"] and self.config["scan_start_menu"]:
            tasks.append(self._scan_start_menu_shortcuts())
        
        if self.config["scan_shortcuts"] and self.config["scan_desktop"]:
            tasks.append(self._scan_desktop_shortcuts())
        
        # 并行执行所有扫描任务
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
    
    async def _scan_registry_app_paths(self) -> List[AppInfo]:
        """扫描注册表App Paths"""
        apps = []
        logger.debug("扫描注册表 App Paths...")
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        app_name = winreg.EnumKey(key, i)
                        if not app_name.lower().endswith('.exe'):
                            continue
                            
                        app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{app_name}"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, app_key_path) as app_key:
                            try:
                                # 获取可执行文件路径
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                if not exe_path or not os.path.exists(exe_path):
                                    continue
                                
                                # 获取友好名称
                                try:
                                    friendly_name, _ = winreg.QueryValueEx(app_key, "FriendlyAppName")
                                    display_name = friendly_name if friendly_name else app_name[:-4]
                                except:
                                    display_name = app_name[:-4]
                                
                                # 获取文件信息
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
                        
        except Exception as e:
            logger.error(f"扫描App Paths注册表失败: {e}")
            self._scan_stats["error_count"] += 1
        
        self._scan_stats["registry_count"] += len(apps)
        logger.debug(f"从App Paths找到 {len(apps)} 个应用")
        return apps
    
    async def _scan_registry_uninstall(self) -> List[AppInfo]:
        """扫描注册表Uninstall"""
        apps = []
        logger.debug("扫描注册表 Uninstall...")
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                apps.extend(await self._process_uninstall_key(key, AppSource.REGISTRY_UNINSTALL))
        except Exception as e:
            logger.error(f"扫描Uninstall注册表失败: {e}")
            self._scan_stats["error_count"] += 1
        
        self._scan_stats["registry_count"] += len(apps)
        logger.debug(f"从Uninstall找到 {len(apps)} 个应用")
        return apps
    
    async def _scan_registry_user_uninstall(self) -> List[AppInfo]:
        """扫描用户注册表Uninstall"""
        apps = []
        logger.debug("扫描用户注册表 Uninstall...")
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                apps.extend(await self._process_uninstall_key(key, AppSource.REGISTRY_USER_UNINSTALL))
        except Exception as e:
            logger.error(f"扫描用户Uninstall注册表失败: {e}")
            self._scan_stats["error_count"] += 1
        
        self._scan_stats["registry_count"] += len(apps)
        logger.debug(f"从用户Uninstall找到 {len(apps)} 个应用")
        return apps
    
    async def _process_uninstall_key(self, key, source: AppSource) -> List[AppInfo]:
        """处理Uninstall注册表键"""
        apps = []
        
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey_path = f"{winreg.QueryInfoKey(key)[0]}\\{subkey_name}"
                
                with winreg.OpenKey(key, subkey_name) as subkey:
                    try:
                        # 获取基本信息
                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                        install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                        
                        if not display_name or not install_location:
                            continue
                        
                        # 获取额外信息
                        try:
                            publisher, _ = winreg.QueryValueEx(subkey, "Publisher")
                        except:
                            publisher = None
                        
                        try:
                            version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                        except:
                            version = None
                        
                        # 查找可执行文件
                        exe_files = self._find_executables(install_location)
                        for exe_path in exe_files:
                            file_info = self._get_file_info(exe_path)
                            
                            app = AppInfo(
                                name=display_name,
                                path=exe_path,
                                source=source,
                                display_name=display_name,
                                install_location=install_location,
                                publisher=publisher,
                                version=version,
                                last_modified=file_info["modified"],
                                file_hash=file_info["hash"]
                            )
                            apps.append(app)
                            
                    except Exception as e:
                        logger.debug(f"处理Uninstall子项失败 {subkey_name}: {e}")
                        
            except Exception as e:
                logger.debug(f"枚举Uninstall键失败 {i}: {e}")
        
        return apps
    
    async def _scan_start_menu_shortcuts(self) -> List[AppInfo]:
        """扫描开始菜单快捷方式"""
        apps = []
        paths = [
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        ]
        
        for path in paths:
            if os.path.exists(path):
                apps.extend(await self._scan_shortcuts_in_directory(path, AppSource.SHORTCUT_START_MENU))
        
        self._scan_stats["shortcut_count"] += len(apps)
        logger.debug(f"从开始菜单找到 {len(apps)} 个快捷方式")
        return apps
    
    async def _scan_desktop_shortcuts(self) -> List[AppInfo]:
        """扫描桌面快捷方式"""
        apps = []
        paths = [
            os.path.expanduser(r"~\Desktop"),
            r"C:\Users\Public\Desktop"
        ]
        
        for path in paths:
            if os.path.exists(path):
                apps.extend(await self._scan_shortcuts_in_directory(path, AppSource.SHORTCUT_DESKTOP))
        
        self._scan_stats["shortcut_count"] += len(apps)
        logger.debug(f"从桌面找到 {len(apps)} 个快捷方式")
        return apps
    
    async def _scan_shortcuts_in_directory(self, directory: str, source: AppSource) -> List[AppInfo]:
        """在指定目录扫描快捷方式"""
        apps = []
        
        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            lnk_files = await loop.run_in_executor(None, self._find_lnks_recursive, directory)
            
            for lnk_path in lnk_files:
                try:
                    app_info = await loop.run_in_executor(None, self._parse_shortcut, lnk_path)
                    if app_info:
                        app_info.source = source
                        apps.append(app_info)
                except Exception as e:
                    logger.debug(f"解析快捷方式失败 {lnk_path}: {e}")
                    
        except Exception as e:
            logger.error(f"扫描快捷方式目录失败 {directory}: {e}")
        
        return apps
    
    def _find_lnks_recursive(self, directory: str) -> List[str]:
        """递归查找所有.lnk文件"""
        lnk_files = []
        try:
            pattern = os.path.join(directory, "**", "*.lnk")
            lnk_files = glob.glob(pattern, recursive=True)
        except Exception as e:
            logger.debug(f"查找.lnk文件失败 {directory}: {e}")
        return lnk_files
    
    def _parse_shortcut(self, lnk_path: str) -> Optional[AppInfo]:
        """解析快捷方式文件"""
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target_path = shortcut.TargetPath
            
            if not target_path or not os.path.exists(target_path):
                return None
            
            # 只处理.exe文件
            if not target_path.lower().endswith('.exe'):
                return None
            
            # 获取应用名称
            app_name = os.path.splitext(os.path.basename(lnk_path))[0]
            
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
                source=AppSource.SHORTCUT_START_MENU,  # 默认值，会被覆盖
                display_name=app_name,
                shortcut_path=lnk_path,
                last_modified=file_info["modified"],
                file_hash=file_info["hash"]
            )
            
        except ImportError:
            logger.warning("win32com模块未安装，跳过快捷方式解析")
        except Exception as e:
            logger.debug(f"解析快捷方式失败 {lnk_path}: {e}")
        
        return None
    
    def _find_executables(self, directory: str) -> List[str]:
        """在目录中查找可执行文件"""
        if not os.path.exists(directory):
            return []
        
        exe_files = []
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.exe'):
                        exe_path = os.path.join(root, file)
                        if os.path.exists(exe_path):
                            exe_files.append(exe_path)
                            
                            # 限制数量
                            if len(exe_files) >= 10:  # 每个目录最多10个
                                break
                
                if len(exe_files) >= 10:
                    break
                    
        except Exception as e:
            logger.debug(f"查找可执行文件失败 {directory}: {e}")
        
        return exe_files
    
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
                # 优先级：快捷方式 > App Paths > Uninstall
                existing = unique_apps[key]
                if self._get_source_priority(app.source) > self._get_source_priority(existing.source):
                    unique_apps[key] = app
        
        # 转换为列表并排序
        result = list(unique_apps.values())
        result.sort(key=lambda x: x.display_name.lower())
        
        # 限制数量
        if len(result) > self.config["max_apps"]:
            result = result[:self.config["max_apps"]]
            logger.warning(f"应用数量超过限制，已截断至 {self.config['max_apps']} 个")
        
        return result
    
    def _get_source_priority(self, source: AppSource) -> int:
        """获取来源优先级"""
        priorities = {
            AppSource.SHORTCUT_START_MENU: 4,
            AppSource.SHORTCUT_DESKTOP: 4,
            AppSource.SHORTCUT_COMMON: 4,
            AppSource.REGISTRY_APP_PATHS: 3,
            AppSource.REGISTRY_UNINSTALL: 2,
            AppSource.REGISTRY_USER_UNINSTALL: 1
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
                "duration": self._scan_stats["scan_duration"]
            }
        }
    
    def get_scan_stats(self) -> Dict:
        """获取扫描统计信息"""
        return self._scan_stats.copy()

# 全局实例
_enhanced_scanner = None

def get_enhanced_scanner(config: Dict = None) -> EnhancedAppScanner:
    """获取全局扫描器实例"""
    global _enhanced_scanner
    if _enhanced_scanner is None:
        _enhanced_scanner = EnhancedAppScanner(config)
    return _enhanced_scanner

async def refresh_enhanced_apps():
    """刷新增强应用列表"""
    scanner = get_enhanced_scanner()
    await scanner.refresh_apps()