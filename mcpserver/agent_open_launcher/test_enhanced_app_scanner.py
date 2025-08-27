# test_enhanced_app_scanner.py - 增强版应用扫描器测试
import unittest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_app_scanner import EnhancedAppScanner, AppInfo, AppSource, get_enhanced_scanner

class TestEnhancedAppScanner(unittest.TestCase):
    """测试增强版应用扫描器"""
    
    def setUp(self):
        """测试设置"""
        self.config = {
            "cache_enabled": False,  # 测试时禁用缓存
            "max_apps": 100,
            "debug_mode": True
        }
        self.scanner = EnhancedAppScanner(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.scanner)
        self.assertEqual(self.scanner.config["max_apps"], 100)
        self.assertFalse(self.scanner._scan_completed)
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        scanner = EnhancedAppScanner()
        self.assertTrue(scanner.config["cache_enabled"])
        self.assertEqual(scanner.config["cache_ttl"], 3600)
        self.assertEqual(scanner.config["max_apps"], 1000)
    
    def test_get_file_info(self):
        """测试获取文件信息"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            info = self.scanner._get_file_info(tmp_path)
            self.assertIn("modified", info)
            self.assertIn("size", info)
            self.assertGreater(info["size"], 0)
        finally:
            os.unlink(tmp_path)
    
    def test_get_file_info_nonexistent(self):
        """测试获取不存在文件的信息"""
        info = self.scanner._get_file_info("nonexistent_file.exe")
        self.assertEqual(info["modified"], 0)
        self.assertEqual(info["size"], 0)
    
    def test_get_source_priority(self):
        """测试获取来源优先级"""
        self.assertGreater(
            self.scanner._get_source_priority(AppSource.SHORTCUT_START_MENU),
            self.scanner._get_source_priority(AppSource.REGISTRY_UNINSTALL)
        )
    
    def test_process_and_deduplicate(self):
        """测试处理和去重"""
        apps = [
            AppInfo("App1", "path1", AppSource.REGISTRY_APP_PATHS),
            AppInfo("App1", "path1", AppSource.REGISTRY_UNINSTALL),  # 重复名称，不同路径
            AppInfo("App2", "path2", AppSource.SHORTCUT_START_MENU),
            AppInfo("app1", "path3", AppSource.REGISTRY_APP_PATHS),  # 小写重复
        ]
        
        # 模拟文件存在
        with patch('os.path.exists', return_value=True):
            unique_apps = self.scanner._process_and_deduplicate(apps)
        
        self.assertEqual(len(unique_apps), 3)
        # 验证优先级
        app1 = next(app for app in unique_apps if app.name == "App1")
        self.assertEqual(app1.path, "path1")
    
    def test_build_name_map(self):
        """测试构建名称映射"""
        apps = [
            AppInfo("Chrome", "chrome.exe", AppSource.REGISTRY_APP_PATHS, "Google Chrome"),
            AppInfo("Notepad", "notepad.exe", AppSource.REGISTRY_APP_PATHS)
        ]
        
        self.scanner.apps_cache = apps
        self.scanner._build_name_map()
        
        self.assertIn("chrome", self.scanner.app_name_map)
        self.assertIn("google chrome", self.scanner.app_name_map)
        self.assertIn("notepad", self.scanner.app_name_map)
    
    @patch('winreg.OpenKey')
    @patch('winreg.QueryInfoKey')
    @patch('winreg.EnumKey')
    def test_scan_registry_app_paths_empty(self, mock_enum, mock_query, mock_open):
        """测试扫描空的App Paths注册表"""
        mock_query.return_value = (0,)  # 没有子键
        
        apps = asyncio.run(self.scanner._scan_registry_app_paths())
        self.assertEqual(len(apps), 0)
    
    @patch('os.walk')
    def test_find_executables(self, mock_walk):
        """测试查找可执行文件"""
        # 模拟目录结构
        mock_walk.return_value = [
            ("root", ["subdir"], ["app1.exe", "app2.exe", "readme.txt"]),
            ("root/subdir", [], ["app3.exe"])
        ]
        
        with patch('os.path.exists', return_value=True):
            exes = self.scanner._find_executables("test_dir")
        
        self.assertEqual(len(exes), 3)
        self.assertTrue(all(exe.endswith('.exe') for exe in exes))
    
    def test_find_executables_nonexistent_dir(self):
        """测试查找不存在的目录"""
        with patch('os.path.exists', return_value=False):
            exes = self.scanner._find_executables("nonexistent")
        self.assertEqual(len(exes), 0)
    
    @patch('glob.glob')
    def test_find_lnks_recursive(self, mock_glob):
        """测试递归查找lnk文件"""
        mock_glob.return_value = ["app1.lnk", "app2.lnk"]
        
        lnks = self.scanner._find_lnks_recursive("test_dir")
        self.assertEqual(len(lnks), 2)
        self.assertTrue(all(lnk.endswith('.lnk') for lnk in lnks))
    
    @patch('win32com.client.Dispatch')
    def test_parse_shortcut_success(self, mock_dispatch):
        """测试成功解析快捷方式"""
        mock_shell = Mock()
        mock_shortcut = Mock()
        mock_shortcut.TargetPath = "C:\\app.exe"
        mock_shortcut.Description = "Test App"
        mock_shell.CreateShortCut.return_value = mock_shortcut
        mock_dispatch.return_value = mock_shell
        
        with patch('os.path.exists', return_value=True):
            app = self.scanner._parse_shortcut("test.lnk")
        
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "Test App")
        self.assertEqual(app.path, "C:\\app.exe")
    
    @patch('win32com.client.Dispatch')
    def test_parse_shortcut_no_target(self, mock_dispatch):
        """测试解析没有目标的快捷方式"""
        mock_shell = Mock()
        mock_shortcut = Mock()
        mock_shortcut.TargetPath = ""
        mock_shell.CreateShortCut.return_value = mock_shortcut
        mock_dispatch.return_value = mock_shell
        
        app = self.scanner._parse_shortcut("test.lnk")
        self.assertIsNone(app)
    
    def test_parse_shortcut_import_error(self):
        """测试win32com导入错误"""
        with patch('builtins.__import__', side_effect=ImportError):
            app = self.scanner._parse_shortcut("test.lnk")
            self.assertIsNone(app)
    
    @patch('enhanced_app_scanner.EnhancedAppScanner._scan_all_sources')
    async def test_ensure_scan_completed(self, mock_scan):
        """测试确保扫描完成"""
        self.scanner._scan_completed = False
        await self.scanner.ensure_scan_completed()
        mock_scan.assert_called_once()
        self.assertTrue(self.scanner._scan_completed)
    
    @patch('enhanced_app_scanner.EnhancedAppScanner._scan_all_sources')
    async def test_ensure_scan_completed_already_done(self, mock_scan):
        """测试扫描已完成的情况"""
        self.scanner._scan_completed = True
        await self.scanner.ensure_scan_completed()
        mock_scan.assert_not_called()
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    async def test_load_cache_success(self, mock_json, mock_open, mock_exists):
        """测试成功加载缓存"""
        mock_exists.return_value = True
        mock_data = {
            "timestamp": time.time() - 1000,  # 未过期
            "apps": [
                {
                    "name": "TestApp",
                    "path": "test.exe",
                    "source": "registry_app_paths",
                    "display_name": "Test App"
                }
            ],
            "stats": {"total_scanned": 1}
        }
        mock_json.return_value = mock_data
        
        self.scanner.config["cache_ttl"] = 3600
        result = await self.scanner._load_cache()
        
        self.assertTrue(result)
        self.assertEqual(len(self.scanner.apps_cache), 1)
        self.assertEqual(self.scanner.apps_cache[0].name, "TestApp")
    
    @patch('os.path.exists')
    async def test_load_cache_no_file(self, mock_exists):
        """测试加载不存在的缓存文件"""
        mock_exists.return_value = False
        result = await self.scanner._load_cache()
        self.assertFalse(result)
    
    def test_get_enhanced_scanner_singleton(self):
        """测试全局扫描器单例"""
        scanner1 = get_enhanced_scanner()
        scanner2 = get_enhanced_scanner()
        self.assertIs(scanner1, scanner2)

class TestAppInfo(unittest.TestCase):
    """测试AppInfo数据类"""
    
    def test_app_info_creation(self):
        """测试创建AppInfo"""
        app = AppInfo(
            name="TestApp",
            path="test.exe",
            source=AppSource.REGISTRY_APP_PATHS
        )
        
        self.assertEqual(app.name, "TestApp")
        self.assertEqual(app.path, "test.exe")
        self.assertEqual(app.source, AppSource.REGISTRY_APP_PATHS)
        self.assertEqual(app.display_name, "TestApp")  # 默认值
        self.assertEqual(app.description, "应用: TestApp")  # 默认值
    
    def test_app_info_with_display_name(self):
        """测试带显示名称的AppInfo"""
        app = AppInfo(
            name="test",
            path="test.exe",
            source=AppSource.REGISTRY_APP_PATHS,
            display_name="Test Application"
        )
        
        self.assertEqual(app.name, "test")
        self.assertEqual(app.display_name, "Test Application")

if __name__ == '__main__':
    # 导入time
    import time
    unittest.main()