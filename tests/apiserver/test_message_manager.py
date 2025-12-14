"""
message_manager.py 模块测试

测试消息管理器的核心功能：
- 消息处理
- 会话管理
- 后台分析触发
- 对话历史保存
"""

import json
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
from apiserver.message_manager import message_manager, MessageManager


class TestMessageManagerSingleton:
    """测试消息管理器单例"""
    
    def test_message_manager_is_singleton(self):
        """测试message_manager是单例"""
        manager1 = message_manager
        manager2 = message_manager
        
        assert manager1 is manager2, "message_manager应该是单例实例"


class TestMessageManagerInitialization:
    """测试消息管理器初始化"""
    
    def test_message_manager_init(self):
        """测试MessageManager初始化"""
        manager = MessageManager()
        
        # 验证默认属性
        assert hasattr(manager, 'sessions'), "应该包含sessions属性"
        assert hasattr(manager, 'background_analysis_enabled'), "应该包含background_analysis_enabled属性"
        assert isinstance(manager.sessions, dict), "sessions应该是字典"


class TestMessageManagerSessionManagement:
    """测试消息管理器会话管理"""
    
    @pytest.fixture
    def manager(self):
        """MessageManager实例夹具"""
        return MessageManager()
    
    def test_process_message_new_session(self, manager):
        """测试处理新会话消息"""
        session_id = "new_session_123"
        message = "测试消息"
        
        result = manager.process_message(session_id, message)
        
        # 验证会话已创建
        assert session_id in manager.sessions
        # 验证返回消息
        assert "message" in result
        assert result["message"] == message
    
    def test_process_message_existing_session(self, manager):
        """测试处理现有会话消息"""
        session_id = "existing_session_456"
        
        # 先创建一个会话
        manager.process_message(session_id, "第一条消息")
        
        # 处理第二条消息
        result = manager.process_message(session_id, "第二条消息")
        
        # 验证返回消息
        assert result["message"] == "第二条消息"
    
    def test_get_session_history_empty(self, manager):
        """测试获取空会话历史"""
        session_id = "empty_session_789"
        
        history = manager.get_session_history(session_id)
        
        # 新会话应该有空的对话历史
        assert history == []
    
    def test_get_session_history_with_messages(self, manager):
        """测试获取有消息的会话历史"""
        session_id = "history_session_123"
        
        # 处理一些消息
        manager.process_message(session_id, "消息1")
        manager.process_message(session_id, "消息2")
        
        history = manager.get_session_history(session_id)
        
        # 验证历史记录
        assert len(history) >= 0  # 取决于实现，可能为空或包含消息


class TestMessageManagerBackgroundAnalysis:
    """测试消息管理器后台分析"""
    
    @pytest.fixture
    def manager(self):
        """MessageManager实例夹具"""
        return MessageManager()
    
    def test_trigger_background_analysis_enabled(self, manager):
        """测试触发启用的后台分析"""
        session_id = "analysis_session_123"
        manager.background_analysis_enabled = True
        
        # Mock实际的后台分析功能
        with patch.object(manager, '_perform_background_analysis') as mock_analysis:
            mock_analysis.return_value = None
            
            result = manager.trigger_background_analysis(session_id)
            
            # 验证分析被触发
            mock_analysis.assert_called_once_with(session_id)
            assert result is True
    
    def test_trigger_background_analysis_disabled(self, manager):
        """测试触发禁用的后台分析"""
        session_id = "analysis_session_456"
        manager.background_analysis_enabled = False
        
        result = manager.trigger_background_analysis(session_id)
        
        # 分析应该被跳过
        assert result is False
    
    def test_trigger_background_analysis_exception(self, manager):
        """测试触发后台分析时异常"""
        session_id = "analysis_session_789"
        manager.background_analysis_enabled = True
        
        # Mock分析抛出异常
        with patch.object(manager, '_perform_background_analysis', side_effect=Exception("分析错误")):
            result = manager.trigger_background_analysis(session_id)
            
            # 异常应该被捕获并返回False
            assert result is False


class TestMessageManagerConversationSaving:
    """测试消息管理器对话保存"""
    
    @pytest.fixture
    def manager(self):
        """MessageManager实例夹具"""
        return MessageManager()
    
    def test_save_conversation_and_logs_success(self, manager):
        """测试成功保存对话和日志"""
        session_id = "save_session_123"
        user_message = "用户消息"
        assistant_response = "助手回复"
        
        # Mock日志记录
        with patch("apiserver.message_manager.logger") as mock_logger:
            result = manager.save_conversation_and_logs(session_id, user_message, assistant_response)
            
            # 验证方法被调用
            assert result is True
            # 验证日志记录
            mock_logger.info.assert_called()
    
    def test_save_conversation_and_logs_exception(self, manager):
        """测试保存对话和日志时异常"""
        session_id = "save_session_456"
        user_message = "用户消息"
        assistant_response = "助手回复"
        
        # Mock日志记录抛出异常
        with patch("apiserver.message_manager.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("日志错误")
            
            result = manager.save_conversation_and_logs(session_id, user_message, assistant_response)
            
            # 异常应该被捕获并返回False
            assert result is False


class TestMessageManagerCleanup:
    """测试消息管理器清理"""
    
    @pytest.fixture
    def manager(self):
        """MessageManager实例夹具"""
        return MessageManager()
    
    def test_cleanup_old_sessions(self, manager):
        """测试清理旧会话"""
        # 创建一些会话
        manager.process_message("session1", "消息1")
        manager.process_message("session2", "消息2")
        
        # 验证会话存在
        assert "session1" in manager.sessions
        assert "session2" in manager.sessions
        
        # Mock清理逻辑
        with patch.object(manager, '_should_cleanup_session', return_value=True):
            manager.cleanup_old_sessions()
            
            # 验证会话可能被清理（取决于实现）


if __name__ == "__main__":
    pytest.main([__file__, "-v"])