#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows语音输入模块 - 基于Windows Runtime Speech APIs
参考官方文档重构，支持完整的语音识别功能
"""
import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config

logger = logging.getLogger("WindowsSpeechInput")

try:
    import winrt.windows.media.speechrecognition as speechrecognition
    import winrt.windows.foundation as foundation
    import winrt.windows.globalization as globalization
    import winrt.windows.media.capture as mediacapture
    import winrt.windows.media.capture.mediaproperties as mediaproperties
    import winrt.windows.system as system
    # 正确导入TimeSpan
    from winrt.windows.foundation import TimeSpan
    WINDOWS_SPEECH_AVAILABLE = True
except ImportError:
    logger.warning("Windows Speech Runtime不可用，请确保在Windows 10/11环境下运行")
    WINDOWS_SPEECH_AVAILABLE = False

class AudioCapturePermissions:
    """音频捕获权限检查类 - 参考官方文档实现"""
    
    # 如果没有麦克风设备，会抛出此HResult值的异常
    NO_CAPTURE_DEVICES_HRESULT = -1072845856
    
    @staticmethod
    async def request_microphone_permission():
        """请求麦克风权限 - 参考官方文档实现"""
        try:
            # 请求访问音频捕获设备
            settings = mediacapture.MediaCaptureInitializationSettings()
            settings.streaming_capture_mode = mediacapture.StreamingCaptureMode.AUDIO
            settings.media_category = mediacapture.MediaCategory.SPEECH
            capture = mediacapture.MediaCapture()
            
            await capture.initialize_async(settings)
            return True
            
        except Exception as exception:
            # 当没有麦克风设备时抛出异常
            if hasattr(exception, 'hresult') and exception.hresult == AudioCapturePermissions.NO_CAPTURE_DEVICES_HRESULT:
                logger.error("系统上没有音频捕获设备")
                return False
            else:
                # 权限被拒绝或其他错误
                logger.error(f"麦克风权限检查失败: {exception}")
                return False

class WindowsSpeechInput:
    """Windows语音输入类 - 基于Windows Runtime Speech APIs重构版本"""
    
    def __init__(self):
        self.speech_recognizer = None
        self.is_listening = False
        self.is_initialized = False
        self.on_text_callback = None
        self.on_error_callback = None
        self.on_status_callback = None
        
        # 语音识别配置
        self.recognition_config = {
            "language": "zh-CN",  # 默认中文
            "continuous": True,  # 连续识别
            "timeout": 30,  # 超时时间（秒）
            "confidence_threshold": 0.7,  # 置信度阈值
            "auto_stop_silence_timeout": 3,  # 自动停止静音超时
            "use_ui": True  # 是否使用默认UI
        }
        
        # 约束配置
        self.constraints = {
            "dictation": True,  # 听写约束
            "web_search": False,  # 网络搜索约束
            "list_constraints": [],  # 列表约束
            "grammar_file": None  # SRGS语法文件
        }
        
        # UI选项配置
        self.ui_options = {
            "audible_prompt": "请说话...",  # 音频提示
            "example_text": "例如：'今天天气怎么样'",  # 示例文本
            "is_readback_enabled": True,  # 是否启用回读
            "show_confirmation": True  # 是否显示确认
        }
        
        if WINDOWS_SPEECH_AVAILABLE:
            self._init_speech_recognizer()
        else:
            logger.error("Windows Speech Runtime不可用")
    
    async def _check_permissions(self):
        """检查麦克风权限"""
        try:
            has_permission = await AudioCapturePermissions.request_microphone_permission()
            if not has_permission:
                logger.error("麦克风权限检查失败")
                return False
            return True
        except Exception as e:
            logger.error(f"权限检查异常: {e}")
            return False
    
    async def _init_speech_recognizer_async(self):
        """异步初始化语音识别器"""
        try:
            # 创建语言对象
            language = globalization.Language(self.recognition_config["language"])
            
            # 创建语音识别器
            self.speech_recognizer = speechrecognition.SpeechRecognizer(language)
            
            # 编译约束（必须调用）
            await self.speech_recognizer.compile_constraints_async()
            
            # 设置连续识别会话
            session = self.speech_recognizer.continuous_recognition_session
            
            # 设置超时时间（使用TimeSpan）
            timeout_ts = TimeSpan()
            timeout_ts.duration = self.recognition_config["auto_stop_silence_timeout"] * 10_000_000  # 转换为100纳秒单位
            session.auto_stop_silence_timeout = timeout_ts
            
            # 绑定事件处理器（使用正确的事件名和方法）
            self.result_token = session.add_result_generated(self._on_result_received)
            self.completed_token = session.add_completed(self._on_recognition_completed)
            
            # 设置UI选项
            self._setup_ui_options()
            
            # 添加约束
            self._setup_constraints()
            
            self.is_initialized = True
            logger.info("Windows语音识别器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化语音识别器失败: {e}")
            self.is_initialized = False
    
    def _init_speech_recognizer(self):
        """同步初始化语音识别器（包装异步方法）"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._init_speech_recognizer_async())
            loop.close()
        except Exception as e:
            logger.error(f"同步初始化语音识别器失败: {e}")
            self.is_initialized = False
    
    def _setup_ui_options(self):
        """设置UI选项"""
        try:
            ui_options = self.speech_recognizer.ui_options
            ui_options.audible_prompt = self.ui_options["audible_prompt"]
            ui_options.example_text = self.ui_options["example_text"]
            ui_options.is_readback_enabled = self.ui_options["is_readback_enabled"]
            ui_options.show_confirmation = self.ui_options["show_confirmation"]
            logger.debug("UI选项设置完成")
        except Exception as e:
            logger.warning(f"设置UI选项失败: {e}")
    
    async def _setup_constraints_async(self):
        """异步设置识别约束"""
        try:
            # 清空现有约束
            self.speech_recognizer.constraints.clear()
            
            # 添加听写约束（默认）
            if self.constraints["dictation"]:
                # 听写约束是默认的，不需要显式添加
                logger.debug("启用听写约束")
            
            # 添加网络搜索约束
            if self.constraints["web_search"]:
                web_search_constraint = speechrecognition.SpeechRecognitionTopicConstraint(
                    speechrecognition.SpeechRecognitionScenario.WEB_SEARCH, 
                    "webSearch"
                )
                self.speech_recognizer.constraints.append(web_search_constraint)
                logger.debug("添加网络搜索约束")
            
            # 添加列表约束
            for constraint_name, word_list in self.constraints["list_constraints"]:
                list_constraint = speechrecognition.SpeechRecognitionListConstraint(
                    word_list, constraint_name
                )
                self.speech_recognizer.constraints.append(list_constraint)
                logger.debug(f"添加列表约束: {constraint_name}")
            
            # 编译约束
            await self.speech_recognizer.compile_constraints_async()
            
        except Exception as e:
            logger.error(f"设置约束失败: {e}")
    
    def _setup_constraints(self):
        """同步设置识别约束（包装异步方法）"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._setup_constraints_async())
            loop.close()
        except Exception as e:
            logger.error(f"同步设置约束失败: {e}")
    
    async def _compile_constraints(self):
        """编译约束"""
        try:
            await self.speech_recognizer.compile_constraints_async()
            logger.debug("约束编译成功")
        except Exception as e:
            logger.error(f"约束编译失败: {e}")
    
    def _on_result_received(self, sender, args):
        """处理语音识别结果"""
        try:
            result = args.result
            
            # 检查置信度
            if result.confidence >= self.recognition_config["confidence_threshold"]:
                recognized_text = result.text
                logger.info(f"识别到文本: {recognized_text} (置信度: {result.confidence})")
                
                # 调用文本回调
                if self.on_text_callback:
                    threading.Thread(
                        target=self.on_text_callback,
                        args=(recognized_text,),
                        daemon=True
                    ).start()
                
                # 通知状态变化
                self._notify_status_change("text_received", {"text": recognized_text, "confidence": result.confidence})
            else:
                logger.debug(f"识别置信度过低: {result.confidence}")
                
        except Exception as e:
            logger.error(f"处理识别结果时出错: {e}")
    
    def _on_recognition_completed(self, sender, args):
        """处理识别完成事件"""
        try:
            if args.status != speechrecognition.SpeechRecognitionResultStatus.SUCCESS:
                error_msg = f"语音识别失败: {args.status}"
                logger.warning(error_msg)
                
                # 调用错误回调
                if self.on_error_callback:
                    threading.Thread(
                        target=self.on_error_callback,
                        args=(error_msg,),
                        daemon=True
                    ).start()
                
                # 通知状态变化
                self._notify_status_change("error", {"error": error_msg})
            else:
                logger.debug("语音识别会话完成")
                self._notify_status_change("completed", {})
                    
        except Exception as e:
            logger.error(f"处理识别完成事件时出错: {e}")
    
    def _notify_status_change(self, event_type: str, data: Dict[str, Any]):
        """通知状态变化"""
        if self.on_status_callback:
            status_data = {
                "event_type": event_type,
                "timestamp": time.time(),
                "data": data
            }
            threading.Thread(
                target=self.on_status_callback,
                args=(status_data,),
                daemon=True
            ).start()
    
    async def start_listening_async(self, on_text: Callable[[str], None] = None, 
                                   on_error: Callable[[str], None] = None,
                                   on_status: Callable[[Dict[str, Any]], None] = None):
        """异步开始语音监听"""
        if not self.is_initialized:
            logger.error("语音识别器未初始化")
            return False
        
        if self.is_listening:
            logger.warning("已经在监听中")
            return True
        
        # 检查权限
        if not await self._check_permissions():
            return False
        
        try:
            # 设置回调函数
            if on_text:
                self.on_text_callback = on_text
            if on_error:
                self.on_error_callback = on_error
            if on_status:
                self.on_status_callback = on_status
            
            # 开始连续识别
            await self.speech_recognizer.continuous_recognition_session.start_async()
            self.is_listening = True
            
            logger.info("开始语音监听")
            self._notify_status_change("started", {})
            return True
            
        except Exception as e:
            logger.error(f"开始语音监听失败: {e}")
            return False
    
    def start_listening(self, on_text: Callable[[str], None] = None, 
                       on_error: Callable[[str], None] = None,
                       on_status: Callable[[Dict[str, Any]], None] = None):
        """开始语音监听（同步包装）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.start_listening_async(on_text, on_error, on_status)
            )
        finally:
            loop.close()
    
    async def stop_listening_async(self):
        """异步停止语音监听"""
        if not self.is_listening:
            return
        
        try:
            await self.speech_recognizer.continuous_recognition_session.stop_async()
            
            # 移除事件绑定
            if hasattr(self, 'result_token') and self.result_token:
                self.speech_recognizer.continuous_recognition_session.remove_result_generated(self.result_token)
            if hasattr(self, 'completed_token') and self.completed_token:
                self.speech_recognizer.continuous_recognition_session.remove_completed(self.completed_token)
            
            self.is_listening = False
            logger.info("停止语音监听")
            self._notify_status_change("stopped", {})
            
        except Exception as e:
            logger.error(f"停止语音监听失败: {e}")
    
    def stop_listening(self):
        """停止语音监听（同步包装）"""
        if not self.is_listening:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.stop_listening_async())
        finally:
            loop.close()
    
    async def recognize_with_ui_async(self, on_text: Callable[[str], None] = None,
                                     on_error: Callable[[str], None] = None):
        """使用默认UI进行单次识别"""
        if not self.is_initialized:
            logger.error("语音识别器未初始化")
            return None
        
        # 检查权限
        if not await self._check_permissions():
            return None
        
        try:
            # 编译约束
            await self._compile_constraints()
            
            # 使用默认UI进行识别
            result = await self.speech_recognizer.recognize_with_ui_async()
            
            if result.confidence >= self.recognition_config["confidence_threshold"]:
                recognized_text = result.text
                logger.info(f"UI识别结果: {recognized_text}")
                
                if on_text:
                    on_text(recognized_text)
                
                return recognized_text
            else:
                error_msg = "识别置信度过低"
                logger.warning(error_msg)
                if on_error:
                    on_error(error_msg)
                return None
                
        except Exception as e:
            error_msg = f"UI识别失败: {e}"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
    
    def recognize_with_ui(self, on_text: Callable[[str], None] = None,
                         on_error: Callable[[str], None] = None):
        """使用默认UI进行单次识别（同步包装）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.recognize_with_ui_async(on_text, on_error)
            )
        finally:
            loop.close()
    
    def set_language(self, language_code: str):
        """设置识别语言"""
        try:
            # 重新初始化识别器
            if self.is_listening:
                self.stop_listening()
            
            self.recognition_config["language"] = language_code
            self._init_speech_recognizer()
            
            logger.info(f"设置识别语言为: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"设置语言失败: {e}")
            return False
    
    def add_list_constraint(self, constraint_name: str, word_list: List[str]):
        """添加列表约束"""
        try:
            self.constraints["list_constraints"].append((constraint_name, word_list))
            
            # 如果已初始化，重新设置约束
            if self.is_initialized:
                self._setup_constraints()
            
            logger.info(f"添加列表约束: {constraint_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加列表约束失败: {e}")
            return False
    
    def set_web_search_enabled(self, enabled: bool):
        """设置网络搜索约束"""
        try:
            self.constraints["web_search"] = enabled
            
            # 如果已初始化，重新设置约束
            if self.is_initialized:
                self._setup_constraints()
            
            logger.info(f"网络搜索约束: {'启用' if enabled else '禁用'}")
            return True
            
        except Exception as e:
            logger.error(f"设置网络搜索约束失败: {e}")
            return False
    
    def set_ui_options(self, options: Dict[str, Any]):
        """设置UI选项"""
        try:
            self.ui_options.update(options)
            
            # 如果已初始化，重新设置UI选项
            if self.is_initialized:
                self._setup_ui_options()
            
            logger.info("UI选项已更新")
            return True
            
        except Exception as e:
            logger.error(f"设置UI选项失败: {e}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        try:
            languages = speechrecognition.SpeechRecognizer.supported_topic_languages
            return [lang.language_tag for lang in languages]
        except Exception as e:
            logger.error(f"获取支持语言失败: {e}")
            return ["zh-CN", "en-US"]  # 默认返回
    
    def is_available(self) -> bool:
        """检查语音识别是否可用"""
        return WINDOWS_SPEECH_AVAILABLE and self.is_initialized
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "available": self.is_available(),
            "listening": self.is_listening,
            "initialized": self.is_initialized,
            "language": self.recognition_config["language"],
            "constraints": self.constraints.copy(),
            "ui_options": self.ui_options.copy()
        }

# 使用示例
if __name__ == "__main__":
    def on_text_received(text: str):
        print(f"收到语音输入: {text}")
    
    def on_error_received(error: str):
        print(f"语音识别错误: {error}")
    
    def on_status_changed(status: Dict[str, Any]):
        print(f"状态变化: {status}")
    
    # 创建语音输入实例
    speech_input = WindowsSpeechInput()
    
    if speech_input.is_available():
        print("语音识别可用")
        print(f"支持的语言: {speech_input.get_supported_languages()}")
        
        # 设置UI选项
        speech_input.set_ui_options({
            "audible_prompt": "请说话进行测试...",
            "example_text": "例如：'你好'、'今天天气怎么样'"
        })
        
        # 添加列表约束示例
        speech_input.add_list_constraint("commands", ["开始", "停止", "退出"])
        
        # 开始监听
        speech_input.start_listening(on_text_received, on_error_received, on_status_changed)
        
        try:
            print("正在监听语音输入，按Ctrl+C停止...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            speech_input.stop_listening()
            print("停止语音监听")
    else:
        print("语音识别不可用")
