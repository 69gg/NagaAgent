# test_robust_app_launcher_agent.py - 稳健版应用启动Agent测试
import unittest
import asyncio
import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robust_app_launcher_agent import RobustAppLauncherAgent, create_robust_app_launcher_agent

class TestRobustAppLauncherAgent(unittest.TestCase):
    """测试稳健版应用启动Agent"""
    
    def setUp(self):
        """测试设置"""
        self.config = {
            "debug_mode": True,
            "cache_enabled": False,
            "log_level": "DEBUG"
        }
        self.agent = RobustAppLauncherAgent(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.name, "Robust AppLauncher Agent")
        self.assertEqual(self.agent.version, "3.0.0")
        self.assertFalse(self.agent.initialized)
        self.assertEqual(self.agent.stats["total_requests"], 0)
    
    def test_load_config(self):
        """测试加载配置"""
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as tmp:
            tmp.write("DEBUG_MODE=true\n")
            tmp.write("MAX_APPS=500\n")
            tmp.write("LOG_LEVEL=DEBUG\n")
            tmp_path = tmp.name
        
        try:
            # 修改配置文件路径
            original_path = os.path.join(os.path.dirname(__file__), "config.env")
            backup_path = original_path + ".bak"
            if os.path.exists(original_path):
                os.rename(original_path, backup_path)
            os.rename(tmp_path, original_path)
            
            # 创建新agent测试配置加载
            agent = RobustAppLauncherAgent()
            self.assertTrue(agent.config["debug_mode"])
            self.assertEqual(agent.config["max_apps"], 500)
            self.assertEqual(agent.config["log_level"], "DEBUG")
            
        finally:
            # 恢复原文件
            if os.path.exists(backup_path):
                os.rename(backup_path, original_path)
            elif os.path.exists(original_path):
                os.unlink(original_path)
    
    async def test_initialize(self):
        """测试异步初始化"""
        await self.agent.initialize()
        self.assertTrue(self.agent.initialized)
        self.assertIsNotNone(self.agent.stats["startup_time"])
    
    def test_validate_request_valid(self):
        """测试验证有效请求"""
        request = {
            "tool_name": "启动应用",
            "app": "Chrome"
        }
        
        result = self.agent._validate_request(request)
        self.assertTrue(result["valid"])
        self.assertEqual(result["message"], "验证通过")
    
    def test_validate_request_missing_tool_name(self):
        """测试验证缺少tool_name的请求"""
        request = {
            "app": "Chrome"
        }
        
        result = self.agent._validate_request(request)
        self.assertFalse(result["valid"])
        self.assertIn("缺少tool_name参数", result["message"])
    
    def test_validate_request_invalid_type(self):
        """测试验证无效类型的请求"""
        request = "invalid request"
        
        result = self.agent._validate_request(request)
        self.assertFalse(result["valid"])
        self.assertIn("必须是JSON对象", result["message"])
    
    def test_validate_request_invalid_tool_name_type(self):
        """测试验证无效tool_name类型"""
        request = {
            "tool_name": 123
        }
        
        result = self.agent._validate_request(request)
        self.assertFalse(result["valid"])
        self.assertIn("必须是字符串", result["message"])
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent.initialize')
    async def test_handle_handoff_initialize(self, mock_init):
        """测试handoff时初始化"""
        mock_init.return_value = AsyncMock()
        
        request = {
            "tool_name": "启动应用",
            "app": "Chrome"
        }
        
        response = json.loads(await self.agent.handle_handoff(request))
        
        self.assertTrue(response["success"])
        mock_init.assert_called_once()
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._process_request')
    async def test_handle_handoff_success(self, mock_process):
        """测试成功处理handoff"""
        mock_process.return_value = {"success": True, "message": "Success"}
        
        request = {
            "tool_name": "启动应用",
            "app": "Chrome"
        }
        
        response = json.loads(await self.agent.handle_handoff(request))
        
        self.assertTrue(response["success"])
        self.assertEqual(self.agent.stats["total_requests"], 1)
        self.assertEqual(self.agent.stats["successful_requests"], 1)
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._process_request')
    async def test_handle_handoff_failure(self, mock_process):
        """测试处理handoff失败"""
        mock_process.return_value = {"success": False, "message": "Failed"}
        
        request = {
            "tool_name": "启动应用",
            "app": "NonExistent"
        }
        
        response = json.loads(await self.agent.handle_handoff(request))
        
        self.assertFalse(response["success"])
        self.assertEqual(self.agent.stats["total_requests"], 1)
        self.assertEqual(self.agent.stats["failed_requests"], 1)
        self.assertEqual(self.agent.stats["last_error"], "Failed")
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._process_request')
    async def test_handle_handoff_exception(self, mock_process):
        """测试处理handoff异常"""
        mock_process.side_effect = Exception("Test exception")
        
        request = {
            "tool_name": "启动应用",
            "app": "Chrome"
        }
        
        response = json.loads(await self.agent.handle_handoff(request))
        
        self.assertFalse(response["success"])
        self.assertIn("内部错误", response["message"])
        self.assertEqual(response["error_code"], "INTERNAL_ERROR")
        self.assertEqual(self.agent.stats["total_requests"], 1)
        self.assertEqual(self.agent.stats["failed_requests"], 1)
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._handle_launch_app')
    async def test_process_request_launch_app(self, mock_handle):
        """测试处理启动应用请求"""
        mock_handle.return_value = {"success": True, "message": "App launched"}
        
        result = await self.agent._process_request("启动应用", {"app": "Chrome"}, "test_id")
        
        self.assertTrue(result["success"])
        mock_handle.assert_called_once_with({"app": "Chrome"}, "test_id")
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._handle_get_apps')
    async def test_process_request_get_apps(self, mock_handle):
        """测试处理获取应用列表请求"""
        mock_handle.return_value = {"success": True, "message": "Apps list"}
        
        result = await self.agent._process_request("获取应用列表", {}, "test_id")
        
        self.assertTrue(result["success"])
        mock_handle.assert_called_once_with({}, "test_id")
    
    async def test_process_request_unknown_tool(self):
        """测试处理未知工具"""
        result = await self.agent._process_request("未知工具", {}, "test_id")
        
        self.assertFalse(result["success"])
        self.assertIn("未知的操作", result["message"])
    
    @patch('robust_app_launcher_agent.RobustAppLauncherAgent._get_app_list_for_selection')
    async def test_handle_launch_app_no_app_name(self, mock_get_list):
        """测试启动应用但没有提供应用名"""
        mock_get_list.return_value = {"success": True, "message": "App list"}
        
        result = await self.agent._handle_launch_app({}, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "app_selection")
        mock_get_list.assert_called_once_with("test_id")
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.launch_app')
    async def test_handle_launch_app_success(self, mock_launch):
        """测试成功启动应用"""
        from enhanced_app_launcher import LaunchStatus, LaunchResult
        
        mock_launch.return_value = LaunchStatus(
            result=LaunchResult.SUCCESS,
            message="App started successfully",
            app_name="Chrome",
            process_id=1234,
            start_time=1234567890,
            launch_method="direct"
        )
        
        result = await self.agent._handle_launch_app({
            "app": "Chrome",
            "args": "--incognito"
        }, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "app_started")
        self.assertEqual(result["data"]["process_id"], 1234)
        mock_launch.assert_called_once_with("Chrome", "--incognito", {})
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.launch_app')
    async def test_handle_launch_app_failure(self, mock_launch):
        """测试启动应用失败"""
        from enhanced_app_launcher import LaunchStatus, LaunchResult
        
        mock_launch.return_value = LaunchStatus(
            result=LaunchResult.NOT_FOUND,
            message="App not found",
            app_name="NonExistent"
        )
        
        result = await self.agent._handle_launch_app({
            "app": "NonExistent"
        }, "test_id")
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_found")
        self.assertIn("未找到应用", result["message"])
    
    @patch('robust_app_launcher_agent.EnhancedAppScanner.get_app_info_for_llm')
    async def test_handle_get_apps(self, mock_get_info):
        """测试获取应用列表"""
        mock_get_info.return_value = {
            "total_count": 2,
            "apps": ["Chrome", "Notepad"],
            "scan_stats": {"scan_duration": 1.5}
        }
        
        result = await self.agent._handle_get_apps({
            "limit": 10
        }, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "apps_list")
        self.assertEqual(result["data"]["total_count"], 2)
        self.assertEqual(len(result["data"]["apps"]), 2)
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.terminate_app')
    async def test_handle_terminate_app(self, mock_terminate):
        """测试终止应用"""
        from enhanced_app_launcher import LaunchStatus, LaunchResult
        
        mock_terminate.return_value = LaunchStatus(
            result=LaunchResult.SUCCESS,
            message="App terminated",
            app_name="Chrome"
        )
        
        result = await self.agent._handle_terminate_app({
            "app": "Chrome"
        }, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "success")
        mock_terminate.assert_called_once_with("Chrome")
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.get_running_apps')
    async def test_handle_get_running_apps(self, mock_get_running):
        """测试获取运行中的应用"""
        mock_get_running.return_value = [
            {"name": "Chrome", "pid": 1234, "cpu_percent": 10.5}
        ]
        
        result = await self.agent._handle_get_running_apps({}, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "running_apps")
        self.assertEqual(len(result["data"]["running_apps"]), 1)
    
    @patch('robust_app_launcher_agent.EnhancedAppScanner.refresh_apps')
    async def test_handle_refresh_apps(self, mock_refresh):
        """测试刷新应用列表"""
        mock_refresh.return_value = AsyncMock()
        
        result = await self.agent._handle_refresh_apps({}, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "refreshed")
        mock_refresh.assert_called_once()
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.get_launch_history')
    async def test_handle_get_launch_history(self, mock_get_history):
        """测试获取启动历史"""
        mock_get_history.return_value = [
            {"app_name": "Chrome", "result": "success", "timestamp": 1234567890}
        ]
        
        result = await self.agent._handle_get_launch_history({
            "limit": 5
        }, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "launch_history")
        self.assertEqual(len(result["data"]["history"]), 1)
        mock_get_history.assert_called_once_with(5)
    
    @patch('robust_app_launcher_agent.EnhancedAppLauncher.get_stats')
    async def test_handle_get_stats(self, mock_get_stats):
        """测试获取统计信息"""
        mock_get_stats.return_value = {
            "total_launches": 10,
            "successful_launches": 8
        }
        
        result = await self.agent._handle_get_stats({}, "test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "stats")
        self.assertIn("agent_stats", result["data"])
        self.assertIn("launcher_stats", result["data"])
    
    @patch('robust_app_launcher_agent.EnhancedAppScanner.get_app_info_for_llm')
    async def test_get_app_list_for_selection(self, mock_get_info):
        """测试获取应用选择列表"""
        mock_get_info.return_value = {
            "total_count": 2,
            "apps": ["Chrome", "Notepad"]
        }
        
        result = await self.agent._get_app_list_for_selection("test_id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "app_selection")
        self.assertIn("usage_format", result["data"])
        self.assertIn("example", result["data"])
    
    def test_get_error_suggestion(self):
        """测试获取错误建议"""
        from enhanced_app_launcher import LaunchResult
        
        suggestion = self.agent._get_error_suggestion(LaunchResult.NOT_FOUND)
        self.assertIn("检查应用名称", suggestion)
        
        suggestion = self.agent._get_error_suggestion(LaunchResult.ACCESS_DENIED)
        self.assertIn("管理员权限", suggestion)
    
    def test_create_error_response(self):
        """测试创建错误响应"""
        response = json.loads(self.agent._create_error_response(
            "Test error message",
            "test_id",
            "TEST_ERROR"
        ))
        
        self.assertFalse(response["success"])
        self.assertEqual(response["message"], "Test error message")
        self.assertEqual(response["error_code"], "TEST_ERROR")
    
    def test_create_error_response_with_details(self):
        """测试创建带详细信息的错误响应"""
        self.agent.config["debug_mode"] = True
        
        response = json.loads(self.agent._create_error_response(
            "Test error",
            "test_id",
            "TEST_ERROR",
            "Detailed error info"
        ))
        
        self.assertEqual(response["data"]["error_details"], "Detailed error info")
    
    @patch('builtins.open')
    @patch('json.dump')
    @patch('os.path.join')
    async def test_shutdown_with_debug(self, mock_join, mock_json, mock_open):
        """测试关闭Agent（调试模式）"""
        self.agent.config["debug_mode"] = True
        mock_join.return_value = "test_stats.json"
        
        await self.agent.shutdown()
        
        mock_open.assert_called_once()
        mock_json.assert_called_once()
    
    @patch('builtins.open')
    @patch('json.dump')
    async def test_shutdown_without_debug(self, mock_json, mock_open):
        """测试关闭Agent（非调试模式）"""
        self.agent.config["debug_mode"] = False
        
        await self.agent.shutdown()
        
        mock_open.assert_not_called()
        mock_json.assert_not_called()
    
    def test_create_robust_app_launcher_agent(self):
        """测试创建Agent实例"""
        agent1 = create_robust_app_launcher_agent()
        agent2 = create_robust_app_launcher_agent({"max_retries": 5})
        
        self.assertIsNotNone(agent1)
        self.assertEqual(agent2.config["max_retries"], 5)

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('robust_app_launcher_agent.EnhancedAppScanner')
    @patch('robust_app_launcher_agent.EnhancedAppLauncher')
    async def test_full_launch_flow(self, mock_launcher_class, mock_scanner_class):
        """测试完整的启动流程"""
        # 设置mock
        mock_scanner = Mock()
        mock_scanner.get_app_info_for_llm.return_value = {
            "total_count": 1,
            "apps": ["TestApp"]
        }
        mock_scanner_class.return_value = mock_scanner
        
        mock_launcher = Mock()
        from enhanced_app_launcher import LaunchStatus, LaunchResult
        mock_launcher.launch_app.return_value = LaunchStatus(
            result=LaunchResult.SUCCESS,
            message="App launched",
            app_name="TestApp"
        )
        mock_launcher.get_stats.return_value = {"total_launches": 1}
        mock_launcher_class.return_value = mock_launcher
        
        # 创建agent并测试
        agent = RobustAppLauncherAgent()
        await agent.initialize()
        
        # 获取应用列表
        response1 = json.loads(await agent.handle_handoff({
            "tool_name": "获取应用列表"
        }))
        self.assertTrue(response1["success"])
        
        # 启动应用
        response2 = json.loads(await agent.handle_handoff({
            "tool_name": "启动应用",
            "app": "TestApp"
        }))
        self.assertTrue(response2["success"])
        
        # 获取统计
        response3 = json.loads(await agent.handle_handoff({
            "tool_name": "获取统计信息"
        }))
        self.assertTrue(response3["success"])

if __name__ == '__main__':
    # 运行异步测试
    import asyncio
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        for test, error in result.failures + result.errors:
            print(f"\n{test}:")
            print(error)