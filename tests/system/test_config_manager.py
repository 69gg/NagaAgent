"""
config_manager.py 模块测试

测试配置管理器的核心功能：
- 配置热更新机制
- 模块重新加载注册
- 配置文件监视
- 配置快照管理
"""

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock, call

import pytest
import pytest_asyncio
from system.config_manager import (
    ConfigManager,
    config_manager,
    register_module_reload,
    register_reload_callback,
    update_config,
    start_config_watcher,
    stop_config_watcher,
    get_config_snapshot,
    restore_config_snapshot,
)


class TestConfigManagerInitialization:
    """测试ConfigManager初始化"""
    
    def test_init(self):
        """测试ConfigManager初始化"""
        manager = ConfigManager()
        
        assert isinstance(manager._modules_to_reload, list)
        assert isinstance(manager._reload_callbacks, list)
        assert manager._config_watcher_thread is None
        assert manager._stop_watching is False
        
        # 验证配置监听器已注册
        from system.config import _config_listeners
        assert manager._on_config_changed in _config_listeners
    
    def test_singleton_instance(self):
        """测试配置管理器单例实例"""
        assert config_manager is not None
        assert isinstance(config_manager, ConfigManager)


class TestModuleRegistration:
    """测试模块注册功能"""
    
    def test_register_module_reload(self):
        """测试注册模块重新加载"""
        manager = ConfigManager()
        
        # 注册模块
        manager.register_module_reload("test.module1")
        manager.register_module_reload("test.module2")
        
        assert "test.module1" in manager._modules_to_reload
        assert "test.module2" in manager._modules_to_reload
        assert len(manager._modules_to_reload) == 2
        
        # 测试重复注册不会添加重复项
        manager.register_module_reload("test.module1")
        assert len(manager._modules_to_reload) == 2
    
    def test_register_reload_callback(self):
        """测试注册重新加载回调"""
        manager = ConfigManager()
        
        def callback1():
            pass
        
        def callback2():
            pass
        
        # 注册回调
        manager.register_reload_callback(callback1)
        manager.register_reload_callback(callback2)
        
        assert callback1 in manager._reload_callbacks
        assert callback2 in manager._reload_callbacks
        assert len(manager._reload_callbacks) == 2


class TestConfigChangeHandling:
    """测试配置变更处理"""
    
    def test_on_config_changed_with_callbacks(self):
        """测试配置变更时执行回调"""
        manager = ConfigManager()
        
        # 创建测试回调
        callback1_called = []
        callback2_called = []
        
        def callback1():
            callback1_called.append(True)
        
        def callback2():
            callback2_called.append(True)
        
        manager.register_reload_callback(callback1)
        manager.register_reload_callback(callback2)
        
        # 触发配置变更
        manager._on_config_changed()
        
        # 验证回调被调用
        assert len(callback1_called) == 1
        assert len(callback2_called) == 1
    
    def test_on_config_changed_with_callback_error(self):
        """测试回调执行出错时的处理"""
        manager = ConfigManager()
        
        error_called = []
        good_called = []
        
        def error_callback():
            error_called.append(True)
            raise ValueError("测试错误")
        
        def good_callback():
            good_called.append(True)
        
        manager.register_reload_callback(error_callback)
        manager.register_reload_callback(good_callback)
        
        # 触发配置变更，应该继续执行后续回调
        manager._on_config_changed()
        
        # 验证两个回调都被调用
        assert len(error_called) == 1
        assert len(good_called) == 1
    
    def test_execute_reload_callbacks(self):
        """测试执行重新加载回调"""
        manager = ConfigManager()
        
        callback_results = []
        
        def test_callback():
            callback_results.append("executed")
        
        manager.register_reload_callback(test_callback)
        manager._execute_reload_callbacks()
        
        assert callback_results == ["executed"]
    
    def test_reload_registered_modules(self):
        """测试重新加载注册的模块"""
        import sys
        
        manager = ConfigManager()
        
        # 创建一个模拟模块
        mock_module = MagicMock()
        mock_module.reload_config = Mock()
        sys.modules["test.module.reload"] = mock_module
        
        try:
            # 注册模块
            manager.register_module_reload("test.module.reload")
            
            # 触发重新加载
            manager._reload_registered_modules()
            
            # 验证reload_config被调用
            mock_module.reload_config.assert_called_once()
            
        finally:
            # 清理
            if "test.module.reload" in sys.modules:
                del sys.modules["test.module.reload"]
    
    def test_reload_single_module_missing(self):
        """测试重新加载不存在的模块"""
        manager = ConfigManager()
        
        # 尝试重新加载不存在的模块
        with patch("builtins.print") as mock_print:
            manager._reload_single_module("nonexistent.module")
            
            # 验证打印了警告信息
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "未加载" in call_args or "跳过" in call_args
    
    def test_reload_single_module_no_method(self):
        """测试重新加载没有reload_config方法的模块"""
        import sys
        
        manager = ConfigManager()
        
        # 创建一个没有reload_config方法的模拟模块
        mock_module = MagicMock()
        delattr(mock_module, 'reload_config')  # 确保没有reload_config方法
        sys.modules["test.module.no_method"] = mock_module
        
        try:
            # 注册模块
            manager.register_module_reload("test.module.no_method")
            
            # 触发重新加载
            with patch("builtins.print") as mock_print:
                manager._reload_single_module("test.module.no_method")
                
                # 验证打印了警告信息
                mock_print.assert_called()
                call_args = str(mock_print.call_args)
                assert "没有 reload_config 方法" in call_args or "跳过" in call_args
                
        finally:
            # 清理
            if "test.module.no_method" in sys.modules:
                del sys.modules["test.module.no_method"]


class TestConfigFileOperations:
    """测试配置文件操作"""
    
    def test_load_config_file_success(self, temp_dir: Path):
        """测试成功加载配置文件"""
        manager = ConfigManager()
        
        # 创建测试配置文件
        config_file = temp_dir / "config.json"
        config_data = {
            "system": {"version": "4.0.1"},
            "api": {"api_key": "test_key"}
        }
        config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")
        
        # Mock charset_normalizer
        with patch("system.config_manager.from_path") as mock_from_path:
            mock_result = MagicMock()
            mock_result.best.return_value = MagicMock(encoding="utf-8")
            mock_from_path.return_value = mock_result
            
            # Mock json5.load
            with patch("system.config_manager.json5.load") as mock_json5_load:
                mock_json5_load.return_value = config_data
                
                result = manager._load_config_file(str(config_file))
                
                # 验证结果
                assert result == config_data
                mock_json5_load.assert_called_once()
    
    def test_load_config_file_json5_fallback(self, temp_dir: Path):
        """测试JSON5解析失败时回退到标准JSON"""
        manager = ConfigManager()
        
        config_file = temp_dir / "config.json"
        config_content = '{"system": {"version": "4.0.1"}}'
        config_file.write_text(config_content, encoding="utf-8")
        
        with patch("system.config_manager.from_path") as mock_from_path:
            mock_result = MagicMock()
            mock_result.best.return_value = MagicMock(encoding="utf-8")
            mock_from_path.return_value = mock_result
            
            # 模拟json5.load失败，触发回退
            with patch("system.config_manager.json5.load", side_effect=Exception("JSON5错误")):
                with patch("system.config_manager.json.loads") as mock_json_loads:
                    expected_data = {"system": {"version": "4.0.1"}}
                    mock_json_loads.return_value = expected_data
                    
                    result = manager._load_config_file(str(config_file))
                    
                    # 验证回退机制被触发
                    mock_json_loads.assert_called_once()
                    assert result == expected_data
    
    def test_load_config_file_not_found(self):
        """测试加载不存在的配置文件"""
        manager = ConfigManager()
        
        result = manager._load_config_file("/nonexistent/path/config.json")
        assert result is None
    
    def test_save_config_file_success(self, temp_dir: Path):
        """测试成功保存配置文件"""
        manager = ConfigManager()
        
        config_file = temp_dir / "config.json"
        config_data = {"system": {"version": "4.0.1"}}
        
        # Mock charset_normalizer检测编码
        with patch("system.config_manager.from_path") as mock_from_path:
            mock_result = MagicMock()
            mock_result.best.return_value = MagicMock(encoding="utf-8")
            mock_from_path.return_value = mock_result
            
            # 保存配置
            result = manager._save_config_file(str(config_file), config_data)
            
            # 验证文件被保存
            assert result is True
            assert config_file.exists()
            
            # 验证文件内容
            saved_content = config_file.read_text(encoding="utf-8")
            saved_data = json5.loads(saved_content)
            assert saved_data == config_data
    
    def test_save_config_file_error(self):
        """测试保存配置文件出错"""
        manager = ConfigManager()
        
        # 使用无效路径触发错误
        invalid_path = "/root/nonexistent/config.json"  # 通常没有写入权限
        
        with patch("builtins.print") as mock_print:
            result = manager._save_config_file(invalid_path, {})
            
            # 验证返回False并打印了错误信息
            assert result is False
            mock_print.assert_called()
    
    def test_recursive_update(self):
        """测试递归更新配置字典"""
        manager = ConfigManager()
        
        target = {
            "system": {
                "version": "4.0.0",
                "debug": False,
                "nested": {
                    "value": "old"
                }
            },
            "api": {
                "key": "old_key"
            }
        }
        
        updates = {
            "system": {
                "version": "4.0.1",
                "debug": True,
                "nested": {
                    "value": "new"
                }
            },
            "api": {
                "key": "new_key"
            },
            "new_section": {
                "value": "added"
            }
        }
        
        manager._recursive_update(target, updates)
        
        # 验证更新结果
        assert target["system"]["version"] == "4.0.1"
        assert target["system"]["debug"] is True
        assert target["system"]["nested"]["value"] == "new"
        assert target["api"]["key"] == "new_key"
        assert target["new_section"]["value"] == "added"


class TestConfigUpdate:
    """测试配置更新功能"""
    
    def test_update_config_success(self, temp_dir: Path):
        """测试成功更新配置"""
        manager = ConfigManager()
        
        # 创建测试配置文件
        config_file = temp_dir / "config.json"
        original_config = {
            "system": {"version": "4.0.0", "debug": False},
            "api": {"api_key": "old_key"}
        }
        config_file.write_text(json.dumps(original_config, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Mock路径
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            # Mock加载和保存方法
            with patch.object(manager, '_load_config_file') as mock_load:
                with patch.object(manager, '_save_config_file') as mock_save:
                    with patch("system.config_manager.hot_reload_config") as mock_hot_reload:
                        with patch("time.sleep"):
                            mock_load.return_value = original_config.copy()
                            mock_save.return_value = True
                            
                            # 执行更新
                            updates = {
                                "system": {"debug": True},
                                "api": {"api_key": "new_key"}
                            }
                            result = manager.update_config(updates)
                            
                            # 验证结果
                            assert result is True
                            mock_load.assert_called_once()
                            mock_save.assert_called_once()
                            mock_hot_reload.assert_called_once()
                            
                            # 验证保存时传递了更新后的配置
                            save_args = mock_save.call_args[0]
                            saved_config = save_args[1]
                            assert saved_config["system"]["debug"] is True
                            assert saved_config["api"]["api_key"] == "new_key"
    
    def test_update_config_file_not_found(self):
        """测试配置文件不存在时的更新"""
        manager = ConfigManager()
        
        # Mock路径返回不存在的文件
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.exists.return_value = False
            
            with patch("builtins.print") as mock_print:
                result = manager.update_config({"system": {"debug": True}})
                
                # 验证更新失败
                assert result is False
                mock_print.assert_called()
    
    def test_update_config_load_failure(self, temp_dir: Path):
        """测试配置加载失败时的更新"""
        manager = ConfigManager()
        
        config_file = temp_dir / "config.json"
        config_file.write_text("{}", encoding="utf-8")
        
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            # Mock加载失败
            with patch.object(manager, '_load_config_file', return_value=None):
                with patch("builtins.print") as mock_print:
                    result = manager.update_config({"system": {"debug": True}})
                    
                    # 验证更新失败
                    assert result is False
                    mock_print.assert_called()
    
    def test_update_config_save_failure(self, temp_dir: Path):
        """测试配置保存失败时的更新"""
        manager = ConfigManager()
        
        config_file = temp_dir / "config.json"
        config_file.write_text("{}", encoding="utf-8")
        
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            with patch.object(manager, '_load_config_file') as mock_load:
                with patch.object(manager, '_save_config_file', return_value=False):
                    mock_load.return_value = {}
                    
                    with patch("builtins.print") as mock_print:
                        result = manager.update_config({"system": {"debug": True}})
                        
                        # 验证更新失败
                        assert result is False
                        mock_print.assert_called()


class TestConfigWatcher:
    """测试配置文件监视器"""
    
    def test_start_config_watcher(self):
        """测试启动配置监视器"""
        manager = ConfigManager()
        
        # 确保没有正在运行的监视器
        manager._stop_watching = True
        if manager._config_watcher_thread:
            manager._config_watcher_thread.join(timeout=0.1)
        
        # 启动监视器
        manager.start_config_watcher("/test/config.json")
        
        # 验证线程已创建
        assert manager._config_watcher_thread is not None
        assert manager._stop_watching is False
        assert manager._config_watcher_thread.daemon is True
    
    def test_start_config_watcher_already_running(self):
        """测试重复启动配置监视器"""
        manager = ConfigManager()
        
        # 创建模拟线程
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        manager._config_watcher_thread = mock_thread
        
        # 尝试再次启动
        manager.start_config_watcher("/test/config.json")
        
        # 验证没有创建新线程
        assert manager._config_watcher_thread == mock_thread
    
    def test_stop_config_watcher(self):
        """测试停止配置监视器"""
        manager = ConfigManager()
        
        # 创建模拟线程
        mock_thread = Mock()
        mock_thread.join = Mock()
        manager._config_watcher_thread = mock_thread
        
        # 停止监视器
        manager.stop_config_watcher()
        
        # 验证停止标志设置
        assert manager._stop_watching is True
        # 验证join被调用
        mock_thread.join.assert_called_once_with(timeout=1)
    
    def test_watch_config_file_detects_change(self):
        """测试监视器检测配置文件变化"""
        manager = ConfigManager()
        manager._stop_watching = False
        
        config_file = "/test/config.json"
        
        # Mock文件操作
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getmtime", side_effect=[100, 200]):  # 模拟文件修改时间变化
                with patch("time.sleep") as mock_sleep:
                    with patch("system.config_manager.hot_reload_config") as mock_hot_reload:
                        # 设置睡眠函数在第一次调用后停止循环
                        def stop_after_first_sleep(*args):
                            manager._stop_watching = True
                        mock_sleep.side_effect = stop_after_first_sleep
                        
                        # 运行监视器
                        manager._watch_config_file(config_file)
                        
                        # 验证hot_reload_config被调用
                        mock_hot_reload.assert_called_once()


class TestConfigSnapshot:
    """测试配置快照功能"""
    
    def test_get_config_snapshot_success(self, temp_dir: Path):
        """测试成功获取配置快照"""
        manager = ConfigManager()
        
        # 创建测试配置文件
        config_file = temp_dir / "config.json"
        config_data = {
            "system": {"version": "4.0.1"},
            "api": {"api_key": "test_key"}
        }
        config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")
        
        # Mock路径和charset_normalizer
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            with patch("system.config_manager.from_path") as mock_from_path:
                mock_result = MagicMock()
                mock_result.best.return_value = MagicMock(encoding="utf-8")
                mock_from_path.return_value = mock_result
                
                with patch("system.config_manager.json5.load") as mock_json5_load:
                    mock_json5_load.return_value = config_data
                    
                    snapshot = manager.get_config_snapshot()
                    
                    # 验证快照内容
                    assert snapshot == config_data
    
    def test_get_config_snapshot_fallback(self):
        """测试获取配置快照失败时回退到默认结构"""
        manager = ConfigManager()
        
        # Mock路径指向不存在的文件
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.exists.return_value = False
            
            snapshot = manager.get_config_snapshot()
            
            # 验证返回了默认结构
            assert "system" in snapshot
            assert "api" in snapshot
            assert "api_server" in snapshot
            assert snapshot["system"]["version"] == "4.0"
    
    def test_restore_config_snapshot_success(self, temp_dir: Path):
        """测试成功恢复配置快照"""
        manager = ConfigManager()
        
        config_file = temp_dir / "config.json"
        
        # Mock路径和charset_normalizer
        with patch("system.config_manager.Path") as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value = config_file
            
            with patch("system.config_manager.from_path") as mock_from_path:
                mock_result = MagicMock()
                mock_result.best.return_value = MagicMock(encoding="utf-8")
                mock_from_path.return_value = mock_result
                
                with patch("system.config_manager.hot_reload_config") as mock_hot_reload:
                    snapshot = {
                        "system": {"version": "4.0.1"},
                        "api": {"api_key": "restored_key"}
                    }
                    
                    result = manager.restore_config_snapshot(snapshot)
                    
                    # 验证恢复成功
                    assert result is True
                    mock_hot_reload.assert_called_once()
                    
                    # 验证文件被写入
                    assert config_file.exists()
                    saved_content = config_file.read_text(encoding="utf-8")
                    saved_data = json.loads(saved_content)
                    assert saved_data == snapshot
    
    def test_restore_config_snapshot_error(self):
        """测试恢复配置快照出错"""
        manager = ConfigManager()
        
        # 使用无效快照触发错误
        invalid_snapshot = {"invalid": object()}  # 包含不可序列化对象
        
        with patch("builtins.print") as mock_print:
            result = manager.restore_config_snapshot(invalid_snapshot)
            
            # 验证恢复失败
            assert result is False
            mock_print.assert_called()


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_register_module_reload_function(self):
        """测试register_module_reload便捷函数"""
        with patch.object(config_manager, 'register_module_reload') as mock_register:
            register_module_reload("test.module")
            mock_register.assert_called_once_with("test.module")
    
    def test_register_reload_callback_function(self):
        """测试register_reload_callback便捷函数"""
        def test_callback():
            pass
        
        with patch.object(config_manager, 'register_reload_callback') as mock_register:
            register_reload_callback(test_callback)
            mock_register.assert_called_once_with(test_callback)
    
    def test_update_config_function(self):
        """测试update_config便捷函数"""
        updates = {"system": {"debug": True}}
        
        with patch.object(config_manager, 'update_config') as mock_update:
            mock_update.return_value = True
            result = update_config(updates)
            
            mock_update.assert_called_once_with(updates)
            assert result is True
    
    def test_start_config_watcher_function(self):
        """测试start_config_watcher便捷函数"""
        with patch.object(config_manager, 'start_config_watcher') as mock_start:
            start_config_watcher("config.json")
            mock_start.assert_called_once_with("config.json")
    
    def test_stop_config_watcher_function(self):
        """测试stop_config_watcher便捷函数"""
        with patch.object(config_manager, 'stop_config_watcher') as mock_stop:
            stop_config_watcher()
            mock_stop.assert_called_once()
    
    def test_get_config_snapshot_function(self):
        """测试get_config_snapshot便捷函数"""
        with patch.object(config_manager, 'get_config_snapshot') as mock_get:
            expected_snapshot = {"system": {"version": "4.0.1"}}
            mock_get.return_value = expected_snapshot
            
            snapshot = get_config_snapshot()
            
            mock_get.assert_called_once()
            assert snapshot == expected_snapshot
    
    def test_restore_config_snapshot_function(self):
        """测试restore_config_snapshot便捷函数"""
        snapshot = {"system": {"version": "4.0.1"}}
        
        with patch.object(config_manager, 'restore_config_snapshot') as mock_restore:
            mock_restore.return_value = True
            result = restore_config_snapshot(snapshot)
            
            mock_restore.assert_called_once_with(snapshot)
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])