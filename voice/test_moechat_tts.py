#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的流式TTS实现 - 参考MoeChat的标点符号分割算法
"""
import sys
import os
import time
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.voice_integration import get_voice_integration
from config import config

def test_moechat_tts():
    """测试新的流式TTS实现"""
    print("🧪 测试新的流式TTS实现（参考MoeChat）")
    print("=" * 50)
    
    # 检查语音功能是否启用
    if not config.system.voice_enabled:
        print("❌ 语音功能未启用，请在config.json中设置voice_enabled为true")
        return
    
    # 获取语音集成实例
    try:
        voice_integration = get_voice_integration()
        print("✅ 语音集成模块初始化成功")
    except Exception as e:
        print(f"❌ 语音集成模块初始化失败: {e}")
        return
    
    # 测试文本（模拟apiserver处理后的普通文本）
    test_texts = [
        "你好，这是一个测试。",
        "今天天气很好，适合出去散步。",
        "人工智能技术正在快速发展，为我们的生活带来了很多便利。",
        "这是一个很长的句子，用来测试音频生成和播放功能。",
        "测试普通文本的语音合成效果。"
    ]
    
    print("\n📝 开始测试流式TTS...")
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n🔤 测试 {i}: {text}")
        
        # 模拟流式文本输入
        words = text.split()
        for word in words:
            # 模拟流式输入
            voice_integration.receive_text_chunk(word + " ")
            time.sleep(0.1)  # 模拟网络延迟
        
        # 完成处理
        voice_integration.finish_processing()
        
        # 等待音频播放完成
        time.sleep(2)
        
        # 获取调试信息
        debug_info = voice_integration.get_debug_info()
        print(f"   调试信息: {debug_info}")
    
    print("\n✅ 测试完成！")
    print("\n📊 新流式TTS特性:")
    print("   • 依赖apiserver的标点符号分割算法")
    print("   • 接收处理好的普通文本")
    print("   • 简化的句子检测和音频生成")
    print("   • 内存中直接播放音频数据")
    print("   • 支持工具调用的特殊分流")
    print("   • 异步处理不阻塞前端显示")
    print("   • 完全移除旧的完整文本处理方式")

if __name__ == "__main__":
    test_moechat_tts()
