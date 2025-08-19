#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音输入功能测试脚本
测试重构后的Windows Speech API语音识别功能
"""
import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_windows_speech_import():
    """测试Windows Speech API导入"""
    print("🔍 测试Windows Speech API导入...")
    
    try:
        import winrt.windows.media.speechrecognition as speechrecognition
        import winrt.windows.foundation as foundation
        import winrt.windows.globalization as globalization
        import winrt.windows.media.capture as mediacapture
        print("✅ Windows Speech API导入成功")
        return True
    except ImportError as e:
        print(f"❌ Windows Speech API导入失败: {e}")
        return False

def test_audio_capture_permissions():
    """测试音频捕获权限检查"""
    print("\n🔍 测试音频捕获权限检查...")
    
    try:
        from speech_input.windows_speech_input import AudioCapturePermissions
        print("✅ AudioCapturePermissions类导入成功")
        
        # 注意：这里只是测试类导入，实际权限检查需要异步调用
        print("✅ 音频捕获权限检查模块可用")
        return True
    except Exception as e:
        print(f"❌ 音频捕获权限检查测试失败: {e}")
        return False

def test_speech_input_module():
    """测试语音输入模块"""
    print("\n🔍 测试语音输入模块...")
    
    try:
        from speech_input import get_speech_input_manager, WindowsSpeechInput
        print("✅ 语音输入模块导入成功")
        
        # 测试WindowsSpeechInput类
        speech_input = WindowsSpeechInput()
        print(f"✅ WindowsSpeechInput实例创建成功")
        print(f"   可用性: {speech_input.is_available()}")
        print(f"   状态: {speech_input.get_status()}")
        
        # 测试配置功能
        print("\n🔧 测试配置功能...")
        
        # 测试UI选项设置
        ui_options = {
            "audible_prompt": "测试提示音...",
            "example_text": "测试示例文本"
        }
        success = speech_input.set_ui_options(ui_options)
        print(f"   UI选项设置: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试列表约束
        success = speech_input.add_list_constraint("test_commands", ["测试", "开始", "停止"])
        print(f"   列表约束添加: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试网络搜索约束
        success = speech_input.set_web_search_enabled(True)
        print(f"   网络搜索约束: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试语言设置
        success = speech_input.set_language("zh-CN")
        print(f"   语言设置: {'✅ 成功' if success else '❌ 失败'}")
        
        return True
    except Exception as e:
        print(f"❌ 语音输入模块测试失败: {e}")
        return False

def test_speech_recognition():
    """测试语音识别功能"""
    print("\n🔍 测试语音识别功能...")
    
    try:
        from speech_input import get_speech_input_manager
        
        # 获取语音输入管理器
        manager = get_speech_input_manager()
        print(f"✅ 语音输入管理器获取成功")
        print(f"   可用性: {manager.is_available()}")
        print(f"   状态: {manager.get_status()}")
        
        if not manager.is_available():
            print("❌ 语音输入不可用，跳过识别测试")
            return False
        
        # 测试配置功能
        print("\n🔧 测试管理器配置功能...")
        
        # 设置UI选项
        success = manager.set_ui_options({
            "audible_prompt": "请说话进行测试...",
            "example_text": "例如：'你好'、'今天天气怎么样'"
        })
        print(f"   UI选项设置: {'✅ 成功' if success else '❌ 失败'}")
        
        # 添加列表约束
        success = manager.add_list_constraint("commands", ["开始", "停止", "退出", "测试"])
        print(f"   列表约束添加: {'✅ 成功' if success else '❌ 失败'}")
        
        # 启用网络搜索
        success = manager.set_web_search_enabled(True)
        print(f"   网络搜索启用: {'✅ 成功' if success else '❌ 失败'}")
        
        # 定义回调函数
        def on_text_received(text: str):
            print(f"🎤 识别到语音: {text}")
        
        def on_error_received(error: str):
            print(f"❌ 语音识别错误: {error}")
        
        def on_status_changed(status: dict):
            print(f"📊 状态变化: {status}")
        
        # 开始语音监听
        print("\n🎤 开始语音监听测试...")
        print("   请说话进行测试，按Ctrl+C停止")
        
        if manager.start_listening(on_text_received, on_error_received, on_status_changed):
            print("✅ 语音监听启动成功")
            
            try:
                # 运行30秒进行测试
                for i in range(30):
                    time.sleep(1)
                    if i % 10 == 0:
                        print(f"⏰ 测试进行中... {30-i}秒后自动停止")
            except KeyboardInterrupt:
                print("\n⏹️ 用户中断测试")
            finally:
                manager.stop_listening()
                print("✅ 语音监听已停止")
        else:
            print("❌ 语音监听启动失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 语音识别测试失败: {e}")
        return False

def test_ui_recognition():
    """测试UI识别功能"""
    print("\n🔍 测试UI识别功能...")
    
    try:
        from speech_input import recognize_with_ui
        
        print("🎤 启动UI识别测试...")
        print("   将弹出Windows语音识别UI，请说话进行测试")
        
        def on_text_received(text: str):
            print(f"🎤 UI识别结果: {text}")
        
        def on_error_received(error: str):
            print(f"❌ UI识别错误: {error}")
        
        # 使用UI进行识别
        result = recognize_with_ui(on_text_received, on_error_received)
        
        if result:
            print(f"✅ UI识别成功: {result}")
        else:
            print("❌ UI识别失败或无结果")
        
        return True
        
    except Exception as e:
        print(f"❌ UI识别测试失败: {e}")
        return False

def test_advanced_features():
    """测试高级功能"""
    print("\n🔍 测试高级功能...")
    
    try:
        from speech_input import get_speech_input_manager
        
        manager = get_speech_input_manager()
        
        # 测试获取支持的语言
        languages = manager.get_supported_languages()
        print(f"✅ 支持的语言: {languages}")
        
        # 测试获取配置
        config = manager.get_config()
        print(f"✅ 当前配置: {config}")
        
        # 测试更新配置
        new_config = {
            "speech_config": {
                "confidence_threshold": 0.8
            },
            "ui_options_config": {
                "audible_prompt": "更新后的提示音..."
            }
        }
        manager.update_config(new_config)
        print("✅ 配置更新成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 高级功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎤 重构后语音输入功能测试开始")
    print("=" * 60)
    
    # 测试1: Windows Speech API导入
    if not test_windows_speech_import():
        print("\n❌ Windows Speech API导入失败，测试终止")
        return
    
    # 测试2: 音频捕获权限检查
    if not test_audio_capture_permissions():
        print("\n❌ 音频捕获权限检查失败，测试终止")
        return
    
    # 测试3: 语音输入模块
    if not test_speech_input_module():
        print("\n❌ 语音输入模块测试失败，测试终止")
        return
    
    # 测试4: 语音识别功能
    if not test_speech_recognition():
        print("\n❌ 语音识别功能测试失败")
        return
    
    # 测试5: UI识别功能（可选）
    print("\n🔍 是否测试UI识别功能？(y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            test_ui_recognition()
    except KeyboardInterrupt:
        print("\n⏹️ 跳过UI识别测试")
    
    # 测试6: 高级功能
    if not test_advanced_features():
        print("\n❌ 高级功能测试失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("\n📋 测试总结:")
    print("✅ Windows Speech API导入")
    print("✅ 音频捕获权限检查")
    print("✅ 语音输入模块功能")
    print("✅ 语音识别功能")
    print("✅ 高级配置功能")
    print("\n🚀 重构后的语音输入模块已准备就绪！")

if __name__ == "__main__":
    main()
