#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音输入功能使用示例
演示重构后的Windows Speech API语音识别功能
"""
import time
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def basic_usage_example():
    """基本使用示例"""
    print("🎤 基本使用示例")
    print("=" * 40)
    
    from speech_input import get_speech_input_manager
    
    # 获取语音输入管理器
    manager = get_speech_input_manager()
    
    if not manager.is_available():
        print("❌ 语音输入不可用")
        return
    
    print("✅ 语音输入可用")
    
    # 定义回调函数
    def on_text_received(text: str):
        print(f"🎤 识别到: {text}")
    
    def on_error_received(error: str):
        print(f"❌ 错误: {error}")
    
    def on_status_changed(status: dict):
        print(f"📊 状态: {status['event_type']}")
    
    # 开始监听
    print("🎤 开始语音监听...")
    if manager.start_listening(on_text_received, on_error_received, on_status_changed):
        print("✅ 监听已启动，请说话测试（5秒后自动停止）")
        time.sleep(5)
        manager.stop_listening()
        print("✅ 监听已停止")
    else:
        print("❌ 启动监听失败")

def advanced_usage_example():
    """高级功能示例"""
    print("\n🎤 高级功能示例")
    print("=" * 40)
    
    from speech_input import get_speech_input_manager
    
    manager = get_speech_input_manager()
    
    if not manager.is_available():
        print("❌ 语音输入不可用")
        return
    
    # 设置UI选项
    print("🔧 设置UI选项...")
    manager.set_ui_options({
        "audible_prompt": "请说出您的命令...",
        "example_text": "例如：'开始录音'、'停止录音'、'退出程序'"
    })
    
    # 添加列表约束
    print("🔧 添加命令约束...")
    manager.add_list_constraint("commands", [
        "开始录音", "停止录音", "退出程序", "帮助", "状态"
    ])
    
    # 启用网络搜索
    print("🔧 启用网络搜索...")
    manager.set_web_search_enabled(True)
    
    # 设置语言
    print("🔧 设置识别语言...")
    manager.set_language("zh-CN")
    
    print("✅ 高级配置完成")

def ui_recognition_example():
    """UI识别示例"""
    print("\n🎤 UI识别示例")
    print("=" * 40)
    
    from speech_input import recognize_with_ui
    
    print("🎤 启动UI识别，将弹出Windows语音识别界面...")
    print("请说话进行测试")
    
    def on_text_received(text: str):
        print(f"🎤 UI识别结果: {text}")
    
    def on_error_received(error: str):
        print(f"❌ UI识别错误: {error}")
    
    # 使用UI进行识别
    result = recognize_with_ui(on_text_received, on_error_received)
    
    if result:
        print(f"✅ 最终结果: {result}")
    else:
        print("❌ 无识别结果")

def configuration_example():
    """配置管理示例"""
    print("\n🎤 配置管理示例")
    print("=" * 40)
    
    from speech_input import get_speech_input_manager
    
    manager = get_speech_input_manager()
    
    # 获取当前配置
    print("📋 当前配置:")
    config = manager.get_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # 获取支持的语言
    languages = manager.get_supported_languages()
    print(f"🌍 支持的语言: {languages}")
    
    # 获取状态
    status = manager.get_status()
    print(f"📊 当前状态: {status['listening']}")

def main():
    """主函数"""
    print("🎤 语音输入功能使用示例")
    print("=" * 50)
    
    # 示例1: 基本使用
    basic_usage_example()
    
    # 示例2: 高级功能
    advanced_usage_example()
    
    # 示例3: 配置管理
    configuration_example()
    
    # 示例4: UI识别（可选）
    print("\n🔍 是否测试UI识别功能？(y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            ui_recognition_example()
    except KeyboardInterrupt:
        print("\n⏹️ 跳过UI识别测试")
    
    print("\n" + "=" * 50)
    print("🎉 示例演示完成！")
    print("\n💡 提示:")
    print("- 确保麦克风权限已开启")
    print("- 确保Windows语音识别已启用")
    print("- 在安静环境中测试效果更佳")

if __name__ == "__main__":
    main()
