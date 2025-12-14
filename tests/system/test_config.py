"""
config.py 模块测试

测试NagaAgent配置系统的核心功能：
- 配置类的验证逻辑
- 配置文件加载和解析
- 配置热更新机制
- 提示词管理功能
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from nagaagent_core.vendors import json5  # 导入json5用于测试

import pytest
from system.config import (
    # 配置类
    NagaConfig,
    SystemConfig,
    APIConfig,
    APIServerConfig,
    GRAGConfig,
    HandoffConfig,
    BrowserConfig,
    TTSConfig,
    ASRConfig,
    FilterConfig,
    DifficultyConfig,
    ScoringConfig,
    ComputerControlConfig,
    MQTTConfig,
    UIConfig,
    Live2DConfig,
    VoiceRealtimeConfig,
    NagaPortalConfig,
    OnlineSearchConfig,
    SystemCheckConfig,
    GameModuleConfig,
    # 函数
    load_config,
    reload_config,
    hot_reload_config,
    get_config,
    get_prompt,
    save_prompt,
    get_prompt_manager,
    get_ai_name,
    get_server_port,
    get_all_server_ports,
    # 全局实例
    config,
    server_ports,
    add_config_listener,
    remove_config_listener,
    notify_config_changed,
)


class TestConfigClasses:
    """测试配置数据类"""
    
    def test_system_config_validation(self):
        """测试SystemConfig的字段验证"""
        # 正常情况
        cfg = SystemConfig(
            version="4.0.1",
            ai_name="测试AI",
            voice_enabled=True,
            stream_mode=True,
            debug=True,
            log_level="DEBUG",
            save_prompts=True,
        )
        assert cfg.version == "4.0.1"
        assert cfg.ai_name == "测试AI"
        assert cfg.voice_enabled is True
        assert cfg.debug is True
        assert cfg.log_level == "DEBUG"
        assert cfg.save_prompts is True
        
        # 验证log_level转换
        cfg2 = SystemConfig(log_level="info")
        assert cfg2.log_level == "INFO"
        
        # 测试无效的log_level
        with pytest.raises(ValueError, match="日志级别必须是以下之一"):
            SystemConfig(log_level="INVALID")
    
    def test_api_config_bounds_validation(self):
        """测试APIConfig的边界值验证"""
        # 正常情况
        cfg = APIConfig(
            api_key="test_key",
            base_url="https://api.test.com",
            model="test-model",
            temperature=0.7,
            max_tokens=10000,
            max_history_rounds=100,
            persistent_context=True,
            context_load_days=3,
            context_parse_logs=True,
            applied_proxy=True,
        )
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 10000
        assert cfg.max_history_rounds == 100
        
        # 测试边界值
        with pytest.raises(ValueError):
            APIConfig(temperature=-0.1)
        
        with pytest.raises(ValueError):
            APIConfig(temperature=2.1)
        
        with pytest.raises(ValueError):
            APIConfig(max_tokens=0)
        
        with pytest.raises(ValueError):
            APIConfig(max_tokens=32769)
        
        with pytest.raises(ValueError):
            APIConfig(max_history_rounds=0)
        
        with pytest.raises(ValueError):
            APIConfig(max_history_rounds=201)
    
    def test_server_ports_config(self):
        """测试服务器端口配置"""
        # 默认值
        from system.config import server_ports
        assert server_ports.api_server == 8000
        assert server_ports.agent_server == 8001
        assert server_ports.mcp_server == 8003
        assert server_ports.tts_server == 5048
        assert server_ports.asr_server == 5060
        
        # 测试获取端口函数
        assert get_server_port("api_server") == 8000
        assert get_server_port("agent_server") == 8001
        
        all_ports = get_all_server_ports()
        assert all_ports["api_server"] == 8000
        assert all_ports["agent_server"] == 8001
        assert all_ports["mcp_server"] == 8003
        assert all_ports["tts_server"] == 5048
        assert all_ports["asr_server"] == 5060
    
    def test_naga_config_defaults(self):
        """测试NagaConfig默认值"""
        cfg = NagaConfig()
        assert cfg.system.version == "4.0.0"
        assert cfg.system.ai_name == "娜迦日达"
        assert cfg.api.api_key == "sk-placeholder-key-not-set"
        assert cfg.api.base_url == "https://api.deepseek.com/v1"
        assert cfg.api.model == "deepseek-chat"
        assert cfg.api_server.enabled is True
        assert cfg.api_server.host == "127.0.0.1"
        assert cfg.api_server.port == 8000  # 从server_ports获取
        assert cfg.grag.enabled is False
        assert cfg.handoff.max_loop_stream == 5
        assert cfg.handoff.max_loop_non_stream == 5
        assert cfg.browser.playwright_headless is False
        assert cfg.tts.port == 5048
        assert cfg.mqtt.enabled is False
        assert cfg.ui.user_name == "用户"
        assert cfg.live2d.enabled is True
        assert cfg.voice_realtime.enabled is False
        assert cfg.naga_portal.portal_url == "https://naga.furina.chat/"
        assert cfg.online_search.searxng_url == "http://localhost:8080"
        assert cfg.system_check.passed is False
        assert cfg.computer_control.enabled is True
        assert cfg.game.enabled is False


class TestConfigLoading:
    """测试配置文件加载功能"""
    
    def test_load_config_default_when_missing(self, temp_dir: Path):
        """测试配置文件不存在时使用默认配置"""
        with patch("system.config.Path") as mock_path:
            # 模拟配置文件不存在
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = False
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_config_file
            
            # 调用load_config
            result = load_config()
            
            # 应该返回默认配置
            assert isinstance(result, NagaConfig)
            assert result.system.version == "4.0.0"
            assert result.system.ai_name == "娜迦日达"
    
    def test_load_config_with_json5_comments(self, temp_dir: Path):
        """测试加载包含注释的JSON5配置文件"""
        config_file = temp_dir / "config.json"
        config_content = """{
            // 这是一个注释
            "system": {
                "version": "4.0.1",
                "ai_name": "测试名称",
                # 另一个注释
                "debug": true
            },
            "api": {
                "api_key": "test_key_123",
                "base_url": "https://api.test.com/v1"
            }
        }"""
        
        config_file.write_text(config_content, encoding="utf-8")
        
        with patch("system.config.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            # Mock charset_normalizer检测编码
            with patch("system.config.from_path") as mock_from_path:
                mock_result = MagicMock()
                mock_result.best.return_value = MagicMock(encoding="utf-8")
                mock_from_path.return_value = mock_result
                
                # Mock json5.load
                with patch("system.config.json5.load") as mock_json5_load:
                    expected_config = {
                        "system": {
                            "version": "4.0.1",
                            "ai_name": "测试名称",
                            "debug": True,
                            "log_dir": str(temp_dir / "logs")
                        },
                        "api": {
                            "api_key": "test_key_123",
                            "base_url": "https://api.test.com/v1"
                        }
                    }
                    mock_json5_load.return_value = expected_config
                    
                    result = load_config()
                    
                    # 验证json5.load被调用
                    mock_json5_load.assert_called_once()
                    # 验证配置被正确解析
                    assert result.system.version == "4.0.1"
                    assert result.system.ai_name == "测试名称"
                    assert result.system.debug is True
                    assert result.api.api_key == "test_key_123"
                    assert result.api.base_url == "https://api.test.com/v1"
    
    def test_load_config_with_invalid_json5_fallback(self, temp_dir: Path):
        """测试JSON5解析失败时回退到标准JSON"""
        config_file = temp_dir / "config.json"
        config_content = """{
            "system": {
                "version": "4.0.1",
                "ai_name": "测试名称"
            }
        }"""
        
        config_file.write_text(config_content, encoding="utf-8")
        
        with patch("system.config.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            with patch("system.config.from_path") as mock_from_path:
                mock_result = MagicMock()
                mock_result.best.return_value = MagicMock(encoding="utf-8")
                mock_from_path.return_value = mock_result
                
                # 模拟json5.load失败
                with patch("system.config.json5.load", side_effect=Exception("JSON5解析错误")):
                    # Mock json.loads作为回退
                    with patch("system.config.json.loads") as mock_json_loads:
                        expected_config = {
                            "system": {
                                "version": "4.0.1",
                                "ai_name": "测试名称",
                                "log_dir": str(temp_dir / "logs")
                            }
                        }
                        mock_json_loads.return_value = expected_config
                        
                        result = load_config()
                        
                        # 验证回退机制被触发
                        mock_json_loads.assert_called_once()
                        assert result.system.version == "4.0.1"
                        assert result.system.ai_name == "测试名称"


class TestConfigManagement:
    """测试配置管理功能"""
    
    def test_get_ai_name(self):
        """测试获取AI名称函数"""
        # 使用当前全局配置
        ai_name = get_ai_name()
        assert ai_name == "娜迦日达"  # 默认值
    
    def test_config_listeners(self):
        """测试配置监听器机制"""
        listener_called = []
        
        def test_listener():
            listener_called.append(True)
        
        # 添加监听器
        add_config_listener(test_listener)
        
        # 通知变更
        notify_config_changed()
        
        # 验证监听器被调用
        assert len(listener_called) == 1
        assert listener_called[0] is True
        
        # 移除监听器
        remove_config_listener(test_listener)
        
        # 再次通知，不应该再被调用
        notify_config_changed()
        assert len(listener_called) == 1  # 仍然为1，没有增加
    
    def test_reload_config(self):
        """测试重新加载配置"""
        original_config = get_config()
        
        # Mock load_config返回新配置
        new_config = NagaConfig()
        new_config.system.version = "4.0.2"
        
        with patch("system.config.load_config", return_value=new_config):
            with patch("system.config.notify_config_changed") as mock_notify:
                result = reload_config()
                
                # 验证配置已更新
                assert result.system.version == "4.0.2"
                # 验证通知被调用
                mock_notify.assert_called_once()
    
    def test_hot_reload_config(self):
        """测试热更新配置"""
        # Mock必要函数
        with patch("system.config.load_config") as mock_load:
            with patch("system.config.notify_config_changed") as mock_notify:
                with patch("system.config.config", new=MagicMock()) as mock_global_config:
                    # 设置模拟返回值
                    old_config = MagicMock()
                    old_config.system.version = "4.0.0"
                    new_config = MagicMock()
                    new_config.system.version = "4.0.1"
                    
                    mock_global_config = old_config  # 设置全局配置
                    mock_load.return_value = new_config
                    
                    # 调用热更新
                    result = hot_reload_config()
                    
                    # 验证load_config被调用
                    mock_load.assert_called_once()
                    # 验证notify_config_changed被调用
                    mock_notify.assert_called_once()
                    # 验证返回新配置
                    assert result == new_config


class TestPromptManagement:
    """测试提示词管理功能"""
    
    def test_get_prompt_manager_singleton(self):
        """测试提示词管理器单例模式"""
        manager1 = get_prompt_manager()
        manager2 = get_prompt_manager()
        assert manager1 is manager2
    
    def test_prompt_operations(self, temp_dir: Path):
        """测试提示词获取和保存"""
        # 创建临时提示词文件
        prompts_dir = temp_dir / "prompts"
        prompts_dir.mkdir()
        test_prompt_file = prompts_dir / "test_prompt.txt"
        test_prompt_content = "这是一个测试提示词，参数: {param1}, {param2}"
        test_prompt_file.write_text(test_prompt_content, encoding="utf-8")
        
        # Mock PromptManager的初始化
        with patch("system.config.PromptManager") as MockPromptManager:
            mock_manager = Mock()
            mock_manager.get_prompt = Mock(
                side_effect=lambda name, **kwargs: test_prompt_content.format(**kwargs) if name == "test_prompt" else None
            )
            mock_manager.save_prompt = Mock()
            MockPromptManager.return_value = mock_manager
            
            # 重置全局管理器以使用Mock
            import system.config
            system.config._prompt_manager = None
            
            # 测试获取提示词（带参数）
            result = get_prompt("test_prompt", param1="值1", param2="值2")
            assert result == "这是一个测试提示词，参数: 值1, 值2"
            
            # 测试保存提示词
            save_prompt("new_prompt", "新提示词内容")
            mock_manager.save_prompt.assert_called_once_with("new_prompt", "新提示词内容")


class TestConfigFunctions:
    """测试配置相关的工具函数"""
    
    def test_setup_environment(self):
        """测试环境变量设置"""
        import os
        
        # 保存原始环境变量
        original_env = {}
        for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", 
                   "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "TOKENIZERS_PARALLELISM"]:
            if key in os.environ:
                original_env[key] = os.environ[key]
        
        try:
            # 导入并调用setup_environment
            from system.config import setup_environment
            setup_environment()
            
            # 验证环境变量被设置
            assert os.environ.get("OMP_NUM_THREADS") == "1"
            assert os.environ.get("MKL_NUM_THREADS") == "1"
            assert os.environ.get("OPENBLAS_NUM_THREADS") == "1"
            assert os.environ.get("VECLIB_MAXIMUM_THREADS") == "1"
            assert os.environ.get("NUMEXPR_NUM_THREADS") == "1"
            assert os.environ.get("TOKENIZERS_PARALLELISM") == "false"
            
        finally:
            # 恢复原始环境变量
            for key, value in original_env.items():
                os.environ[key] = value
            for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                       "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "TOKENIZERS_PARALLELISM"]:
                if key not in original_env:
                    os.environ.pop(key, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])