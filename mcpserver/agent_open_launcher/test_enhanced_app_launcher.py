# test_enhanced_app_launcher.py - 增强版应用启动器测试
import unittest
import asyncio
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_app_launcher import (
    EnhancedAppLauncher, LaunchResult, LaunchStatus, create_enhanced_launcher,
    AppInfo, AppSource
)

class TestEnhancedAppLauncher(unittest.TestCase):
    """测试增强版应用启动器"""
    
    def setUp(self):
        """测试设置"""
        self.config = {
            "launch_timeout": 5,
            "max_retries": 2,
            "debug_mode": True,
            "monitor_processes": False  # 测试时禁用进程监控
        }
        self.launcher = EnhancedAppLauncher(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.launcher)
        self.assertEqual(self.launcher.config["launch_timeout"], 5)
        self.assertEqual(self.launcher.config["max_retries"], 2)
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        launcher = EnhancedAppLauncher()
        self.assertTrue(launcher.config["wait_for_startup"])
        self.assertEqual(launcher.config["launch_timeout"], 30)
        self.assertEqual(launcher.config["max_retries"], 3)
    
    def test_validate_executable_valid(self):
        """测试验证有效的可执行文件"""
        # 创建临时exe文件
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as tmp:
            tmp.write(b"fake exe content")
            tmp_path = tmp.name
        
        try:
            # 模拟文件权限
            with patch('os.access', return_value=True):
                result = self.launcher._validate_executable(tmp_path)
            
            self.assertTrue(result["valid"])
            self.assertEqual(result["reason"], "验证通过")
        finally:
            os.unlink(tmp_path)
    
    def test_validate_executable_nonexistent(self):
        """测试验证不存在的可执行文件"""
        result = self.launcher._validate_executable("nonexistent.exe")
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "文件不存在")
    
    def test_validate_executable_wrong_extension(self):
        """测试验证错误扩展名的文件"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"not an exe")
            tmp_path = tmp.name
        
        try:
            result = self.launcher._validate_executable(tmp_path)
            self.assertFalse(result["valid"])
            self.assertEqual(result["reason"], "不是可执行文件")
        finally:
            os.unlink(tmp_path)
    
    def test_validate_executable_empty(self):
        """测试验证空的文件"""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as tmp:
            # 不写入内容，保持为空
            tmp_path = tmp.name
        
        try:
            result = self.launcher._validate_executable(tmp_path)
            self.assertFalse(result["valid"])
            self.assertEqual(result["reason"], "文件为空")
        finally:
            os.unlink(tmp_path)
    
    def test_prepare_launch_args(self):
        """测试准备启动参数"""
        app_info = AppInfo(
            name="TestApp",
            path="C:\\test.exe",
            source=AppSource.REGISTRY_APP_PATHS,
            install_location="C:\\Program Files\\TestApp"
        )
        
        args = ["--arg1", "value1"]
        options = {"working_dir": "C:\\custom"}
        
        launch_args = self.launcher._prepare_launch_args(app_info, args, options)
        
        self.assertEqual(launch_args["exe_path"], "C:\\test.exe")
        self.assertEqual(launch_args["args"], args)
        self.assertEqual(launch_args["working_dir"], "C:\\custom")
    
    def test_prepare_launch_args_no_options(self):
        """测试不提供选项时的启动参数"""
        app_info = AppInfo(
            name="TestApp",
            path="C:\\test.exe",
            source=AppSource.REGISTRY_APP_PATHS,
            install_location="C:\\Program Files\\TestApp"
        )
        
        launch_args = self.launcher._prepare_launch_args(app_info, None, {})
        
        self.assertEqual(launch_args["working_dir"], "C:\\Program Files\\TestApp")
    
    def test_prepare_launch_args_string_args(self):
        """测试字符串参数"""
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        
        launch_args = self.launcher._prepare_launch_args(app_info, "--arg1 value1", {})
        
        self.assertEqual(launch_args["args"], ["--arg1", "value1"])
    
    def test_record_launch(self):
        """测试记录启动历史"""
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        status = LaunchStatus(
            result=LaunchResult.SUCCESS,
            message="Success",
            app_name="TestApp",
            process_id=1234,
            launch_method="direct"
        )
        
        start_time = 1234567890
        self.launcher._record_launch(app_info, status, start_time)
        
        self.assertEqual(len(self.launcher.launch_history), 1)
        record = self.launcher.launch_history[0]
        self.assertEqual(record["app_name"], "TestApp")
        self.assertEqual(record["result"], "success")
        self.assertEqual(record["process_id"], 1234)
    
    def test_record_launch_disabled(self):
        """测试禁用启动记录"""
        self.launcher.config["log_launch_details"] = False
        
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        status = LaunchStatus(LaunchResult.SUCCESS, "Success")
        
        self.launcher._record_launch(app_info, status, 0)
        self.assertEqual(len(self.launcher.launch_history), 0)
    
    def test_get_launch_history(self):
        """测试获取启动历史"""
        # 添加一些历史记录
        self.launcher.launch_history = [
            {"timestamp": 1, "app_name": "App1"},
            {"timestamp": 2, "app_name": "App2"},
            {"timestamp": 3, "app_name": "App3"}
        ]
        
        history = self.launcher.get_launch_history(limit=2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["app_name"], "App2")  # 应该返回最新的两条
        self.assertEqual(history[1]["app_name"], "App3")
    
    def test_get_stats(self):
        """测试获取统计信息"""
        # 添加一些历史记录
        self.launcher.launch_history = [
            {"result": "success"},
            {"result": "success"},
            {"result": "failed"}
        ]
        
        stats = self.launcher.get_stats()
        
        self.assertEqual(stats["total_launches"], 3)
        self.assertEqual(stats["successful_launches"], 2)
        self.assertAlmostEqual(stats["success_rate"], 2/3)
    
    @patch('psutil.process_iter')
    async def test_check_if_running_found(self, mock_process_iter):
        """测试检查运行中的进程（找到）"""
        mock_proc = Mock()
        mock_proc.info = {'pid': 1234, 'exe': 'C:\\test.exe', 'name': 'test.exe'}
        mock_process_iter.return_value = [mock_proc]
        
        app_info = AppInfo("TestApp", "C:\\test.exe", AppSource.REGISTRY_APP_PATHS)
        
        pid = await self.launcher._check_if_running(app_info)
        self.assertEqual(pid, 1234)
    
    @patch('psutil.process_iter')
    async def test_check_if_running_not_found(self, mock_process_iter):
        """测试检查运行中的进程（未找到）"""
        mock_proc = Mock()
        mock_proc.info = {'pid': 1234, 'exe': 'C:\\other.exe', 'name': 'other.exe'}
        mock_process_iter.return_value = [mock_proc]
        
        app_info = AppInfo("TestApp", "C:\\test.exe", AppSource.REGISTRY_APP_PATHS)
        
        pid = await self.launcher._check_if_running(app_info)
        self.assertIsNone(pid)
    
    @patch('subprocess.Popen')
    async def test_launch_via_executable_success(self, mock_popen):
        """测试通过可执行文件启动成功"""
        mock_proc = Mock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc
        
        app_info = AppInfo("TestApp", "C:\\test.exe", AppSource.REGISTRY_APP_PATHS)
        launch_args = {
            "exe_path": "C:\\test.exe",
            "args": [],
            "working_dir": "C:\\",
            "show_cmd": 1,
            "elevated": False
        }
        
        status = await self.launcher._launch_via_executable(app_info, launch_args)
        
        self.assertEqual(status.result, LaunchResult.SUCCESS)
        self.assertEqual(status.process_id, 1234)
        self.assertEqual(status.launch_method, "direct")
    
    @patch('subprocess.Popen')
    async def test_launch_via_executable_permission_error(self, mock_popen):
        """测试权限错误"""
        mock_popen.side_effect = PermissionError("Access denied")
        
        app_info = AppInfo("TestApp", "C:\\test.exe", AppSource.REGISTRY_APP_PATHS)
        launch_args = {
            "exe_path": "C:\\test.exe",
            "args": [],
            "working_dir": "C:\\",
            "show_cmd": 1,
            "elevated": False
        }
        
        status = await self.launcher._launch_via_executable(app_info, launch_args)
        
        self.assertEqual(status.result, LaunchResult.ACCESS_DENIED)
        self.assertIn("权限不足", status.message)
    
    @patch('subprocess.Popen')
    async def test_launch_via_shortcut_success(self, mock_popen):
        """测试通过快捷方式启动成功"""
        mock_proc = Mock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc
        
        app_info = AppInfo(
            "TestApp",
            "C:\\test.exe",
            AppSource.SHORTCUT_START_MENU,
            shortcut_path="C:\\test.lnk"
        )
        launch_args = {
            "exe_path": "C:\\test.exe",
            "args": [],
            "working_dir": "C:\\",
            "shortcut_path": "C:\\test.lnk"
        }
        
        status = await self.launcher._launch_via_shortcut(app_info, launch_args)
        
        self.assertEqual(status.result, LaunchResult.SUCCESS)
        self.assertEqual(status.process_id, 1234)
        self.assertEqual(status.launch_method, "shortcut")
    
    @patch('enhanced_app_launcher.EnhancedAppLauncher._find_app_info')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._validate_executable')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._check_if_running')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._launch_via_executable')
    async def test_launch_app_success(self, mock_launch, mock_check, mock_validate, mock_find):
        """测试启动应用成功"""
        # 设置mock
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        mock_find.return_value = app_info
        mock_validate.return_value = {"valid": True}
        mock_check.return_value = None
        mock_launch.return_value = LaunchStatus(
            LaunchResult.SUCCESS,
            "Success",
            "TestApp",
            1234,
            launch_method="direct"
        )
        
        status = await self.launcher.launch_app("TestApp")
        
        self.assertEqual(status.result, LaunchResult.SUCCESS)
        mock_find.assert_called_once_with("TestApp")
        mock_validate.assert_called_once_with("test.exe")
        mock_launch.assert_called_once()
    
    @patch('enhanced_app_launcher.EnhancedAppLauncher._find_app_info')
    async def test_launch_app_not_found(self, mock_find):
        """测试启动不存在的应用"""
        mock_find.return_value = None
        
        status = await self.launcher.launch_app("NonExistentApp")
        
        self.assertEqual(status.result, LaunchResult.NOT_FOUND)
        self.assertIn("未找到应用", status.message)
    
    @patch('enhanced_app_launcher.EnhancedAppLauncher._find_app_info')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._validate_executable')
    async def test_launch_app_invalid_exe(self, mock_validate, mock_find):
        """测试启动无效的可执行文件"""
        app_info = AppInfo("TestApp", "invalid.exe", AppSource.REGISTRY_APP_PATHS)
        mock_find.return_value = app_info
        mock_validate.return_value = {
            "valid": False,
            "reason": "文件不存在",
            "details": "路径: invalid.exe"
        }
        
        status = await self.launcher.launch_app("TestApp")
        
        self.assertEqual(status.result, LaunchResult.INVALID_PATH)
        self.assertIn("可执行文件无效", status.message)
    
    @patch('enhanced_app_launcher.EnhancedAppLauncher._find_app_info')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._validate_executable')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._check_if_running')
    async def test_launch_app_already_running(self, mock_check, mock_validate, mock_find):
        """测试启动已在运行的应用"""
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        mock_find.return_value = app_info
        mock_validate.return_value = {"valid": True}
        mock_check.return_value = 1234
        
        status = await self.launcher.launch_app("TestApp")
        
        self.assertEqual(status.result, LaunchResult.ALREADY_RUNNING)
        self.assertIn("已在运行", status.message)
    
    @patch('enhanced_app_launcher.EnhancedAppLauncher._find_app_info')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._validate_executable')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._check_if_running')
    @patch('enhanced_app_launcher.EnhancedAppLauncher._launch_via_executable')
    async def test_launch_app_with_retry(self, mock_launch, mock_check, mock_validate, mock_find):
        """测试启动应用重试机制"""
        app_info = AppInfo("TestApp", "test.exe", AppSource.REGISTRY_APP_PATHS)
        mock_find.return_value = app_info
        mock_validate.return_value = {"valid": True}
        mock_check.return_value = None
        mock_launch.side_effect = [Exception("Failed"), LaunchStatus(LaunchResult.SUCCESS, "Success")]
        
        status = await self.launcher.launch_app("TestApp")
        
        self.assertEqual(status.result, LaunchResult.SUCCESS)
        self.assertEqual(mock_launch.call_count, 2)  # 应该重试一次
    
    @patch('psutil.process_iter')
    async def test_get_running_apps(self, mock_process_iter):
        """测试获取运行中的应用"""
        mock_proc1 = Mock()
        mock_proc1.info = {'pid': 1234, 'exe': 'C:\\app1.exe', 'name': 'app1.exe'}
        mock_proc1.cpu_percent.return_value = 10.5
        mock_proc1.memory_percent.return_value = 5.2
        
        mock_proc2 = Mock()
        mock_proc2.info = {'pid': 5678, 'exe': 'C:\\app2.exe', 'name': 'app2.exe'}
        mock_proc2.cpu_percent.return_value = 20.1
        mock_proc2.memory_percent.return_value = 8.7
        
        mock_process_iter.return_value = [mock_proc1, mock_proc2]
        
        # 添加到running_processes
        self.launcher.running_processes = {
            1234: {"name": "App1", "path": "C:\\app1.exe", "start_time": 1234567890},
            5678: {"name": "App2", "path": "C:\\app2.exe", "start_time": 1234567891}
        }
        
        running_apps = await self.launcher.get_running_apps()
        
        self.assertEqual(len(running_apps), 2)
        self.assertEqual(running_apps[0]["pid"], 1234)
        self.assertEqual(running_apps[0]["cpu_percent"], 10.5)
        self.assertEqual(running_apps[1]["pid"], 5678)
        self.assertEqual(running_apps[1]["cpu_percent"], 20.1)
    
    def test_create_enhanced_launcher(self):
        """测试创建增强版启动器"""
        launcher1 = create_enhanced_launcher()
        launcher2 = create_enhanced_launcher({"max_retries": 5})
        
        self.assertIsNotNone(launcher1)
        self.assertEqual(launcher2.config["max_retries"], 5)

if __name__ == '__main__':
    unittest.main()