"""
llm_service.py 模块测试

测试LLM服务的核心功能：
- LLM服务初始化
- 聊天补全流式响应
- 错误处理
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from apiserver.llm_service import get_llm_service, LLMService


class TestLLMServiceInitialization:
    """测试LLM服务初始化"""
    
    def test_get_llm_service_singleton(self):
        """测试获取LLM服务单例"""
        service1 = get_llm_service()
        service2 = get_llm_service()
        
        assert service1 is service2, "get_llm_service应该返回单例实例"
    
    def test_llm_service_init_with_config(self):
        """测试LLM服务使用配置初始化"""
        with patch("apiserver.llm_service.config") as mock_config:
            mock_config.api.api_key = "test_key"
            mock_config.api.base_url = "https://api.test.com"
            mock_config.api.model = "test-model"
            mock_config.api.temperature = 0.7
            mock_config.api.max_tokens = 1000
            
            # Mock OpenAI客户端
            with patch("apiserver.llm_service.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                
                service = LLMService()
                
                # 验证OpenAI客户端已初始化
                mock_openai.assert_called_once_with(
                    api_key="test_key",
                    base_url="https://api.test.com"
                )
                assert service.client == mock_client
                assert service.model == "test-model"
                assert service.temperature == 0.7
                assert service.max_tokens == 1000


class TestLLMServiceChatCompletion:
    """测试LLM聊天补全"""
    
    @pytest.fixture
    def llm_service(self):
        """LLM服务实例夹具"""
        with patch("apiserver.llm_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            service = LLMService()
            service.client = mock_client
            service.model = "test-model"
            service.temperature = 0.7
            service.max_tokens = 1000
            
            return service
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_success(self, llm_service):
        """测试流式聊天补全成功"""
        # Mock流式响应
        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content="测试回复"))]
        
        mock_stream = Mock()
        mock_stream.__aiter__ = Mock(return_value=AsyncMock())
        mock_stream.__aiter__.return_value.__anext__ = AsyncMock(
            side_effect=[mock_chunk, StopAsyncIteration]
        )
        
        llm_service.client.chat.completions.create = Mock(return_value=mock_stream)
        
        messages = [{"role": "user", "content": "你好"}]
        
        # 收集流式响应
        responses = []
        async for chunk in llm_service.chat_completion_stream(messages):
            responses.append(chunk)
        
        # 验证响应
        assert len(responses) == 1
        assert responses[0] == {"content": "测试回复"}
        
        # 验证OpenAI调用
        llm_service.client.chat.completions.create.assert_called_once_with(
            model="test-model",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True
        )
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_empty_response(self, llm_service):
        """测试流式聊天补全空响应"""
        mock_stream = Mock()
        mock_stream.__aiter__ = Mock(return_value=AsyncMock())
        mock_stream.__aiter__.return_value.__anext__ = AsyncMock(
            side_effect=StopAsyncIteration
        )
        
        llm_service.client.chat.completions.create = Mock(return_value=mock_stream)
        
        messages = [{"role": "user", "content": "你好"}]
        
        responses = []
        async for chunk in llm_service.chat_completion_stream(messages):
            responses.append(chunk)
        
        # 应该没有响应
        assert len(responses) == 0
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_exception(self, llm_service):
        """测试流式聊天补全异常"""
        llm_service.client.chat.completions.create = Mock(
            side_effect=Exception("API错误")
        )
        
        messages = [{"role": "user", "content": "你好"}]
        
        # 应该抛出异常
        with pytest.raises(Exception, match="API错误"):
            async for _ in llm_service.chat_completion_stream(messages):
                pass


class TestLLMServiceEdgeCases:
    """测试LLM服务边界情况"""
    
    def test_llm_service_with_missing_config(self):
        """测试缺少配置的LLM服务初始化"""
        with patch("apiserver.llm_service.config") as mock_config:
            mock_config.api = None
            
            with pytest.raises(AttributeError):
                LLMService()
    
    def test_chat_completion_with_empty_messages(self):
        """测试空消息列表的聊天补全"""
        with patch("apiserver.llm_service.OpenAI") as mock_openai:
            service = LLMService()
            
            # 空消息列表应该抛出异常
            with pytest.raises(ValueError):
                service.chat_completion_stream([])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])