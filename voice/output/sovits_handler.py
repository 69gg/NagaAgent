# -*- coding: utf-8 -*-
"""
GPT-SoVITS HTTP API 适配器
"""

import requests
import tempfile
import logging
from system.config import config

logger = logging.getLogger(__name__)


def generate_speech_sovits(text: str) -> str:
    """
    使用 SoVITS API 生成音频

    Args:
        text: 待合成文本

    Returns:
        音频文件路径（临时文件）

    Raises:
        Exception: API 调用失败
    """
    sovits_config = config.tts.sovits

    # 构建请求参数
    payload = {
        "text": text,
        "text_lang": sovits_config.language,
        "ref_audio_path": sovits_config.reference_audio,
        "prompt_text": sovits_config.reference_text,
        "prompt_lang": sovits_config.language,
        "media_type": "wav",
        "streaming_mode": False,
    }

    logger.info(f"[SoVITS] 请求音频: text='{text[:50]}...'")

    try:
        # POST 请求（先尝试根路径）
        response = requests.post(sovits_config.api_url, json=payload, timeout=sovits_config.timeout)

        if response.status_code == 200:
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file.write(response.content)
            temp_file.close()
            logger.info(f"[SoVITS] 音频生成成功: {temp_file.name}")
            return temp_file.name
        else:
            error_msg = f"SoVITS API 调用失败: {response.status_code} - {response.text}"
            logger.error(f"[SoVITS] {error_msg}")
            raise Exception(error_msg)

    except requests.exceptions.Timeout:
        error_msg = f"SoVITS API 请求超时（{sovits_config.timeout}秒）"
        logger.error(f"[SoVITS] {error_msg}")
        raise Exception(error_msg)

    except Exception as e:
        logger.error(f"[SoVITS] API 调用异常: {e}")
        raise Exception(f"SoVITS API 调用异常: {e}")
