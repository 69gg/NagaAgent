#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音输入模块 - NagaAgent语音输入功能
基于Windows Runtime Speech APIs重构的语音识别模块
"""

from .speech_input_manager import (
    get_speech_input_manager,
    start_speech_listening,
    stop_speech_listening,
    recognize_with_ui,
    get_speech_status,
    add_list_constraint,
    set_web_search_enabled,
    set_ui_options,
    SpeechInputManager
)

from .windows_speech_input import WindowsSpeechInput, AudioCapturePermissions

__version__ = "2.0.0"
__author__ = "NagaAgent Team"

__all__ = [
    "get_speech_input_manager",
    "start_speech_listening", 
    "stop_speech_listening",
    "recognize_with_ui",
    "get_speech_status",
    "add_list_constraint",
    "set_web_search_enabled",
    "set_ui_options",
    "SpeechInputManager",
    "WindowsSpeechInput",
    "AudioCapturePermissions"
]
