"""
agent_server.py 模块测试

测试Agent服务器的核心功能：
- FastAPI应用路由
- 健康检查端点
- 任务调度端点
- 模块初始化
"""

import asyncio
import json
import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from agentserver.agent_server import app, Modules, _now_iso, lifespan


class TestFastAPIApp:
    """测试FastAPI应用"""
    
    @pytest.fixture
    def client(self):
        """FastAPI测试客户端"""
        return TestClient(app)
    
    def test_health_check_success(self, client):
        """测试健康检查端点成功"""
        # Mock Modules
        Modules.analyzer = Mock()
        Modules.computer_control = Mock()
        
        response = client.get("/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert isinstance(data["modules"], dict)
        assert data["modules"]["analyzer"] is True
        assert data["modules"]["computer_control"] is True
    
    def test_health_check_partial_ready(self, client):
        """测试健康检查端点部分模块未就绪"""
        # Mock部分模块为None
        Modules.analyzer = None
        Modules.computer_control = Mock()
        
        response = client.get("/health")
        
        data = response.json()
        assert data["modules"]["analyzer"] is False
        assert data["modules"]["computer_control"] is True
    
    def test_schedule_endpoint_unavailable(self, client):
        """测试调度端点（模块未就绪）"""
        # Mock模块未就绪
        Modules.computer_control = None
        Modules.task_scheduler = None
        
        payload = {"query": "测试任务", "agent_calls": []}
        response = client.post("/schedule", json=payload)
        
        # 验证服务不可用
        assert response.status_code == 503
        data = response.json()
        assert "电脑控制智能体或任务调度器未就绪" in data["detail"]
    
    def test_schedule_endpoint_no_tasks(self, client):
        """测试调度端点（无任务）"""
        # Mock模块
        Modules.computer_control = Mock()
        Modules.task_scheduler = AsyncMock()
        Modules.task_scheduler.create_task = AsyncMock(return_value="task_123")
        
        payload = {
            "query": "测试查询",
            "agent_calls": [],
            "session_id": "session_123",
            "analysis_session_id": "analysis_123",
            "request_id": "request_123"
        }
        
        response = client.post("/schedule", json=payload)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "no_tasks"
        assert data["task_id"] == "request_123"
        assert data["message"] == "未发现可执行的Agent任务"
        assert data["session_id"] == "session_123"
        assert data["analysis_session_id"] == "analysis_123"
    
    def test_schedule_endpoint_with_tasks(self, client):
        """测试调度端点（有任务）"""
        # Mock模块
        mock_computer_control = Mock()
        mock_task_scheduler = AsyncMock()
        mock_task_scheduler.create_task = AsyncMock(return_value="task_123")
        Modules.computer_control = mock_computer_control
        Modules.task_scheduler = mock_task_scheduler
        
        # Mock异步任务创建
        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = Mock()
            
            payload = {
                "query": "执行电脑控制任务",
                "agent_calls": [
                    {
                        "tool_name": "computer_control",
                        "service_name": "computer_control",
                        "instruction": "打开记事本"
                    }
                ],
                "session_id": "session_456",
                "analysis_session_id": "analysis_456",
                "request_id": "request_456",
                "callback_url": "http://localhost:8000/callback"
            }
            
            response = client.post("/schedule", json=payload)
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "scheduled"
            assert data["task_id"] == "request_456"
            assert "已调度 1 个Agent任务" in data["message"]
            
            # 验证异步任务被创建
            mock_create_task.assert_called_once()
            
            # 验证任务调度器被调用
            mock_task_scheduler.create_task.assert_called_once_with(
                task_id="request_456",
                purpose="执行Agent任务: 执行电脑控制任务",
                session_id="session_456",
                analysis_session_id="analysis_456"
            )
    
    def test_schedule_endpoint_exception(self, client):
        """测试调度端点异常"""
        Modules.computer_control = Mock()
        Modules.task_scheduler = AsyncMock()
        Modules.task_scheduler.create_task = AsyncMock(side_effect=Exception("调度错误"))
        
        payload = {"query": "测试", "agent_calls": [{"tool_name": "test"}]}
        
        response = client.post("/schedule", json=payload)
        
        # 验证内部服务器错误
        assert response.status_code == 500
        data = response.json()
        assert "调度失败" in data["detail"]
    
    def test_analyze_and_execute_endpoint_unavailable(self, client):
        """测试分析执行端点（模块未就绪）"""
        Modules.analyzer = None
        Modules.computer_control = None
        
        payload = {"messages": []}
        response = client.post("/analyze_and_execute", json=payload)
        
        assert response.status_code == 503
        data = response.json()
        assert "分析器或电脑控制智能体未就绪" in data["detail"]
    
    def test_analyze_and_execute_endpoint_invalid_messages(self, client):
        """测试分析执行端点（无效消息格式）"""
        Modules.analyzer = Mock()
        Modules.computer_control = Mock()
        
        # 无效的消息格式（不是列表）
        payload = {"messages": "not a list"}
        response = client.post("/analyze_and_execute", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "messages必须是{role, content}格式的列表" in data["detail"]
    
    def test_analyze_and_execute_endpoint_no_tasks(self, client):
        """测试分析执行端点（无任务）"""
        Modules.analyzer = Mock()
        Modules.computer_control = Mock()
        
        # 没有包含任务的消息
        payload = {
            "messages": [
                {"role": "user", "content": "普通对话"}
            ]
        }
        
        response = client.post("/analyze_and_execute", json=payload)
        
        # 验证成功响应（无任务可执行）
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "未发现可执行的电脑控制任务"


class TestHelperFunctions:
    """测试辅助函数"""
    
    def test_now_iso(self):
        """测试_now_iso函数"""
        from datetime import datetime
        
        iso_str = _now_iso()
        
        # 验证格式
        try:
            datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            assert True
        except ValueError:
            assert False, f"无效的ISO格式: {iso_str}"


class TestLifespan:
    """测试应用生命周期管理"""
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """测试生命周期启动成功"""
        # Mock模块
        mock_app = Mock()
        
        with patch("agentserver.agent_server.get_background_analyzer") as mock_get_analyzer:
            with patch("agentserver.agent_server.ComputerControlAgent") as MockComputerControl:
                with patch("agentserver.agent_server.get_task_scheduler") as mock_get_scheduler:
                    with patch("agentserver.agent_server.config") as mock_config:
                        # 设置Mock
                        mock_analyzer = Mock()
                        mock_computer_control = Mock()
                        mock_scheduler = AsyncMock()
                        mock_scheduler.set_llm_config = Mock()
                        
                        mock_get_analyzer.return_value = mock_analyzer
                        MockComputerControl.return_value = mock_computer_control
                        mock_get_scheduler.return_value = mock_scheduler
                        
                        # Mock配置
                        mock_config.api.model = "test_model"
                        mock_config.api.api_key = "test_key"
                        mock_config.api.base_url = "https://test.url"
                        
                        # 执行启动
                        async with lifespan(mock_app):
                            # 验证模块初始化
                            assert Modules.analyzer == mock_analyzer
                            assert Modules.computer_control == mock_computer_control
                            assert Modules.task_scheduler == mock_scheduler
                            
                            # 验证LLM配置设置
                            mock_scheduler.set_llm_config.assert_called_once_with({
                                "model": "test_model",
                                "api_key": "test_key",
                                "api_base": "https://test.url"
                            })
        
        # 手动清除Modules（生命周期可能没有清理）
        Modules.analyzer = None
        Modules.computer_control = None
        Modules.task_scheduler = None
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """测试生命周期启动失败"""
        mock_app = Mock()
        
        with patch("agentserver.agent_server.get_background_analyzer", side_effect=Exception("初始化错误")):
            # 验证启动时抛出异常
            with pytest.raises(Exception) as exc_info:
                async with lifespan(mock_app):
                    pass
            
            assert "初始化错误" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """测试生命周期关闭"""
        mock_app = Mock()
        
        # 正常启动
        with patch("agentserver.agent_server.get_background_analyzer"):
            with patch("agentserver.agent_server.ComputerControlAgent"):
                with patch("agentserver.agent_server.get_task_scheduler"):
                    with patch("agentserver.agent_server.config"):
                        # 执行完整的生命周期
                        async with lifespan(mock_app):
                            pass  # 正常执行
        
        # 验证成功执行（没有异常）


class TestProcessComputerControlTask:
    """测试电脑控制任务处理"""
    
    @pytest.mark.asyncio
    async def test_process_computer_control_task_success(self):
        """测试处理电脑控制任务成功"""
        from agentserver.agent_server import _process_computer_control_task
        
        # Mock模块和智能体
        mock_computer_control = AsyncMock()
        mock_computer_control.handle_handoff = AsyncMock(
            return_value={"action": "completed", "result": "成功打开记事本"}
        )
        Modules.computer_control = mock_computer_control
        
        # Mock日志
        with patch("agentserver.agent_server.logger") as mock_logger:
            result = await _process_computer_control_task("打开记事本", "session_123")
            
            # 验证结果
            assert result["success"] is True
            assert result["task_type"] == "computer_control"
            assert result["instruction"] == "打开记事本"
            assert result["result"] == {"action": "completed", "result": "成功打开记事本"}
            
            # 验证日志记录
            mock_logger.info.assert_any_call("开始处理电脑控制任务: 打开记事本")
            mock_logger.info.assert_any_call("电脑控制任务完成: 打开记事本")
            
        # 清理
        Modules.computer_control = None
    
    @pytest.mark.asyncio
    async def test_process_computer_control_task_failure(self):
        """测试处理电脑控制任务失败"""
        from agentserver.agent_server import _process_computer_control_task
        
        mock_computer_control = AsyncMock()
        mock_computer_control.handle_handoff = AsyncMock(
            side_effect=Exception("控制失败")
        )
        Modules.computer_control = mock_computer_control
        
        with patch("agentserver.agent_server.logger") as mock_logger:
            result = await _process_computer_control_task("无效指令")
            
            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert result["task_type"] == "computer_control"
            assert result["instruction"] == "无效指令"
            
            # 验证错误日志
            mock_logger.error.assert_called()
            
        # 清理
        Modules.computer_control = None


class TestExecuteAgentTasksAsync:
    """测试异步执行Agent任务"""
    
    @pytest.mark.asyncio
    async def test_execute_agent_tasks_async_success(self):
        """测试异步执行Agent任务成功"""
        from agentserver.agent_server import _execute_agent_tasks_async
        
        # Mock模块
        mock_task_scheduler = AsyncMock()
        mock_task_scheduler.add_task_step = AsyncMock()
        Modules.task_scheduler = mock_task_scheduler
        
        # Mock任务处理
        with patch("agentserver.agent_server._process_computer_control_task") as mock_process_task:
            mock_process_task.return_value = {
                "success": True,
                "result": "任务完成",
                "task_type": "computer_control"
            }
            
            # Mock回调通知
            with patch("agentserver.agent_server._send_callback_notification") as mock_callback:
                mock_callback.return_value = None
                
                # Mock日志
                with patch("agentserver.agent_server.logger") as mock_logger:
                    agent_calls = [
                        {
                            "tool_name": "computer_control",
                            "service_name": "computer_control",
                            "instruction": "任务1"
                        }
                    ]
                    
                    await _execute_agent_tasks_async(
                        agent_calls=agent_calls,
                        session_id="session_123",
                        analysis_session_id="analysis_123",
                        request_id="request_123",
                        callback_url="http://localhost:8000/callback"
                    )
                    
                    # 验证任务调度器被调用
                    assert mock_task_scheduler.add_task_step.call_count >= 2
                    
                    # 验证任务处理被调用
                    mock_process_task.assert_called_once_with("任务1", "session_123")
                    
                    # 验证回调被调用
                    mock_callback.assert_called_once()
                    
                    # 验证日志记录
                    mock_logger.info.assert_any_call("[异步执行] 开始执行 1 个Agent任务")
                    
        # 清理
        Modules.task_scheduler = None
    
    @pytest.mark.asyncio
    async def test_execute_agent_tasks_async_failure(self):
        """测试异步执行Agent任务失败"""
        from agentserver.agent_server import _execute_agent_tasks_async
        
        Modules.task_scheduler = AsyncMock()
        Modules.task_scheduler.add_task_step = AsyncMock()
        
        with patch("agentserver.agent_server._process_computer_control_task") as mock_process_task:
            mock_process_task.side_effect = Exception("处理失败")
            
            with patch("agentserver.agent_server._send_callback_notification") as mock_callback:
                with patch("agentserver.agent_server.logger") as mock_logger:
                    agent_calls = [{"tool_name": "test", "instruction": "任务1"}]
                    
                    await _execute_agent_tasks_async(
                        agent_calls=agent_calls,
                        session_id="session_123",
                        analysis_session_id="analysis_123",
                        request_id="request_123",
                        callback_url="http://localhost:8000/callback"
                    )
                    
                    # 验证错误回调被调用
                    mock_callback.assert_called_once()
                    mock_logger.error.assert_called_with("[异步执行] 任务 1 执行失败: 处理失败")
                    
        # 清理
        Modules.task_scheduler = None


class TestSendCallbackNotification:
    """测试发送回调通知"""
    
    @pytest.mark.asyncio
    async def test_send_callback_notification_success(self):
        """测试发送回调通知成功"""
        from agentserver.agent_server import _send_callback_notification
        
        # Mock httpx（在函数内部导入，需要模拟全局模块）
        with patch("httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock(status_code=200)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
            
            # Mock日志
            with patch("agentserver.agent_server.logger") as mock_logger:
                results = [{"agent_call": {}, "result": {"success": True}, "step_index": 0}]
                
                await _send_callback_notification(
                    callback_url="http://localhost:8000/callback",
                    request_id="request_123",
                    session_id="session_123",
                    analysis_session_id="analysis_123",
                    results=results
                )
                
                # 验证HTTP请求
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "http://localhost:8000/callback"
                
                # 验证请求体
                payload = call_args[1]["json"]
                assert payload["request_id"] == "request_123"
                assert payload["session_id"] == "session_123"
                assert payload["analysis_session_id"] == "analysis_123"
                assert payload["success"] is True
                assert payload["results"] == results
                
                # 验证成功日志
                mock_logger.info.assert_called_with("[回调通知] Agent任务结果回调成功: request_123")
    
    @pytest.mark.asyncio
    async def test_send_callback_notification_error_response(self):
        """测试发送回调通知（服务器错误响应）"""
        from agentserver.agent_server import _send_callback_notification
        
        with patch("httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock(status_code=500)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
            
            with patch("agentserver.agent_server.logger") as mock_logger:
                await _send_callback_notification(
                    callback_url="http://localhost:8000/callback",
                    request_id="request_123",
                    session_id="session_123",
                    analysis_session_id="analysis_123",
                    results=[]
                )
                
                # 验证错误日志
                mock_logger.error.assert_called_with("[回调通知] Agent任务结果回调失败: 500")
    
    @pytest.mark.asyncio
    async def test_send_callback_notification_exception(self):
        """测试发送回调通知异常"""
        from agentserver.agent_server import _send_callback_notification
        
        with patch("httpx") as mock_httpx:
            mock_httpx.AsyncClient.side_effect = Exception("网络错误")
            
            with patch("agentserver.agent_server.logger") as mock_logger:
                await _send_callback_notification(
                    callback_url="http://localhost:8000/callback",
                    request_id="request_123",
                    session_id="session_123",
                    analysis_session_id="analysis_123",
                    results=[]
                )
                
                # 验证异常日志
                mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])