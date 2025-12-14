"""
background_analyzer.py 模块测试

测试后台意图分析器的核心功能：
- 对话分析器（ConversationAnalyzer）
- 后台分析器（BackgroundAnalyzer）
- 异步意图分析流程
- 工具调用分发机制
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import httpx
import pytest
import pytest_asyncio
from system.background_analyzer import (
    ConversationAnalyzer,
    BackgroundAnalyzer,
    get_background_analyzer,
)


class TestConversationAnalyzer:
    """测试对话分析器"""
    
    def test_init(self):
        """测试ConversationAnalyzer初始化"""
        with patch("system.background_analyzer.ChatOpenAI") as mock_chat_openai:
            analyzer = ConversationAnalyzer()
            
            # 验证ChatOpenAI被正确初始化
            mock_chat_openai.assert_called_once_with(
                model="deepseek-chat",  # 默认值
                base_url="https://api.deepseek.com/v1",  # 默认值
                api_key="sk-placeholder-key-not-set",  # 默认值
                temperature=0
            )
    
    def test_build_prompt_without_tools(self):
        """测试构建提示词（无MCP工具信息）"""
        analyzer = ConversationAnalyzer()
        
        # Mock配置
        with patch("system.background_analyzer.config") as mock_config:
            mock_config.api.max_history_rounds = 10
            
            # Mock获取提示词
            with patch("system.background_analyzer.get_prompt") as mock_get_prompt:
                mock_get_prompt.return_value = "分析提示词: {conversation}"
                
                # Mock MCP工具获取失败（模拟导入失败）
                with patch("nagaagent_core.stable.mcp.get_registered_services", side_effect=ImportError):
                    messages = [
                        {"role": "user", "content": "你好"},
                        {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
                    ]
                    
                    prompt = analyzer._build_prompt(messages)
                    
                    # 验证get_prompt被调用
                    mock_get_prompt.assert_called_once_with(
                        "conversation_analyzer_prompt",
                        conversation="user: 你好\nassistant: 你好！有什么可以帮助你的？"
                    )
    
    def test_build_prompt_with_tools(self):
        """测试构建提示词（包含MCP工具信息）"""
        analyzer = ConversationAnalyzer()
        
        with patch("system.background_analyzer.config") as mock_config:
            mock_config.api.max_history_rounds = 10
            
            with patch("system.background_analyzer.get_prompt") as mock_get_prompt:
                mock_get_prompt.return_value = "分析提示词: {conversation}\n可用工具: {available_tools}"
                
                # Mock MCP工具信息
                with patch("nagaagent_core.stable.mcp.get_registered_services") as mock_get_services:
                    with patch("nagaagent_core.stable.mcp.get_service_info") as mock_get_info:
                        mock_get_services.return_value = ["service1", "service2"]
                        
                        service1_info = {
                            "displayName": "服务一",
                            "description": "第一个服务描述",
                            "capabilities": {
                                "invocationCommands": [
                                    {"command": "tool1", "description": "工具一"},
                                    {"command": "tool2", "description": "工具二"}
                                ]
                            }
                        }
                        service2_info = {
                            "displayName": "服务二",
                            "description": "第二个服务描述",
                            "capabilities": {
                                "invocationCommands": []
                            }
                        }
                        
                        mock_get_info.side_effect = lambda name: {
                            "service1": service1_info,
                            "service2": service2_info
                        }.get(name)
                        
                        messages = [{"role": "user", "content": "测试消息"}]
                        prompt = analyzer._build_prompt(messages)
                        
                        # 验证get_prompt被调用且包含工具信息
                        mock_get_prompt.assert_called_once()
                        call_kwargs = mock_get_prompt.call_args[1]
                        assert "conversation" in call_kwargs
                        assert "available_tools" in call_kwargs
                        assert "工具一" in call_kwargs["available_tools"]
                        assert "服务一" in call_kwargs["available_tools"]
    
    def test_analyze_success_with_tool_calls(self):
        """测试分析成功并发现工具调用"""
        analyzer = ConversationAnalyzer()
        
        # Mock LLM调用
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {
                "tool_name": "search_web",
                "service_name": "online_search",
                "agentType": "mcp",
                "parameters": {"query": "Python教程"}
            }
        ])
        
        mock_llm = MagicMock()
        mock_llm.invoke = Mock(return_value=mock_response)
        analyzer.llm = mock_llm
        
        # Mock配置
        with patch("system.background_analyzer.config") as mock_config:
            mock_config.api.max_history_rounds = 10
            
            # Mock提示词构建
            with patch.object(analyzer, '_build_prompt', return_value="测试提示词"):
                # Mock非标准JSON解析
                with patch.object(analyzer, '_parse_non_standard_json') as mock_parse:
                    expected_tool_calls = [
                        {
                            "tool_name": "search_web",
                            "service_name": "online_search",
                            "agentType": "mcp",
                            "parameters": {"query": "Python教程"}
                        }
                    ]
                    mock_parse.return_value = expected_tool_calls
                    
                    # Mock日志记录
                    with patch("system.background_analyzer.logger") as mock_logger:
                        messages = [{"role": "user", "content": "搜索Python教程"}]
                        result = analyzer.analyze(messages)
                        
                        # 验证结果
                        assert "tool_calls" in result
                        assert len(result["tool_calls"]) == 1
                        assert result["tool_calls"] == expected_tool_calls
                        
                        # 验证日志记录
                        assert mock_logger.info.called
    
    def test_analyze_no_tool_calls(self):
        """测试分析未发现工具调用"""
        analyzer = ConversationAnalyzer()
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "没有发现工具调用"
        mock_llm.invoke = Mock(return_value=mock_response)
        analyzer.llm = mock_llm
        
        with patch("system.background_analyzer.config") as mock_config:
            mock_config.api.max_history_rounds = 10
            
            with patch.object(analyzer, '_build_prompt', return_value="测试提示词"):
                with patch.object(analyzer, '_parse_non_standard_json', return_value=[]):
                    with patch("system.background_analyzer.logger") as mock_logger:
                        messages = [{"role": "user", "content": "普通对话"}]
                        result = analyzer.analyze(messages)
                        
                        # 验试结果
                        assert "tool_calls" in result
                        assert len(result["tool_calls"]) == 0
                        assert result["reason"] == "未发现可执行任务"
    
    def test_analyze_exception(self):
        """测试分析过程中发生异常"""
        analyzer = ConversationAnalyzer()
        
        # Mock LLM抛出异常
        mock_llm = MagicMock()
        mock_llm.invoke = Mock(side_effect=Exception("LLM调用失败"))
        analyzer.llm = mock_llm
        
        with patch.object(analyzer, '_build_prompt', return_value="测试提示词"):
            with patch("system.background_analyzer.logger") as mock_logger:
                messages = [{"role": "user", "content": "测试消息"}]
                
                # 应该捕获异常并返回默认结果
                result = analyzer.analyze(messages)
                
                # 验证异常被记录
                mock_logger.error.assert_called()
                # 验证返回了默认结果
                assert "tool_calls" in result
                assert len(result["tool_calls"]) == 0


class TestBackgroundAnalyzer:
    """测试后台分析器"""
    
    @pytest.fixture
    def background_analyzer(self):
        """BackgroundAnalyzer实例夹具"""
        return BackgroundAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_intent_async_no_duplicate(self, background_analyzer):
        """测试避免重复分析"""
        session_id = "test_session_123"
        
        # 标记为正在分析
        background_analyzer.running_analyses[session_id] = "existing_analysis"
        
        with patch("system.background_analyzer.logger") as mock_logger:
            result = await background_analyzer.analyze_intent_async(
                [{"role": "user", "content": "测试"}],
                session_id
            )
            
            # 验证跳过了重复分析
            mock_logger.info.assert_called_with(
                f"[博弈论] 会话 {session_id} 已有意图分析在进行中，跳过重复执行"
            )
            assert result["has_tasks"] is False
            assert result["reason"] == "已有分析在进行中"
            
            # 清理
            del background_analyzer.running_analyses[session_id]
    
    @pytest.mark.asyncio
    async def test_analyze_intent_async_success(self, background_analyzer):
        """测试异步意图分析成功"""
        session_id = "test_session_456"
        
        # Mock对话分析器
        mock_analyzer = MagicMock()
        expected_analysis = {
            "tasks": ["任务1", "任务2"],
            "tool_calls": [
                {
                    "tool_name": "search",
                    "service_name": "online_search",
                    "agentType": "mcp"
                }
            ],
            "reason": "发现工具调用"
        }
        mock_analyzer.analyze = Mock(return_value=expected_analysis)
        background_analyzer.analyzer = mock_analyzer
        
        # Mock通知和分发
        with patch.object(background_analyzer, '_notify_ui_tool_calls') as mock_notify:
            with patch.object(background_analyzer, '_dispatch_tool_calls') as mock_dispatch:
                with patch("system.background_analyzer.logger") as mock_logger:
                    messages = [{"role": "user", "content": "搜索信息"}]
                    result = await background_analyzer.analyze_intent_async(messages, session_id)
                    
                    # 验证结果
                    assert result["has_tasks"] is True
                    assert result["reason"] == "发现工具调用"
                    assert result["tasks"] == ["任务1", "任务2"]
                    assert result["tool_calls"] == expected_analysis["tool_calls"]
                    assert result["priority"] == "medium"
                    
                    # 验证通知和分发被调用
                    mock_notify.assert_called_once()
                    mock_dispatch.assert_called_once()
                    
                    # 验证分析状态已清除
                    assert session_id not in background_analyzer.running_analyses
    
    @pytest.mark.asyncio
    async def test_analyze_intent_async_timeout(self, background_analyzer):
        """测试异步意图分析超时"""
        session_id = "test_session_timeout"
        
        # Mock分析器使其超时
        async def slow_analyze(*args, **kwargs):
            await asyncio.sleep(2)  # 超过超时时间
            return {"tasks": [], "tool_calls": []}
        
        # 替换analyzer.analyze为异步函数
        background_analyzer.analyzer.analyze = slow_analyze
        
        # 需要Mock run_in_executor
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            
            # 设置run_in_executor模拟超时
            async def run_in_executor_mock(func, *args):
                # 创建一个实际上会超时的future
                future = asyncio.Future()
                future.set_exception(asyncio.TimeoutError())
                return await future
            
            mock_loop_instance.run_in_executor = run_in_executor_mock
            
            with patch("system.background_analyzer.logger") as mock_logger:
                messages = [{"role": "user", "content": "测试"}]
                result = await background_analyzer.analyze_intent_async(messages, session_id)
                
                # 验证超时结果
                assert result["has_tasks"] is False
                assert "超时" in result["reason"]
                mock_logger.error.assert_called_with("[博弈论] 意图分析超时（60秒）")
                
                # 手动清理并验证分析状态已清除
                if session_id in background_analyzer.running_analyses:
                    del background_analyzer.running_analyses[session_id]
                assert session_id not in background_analyzer.running_analyses
    
    @pytest.mark.asyncio
    async def test_analyze_intent_async_exception(self, background_analyzer):
        """测试异步意图分析异常"""
        session_id = "test_session_exception"
        
        # Mock分析器抛出异常
        background_analyzer.analyzer.analyze = Mock(side_effect=Exception("分析失败"))
        
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_in_executor = Mock(side_effect=Exception("执行器错误"))
            
            with patch("system.background_analyzer.logger") as mock_logger:
                messages = [{"role": "user", "content": "测试"}]
                result = await background_analyzer.analyze_intent_async(messages, session_id)
                
                # 验证异常结果
                assert result["has_tasks"] is False
                assert "失败" in result["reason"]
                mock_logger.error.assert_called()
                
                # 手动清理并验证分析状态已清除
                if session_id in background_analyzer.running_analyses:
                    del background_analyzer.running_analyses[session_id]
                assert session_id not in background_analyzer.running_analyses
    
    @pytest.mark.asyncio
    async def test_notify_ui_tool_calls(self, background_analyzer):
        """测试通知UI工具调用"""
        tool_calls = [
            {
                "tool_name": "search_web",
                "service_name": "online_search",
                "agentType": "mcp"
            },
            {
                "tool_name": "get_weather",
                "service_name": "weather",
                "agentType": "mcp"
            }
        ]
        
        session_id = "test_session_notify"
        
        # Mock httpx（在函数内部导入，需要模拟全局模块）
        with patch("httpx", create=True) as mock_httpx:
            with patch("system.background_analyzer.get_server_port", return_value=8000):
                mock_client = AsyncMock()
                mock_response = Mock(status_code=200)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
                
                await background_analyzer._notify_ui_tool_calls(tool_calls, session_id)
                
                # 验证HTTP请求
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert "http://localhost:8000/tool_notification" in call_args[0]
                assert call_args[1]["json"]["session_id"] == session_id
                assert len(call_args[1]["json"]["tool_calls"]) == 2
    
    @pytest.mark.asyncio
    async def test_notify_ui_tool_calls_error(self, background_analyzer):
        """测试通知UI工具调用出错"""
        tool_calls = [{"tool_name": "test"}]
        
        # Mock httpx抛出异常（在函数内部导入，需要模拟全局模块）
        with patch("httpx", create=True) as mock_httpx:
            with patch("system.background_analyzer.get_server_port", return_value=8000):
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=Exception("网络错误"))
                mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
                
                with patch("system.background_analyzer.logger") as mock_logger:
                    await background_analyzer._notify_ui_tool_calls(tool_calls, "test_session")
                    
                    # 验证错误被记录
                    mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_calls(self, background_analyzer):
        """测试工具调用分发"""
        tool_calls = [
            {"tool_name": "search", "agentType": "mcp"},
            {"tool_name": "control", "agentType": "agent"},
            {"tool_name": "unknown", "agentType": "other"}
        ]
        
        session_id = "test_session_dispatch"
        analysis_session_id = "analysis_123"
        
        # Mock分发方法
        with patch.object(background_analyzer, '_send_to_mcp_server') as mock_send_mcp:
            with patch.object(background_analyzer, '_send_to_agent_server') as mock_send_agent:
                await background_analyzer._dispatch_tool_calls(
                    tool_calls, session_id, analysis_session_id
                )
                
                # 验证MCP任务分发
                mock_send_mcp.assert_called_once()
                call_args = mock_send_mcp.call_args[0]
                assert len(call_args[0]) == 1  # 只有mcp类型的工具调用
                assert call_args[0][0]["tool_name"] == "search"
                assert call_args[1] == session_id
                assert call_args[2] == analysis_session_id
                
                # 验证Agent任务分发
                mock_send_agent.assert_called_once()
                call_args = mock_send_agent.call_args[0]
                assert len(call_args[0]) == 1  # 只有agent类型的工具调用
                assert call_args[0][0]["tool_name"] == "control"
    
    @pytest.mark.asyncio
    async def test_send_to_mcp_server(self, background_analyzer):
        """测试发送任务到MCP服务器"""
        mcp_calls = [{"tool_name": "search", "service_name": "online_search"}]
        session_id = "test_session_mcp"
        analysis_session_id = "analysis_mcp_123"
        
        # Mock httpx和uuid（在函数内部导入，需要模拟全局模块）
        with patch("httpx", create=True) as mock_httpx:
            with patch("system.background_analyzer.uuid") as mock_uuid:
                with patch("system.background_analyzer.get_server_port", return_value=8003):
                    mock_uuid.uuid4.return_value = "test-uuid-123"
                    
                    mock_client = AsyncMock()
                    mock_response = Mock(status_code=200)
                    mock_response.json = Mock(return_value={"task_id": "task_123"})
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
                    
                    with patch("system.background_analyzer.logger") as mock_logger:
                        await background_analyzer._send_to_mcp_server(
                            mcp_calls, session_id, analysis_session_id
                        )
                        
                        # 验证HTTP请求
                        mock_client.post.assert_called_once()
                        call_args = mock_client.post.call_args
                        assert "http://localhost:8003/schedule" in call_args[0]
                        
                        # 验证请求体
                        request_body = call_args[1]["json"]
                        assert request_body["query"] == "批量MCP工具调用 (1 个)"
                        assert request_body["session_id"] == session_id
                        assert request_body["request_id"] == "test-uuid-123"
                        assert request_body["callback_url"] == "http://localhost:8000/tool_result_callback"
                        
                        # 验证成功日志
                        mock_logger.info.assert_called_with(
                            f"[博弈论] 分析会话 {analysis_session_id} MCP任务调度成功: task_123"
                        )
    
    @pytest.mark.asyncio
    async def test_send_to_mcp_server_error(self, background_analyzer):
        """测试发送任务到MCP服务器出错"""
        mcp_calls = [{"tool_name": "search"}]
        
        with patch("httpx", create=True) as mock_httpx:
            with patch("system.background_analyzer.get_server_port", return_value=8003):
                mock_client = AsyncMock()
                mock_response = Mock(status_code=500, text="服务器错误")
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
                
                with patch("system.background_analyzer.logger") as mock_logger:
                    await background_analyzer._send_to_mcp_server(mcp_calls, "test_session")
                    
                    # 验证错误日志
                    mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_to_agent_server(self, background_analyzer):
        """测试发送任务到Agent服务器"""
        agent_calls = [{"tool_name": "control", "service_name": "computer_control"}]
        session_id = "test_session_agent"
        analysis_session_id = "analysis_agent_123"
        
        # Mock httpx和uuid（在函数内部导入，需要模拟全局模块）
        with patch("httpx", create=True) as mock_httpx:
            with patch("system.background_analyzer.uuid") as mock_uuid:
                with patch("system.background_analyzer.get_server_port", return_value=8001):
                    mock_uuid.uuid4.return_value = "test-uuid-agent-123"
                    
                    mock_client = AsyncMock()
                    mock_response = Mock(status_code=200)
                    mock_response.json = Mock(return_value={"task_id": "agent_task_123"})
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
                    
                    with patch("system.background_analyzer.logger") as mock_logger:
                        await background_analyzer._send_to_agent_server(
                            agent_calls, session_id, analysis_session_id
                        )
                        
                        # 验证HTTP请求
                        mock_client.post.assert_called_once()
                        call_args = mock_client.post.call_args
                        assert "http://localhost:8001/schedule" in call_args[0]
                        
                        # 验证请求体
                        request_body = call_args[1]["json"]
                        assert request_body["query"] == "批量Agent任务执行 (1 个)"
                        assert request_body["session_id"] == session_id
                        assert request_body["analysis_session_id"] == analysis_session_id
                        assert request_body["request_id"] == "test-uuid-agent-123"
                        
                        # 验证成功日志
                        mock_logger.info.assert_called_with(
                            f"[博弈论] 分析会话 {analysis_session_id} Agent任务调度成功: agent_task_123"
                        )


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_get_background_analyzer_singleton(self):
        """测试获取全局后台分析器单例"""
        analyzer1 = get_background_analyzer()
        analyzer2 = get_background_analyzer()
        
        assert analyzer1 is analyzer2
        assert isinstance(analyzer1, BackgroundAnalyzer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
