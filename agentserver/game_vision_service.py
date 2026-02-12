#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏视觉服务：截图 -> 视觉模型识别 -> 三线输出（原图/描述/结构化）-> 可选攻略桥接。
"""

from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from system.config import config

logger = logging.getLogger(__name__)


class VisionTarget(BaseModel):
    """画面目标（弱结构化）。"""

    name: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bbox: Optional[list[int]] = None


class VisionStructured(BaseModel):
    """视觉结构化结果（可为空、可部分缺失）。"""

    game_id: Optional[str] = None
    scene: Optional[str] = None
    stage_id: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ocr_texts: list[str] = Field(default_factory=list)
    targets: list[VisionTarget] = Field(default_factory=list)


class ScreenshotAnalyzeRequest(BaseModel):
    """截图识别请求。"""

    query: str = ""
    session_id: Optional[str] = None
    include_guide: bool = True
    save_screenshot: Optional[bool] = None
    model: Optional[str] = None
    model_url: Optional[str] = None
    api_key: Optional[str] = None


class GameVisionService:
    """游戏视觉识别服务。"""

    async def capture_and_analyze(self, request: ScreenshotAnalyzeRequest) -> dict[str, Any]:
        """执行截图并分析，返回三线结果。"""
        screenshot_id = f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        image = self._capture_screen_image()
        image_path = self._resolve_screenshot_path(screenshot_id)

        should_save = (
            config.computer_control.save_screenshot if request.save_screenshot is None else request.save_screenshot
        )
        if should_save:
            self._save_image(image, image_path)
        else:
            # 用户关闭保存时也落地到临时目录，保证可复盘与后续桥接一致
            self._save_image(image, image_path)

        caption = ""
        structured_dict: dict[str, Any] = {}
        parse_ok = False
        raw_text = ""

        if config.computer_control.enable_caption or config.computer_control.enable_structured:
            raw_text = await self._call_vision_model(image_path, request)
            parsed = self._extract_json_object(raw_text)
            if parsed:
                caption = str(parsed.get("caption", "")).strip()
                raw_structured = parsed.get("structured", {})
                if isinstance(raw_structured, dict):
                    try:
                        structured_obj = VisionStructured.model_validate(raw_structured)
                        structured_dict = structured_obj.model_dump()
                        parse_ok = True
                    except Exception as exc:
                        logger.warning(f"结构化结果解析失败: {exc}")

            if not caption:
                caption = raw_text.strip()

        guide_result = await self._call_guide_service(
            request=request,
            image_path=image_path,
            caption=caption,
            structured=structured_dict,
        )

        return {
            "screenshot_id": screenshot_id,
            "screenshot_path": str(image_path),
            "timestamp": datetime.now().isoformat(),
            "image": {
                "path": str(image_path),
                "width": int(image.width),
                "height": int(image.height),
            },
            "caption": caption,
            "structured": structured_dict,
            "parse_ok": parse_ok,
            "raw_model_text": raw_text,
            "guide": guide_result,
        }

    def _resolve_screenshot_dir(self) -> Path:
        raw_dir = (config.computer_control.screenshot_dir or "logs/game_screenshots").strip()
        screenshot_dir = Path(raw_dir)
        if not screenshot_dir.is_absolute():
            screenshot_dir = Path(config.system.base_dir) / screenshot_dir
        dated_dir = screenshot_dir / datetime.now().strftime("%Y-%m-%d")
        dated_dir.mkdir(parents=True, exist_ok=True)
        return dated_dir

    def _resolve_screenshot_path(self, screenshot_id: str) -> Path:
        screenshot_dir = self._resolve_screenshot_dir()
        image_format = (config.computer_control.screenshot_format or "png").strip().lower()
        if image_format not in {"png", "jpg", "jpeg", "webp"}:
            image_format = "png"
        suffix = ".jpg" if image_format == "jpeg" else f".{image_format}"
        return screenshot_dir / f"{screenshot_id}{suffix}"

    def _capture_screen_image(self) -> Any:
        """截图，优先 Pillow.ImageGrab，失败则尝试 pyautogui。"""
        try:
            from PIL import ImageGrab

            image = ImageGrab.grab(all_screens=True)
            if image is None:
                raise RuntimeError("ImageGrab返回空图像")
            return image.convert("RGB")
        except Exception as first_error:
            try:
                import pyautogui

                image = pyautogui.screenshot()
                return image.convert("RGB")
            except Exception as second_error:
                raise RuntimeError(f"截图失败: {first_error}; fallback失败: {second_error}")

    def _save_image(self, image: Any, image_path: Path) -> None:
        image_format = image_path.suffix.lower().replace(".", "")
        if image_format == "jpg":
            image_format = "jpeg"
        if image_format == "jpeg":
            image.save(image_path, format="JPEG", quality=int(config.computer_control.screenshot_quality))
        elif image_format == "webp":
            image.save(image_path, format="WEBP", quality=int(config.computer_control.screenshot_quality))
        else:
            image.save(image_path, format="PNG")

    async def _call_vision_model(self, image_path: Path, request: ScreenshotAnalyzeRequest) -> str:
        model_name = (request.model or config.computer_control.model or config.api.model).strip()
        model_url = (request.model_url or config.computer_control.model_url or config.api.base_url).strip()
        api_key = (request.api_key or config.computer_control.api_key or config.api.api_key).strip()
        timeout = int(config.computer_control.vision_timeout)

        if not model_name:
            raise RuntimeError("视觉模型未配置")
        if not model_url:
            raise RuntimeError("视觉模型URL未配置")
        if not api_key:
            raise RuntimeError("视觉模型API Key未配置")

        data_url = self._build_data_url(image_path)

        system_prompt = (
            "你是游戏画面分析器。请仅输出一个JSON对象，不要输出Markdown。"
            "JSON格式必须是:"
            '{"caption":"...","structured":{"game_id":null,"scene":null,"stage_id":null,'
            '"confidence":0.0,"ocr_texts":[],"targets":[{"name":"","confidence":0.0,"bbox":[0,0,0,0]}]}}。'
            "无法判断时用null/空数组，confidence取0~1。"
        )
        user_prompt = request.query.strip() or "请识别当前游戏画面并返回描述和结构化结果。"

        client = AsyncOpenAI(api_key=api_key, base_url=model_url, timeout=timeout)
        try:
            response = await client.chat.completions.create(
                model=model_name,
                temperature=0.1,
                max_tokens=1200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
            )

            content = response.choices[0].message.content if response.choices else ""
            return self._stringify_content(content)
        except Exception as first_exc:
            logger.warning(f"chat.completions 视觉调用失败，尝试 responses API: {first_exc}")
            response = await client.responses.create(
                model=model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": f"{system_prompt}\n\n{user_prompt}"},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                max_output_tokens=1200,
            )
            output_text = getattr(response, "output_text", "")
            return str(output_text or "")

    @staticmethod
    def _stringify_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                else:
                    text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
            return "\n".join(parts)
        return str(content or "")

    @staticmethod
    def _build_data_url(image_path: Path) -> str:
        image_bytes = image_path.read_bytes()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        suffix = image_path.suffix.lower().replace(".", "")
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
        if not mime:
            mime = "png"
        return f"data:image/{mime};base64,{encoded}"

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned)
            cleaned = cleaned.replace("```", "").strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None

        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
        return None

    async def _call_guide_service(
        self,
        request: ScreenshotAnalyzeRequest,
        image_path: Path,
        caption: str,
        structured: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        endpoint = (config.computer_control.guide_endpoint or "").strip()
        if not request.include_guide or not endpoint:
            return None

        payload: dict[str, Any] = {
            "query": request.query,
            "session_id": request.session_id,
            "screenshot_path": str(image_path),
            "caption": caption,
        }
        if config.computer_control.guide_use_structured:
            payload["structured"] = structured

        headers = {"Content-Type": "application/json"}
        api_key = (config.computer_control.guide_api_key or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        timeout = float(config.computer_control.guide_timeout)

        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code >= 400:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            return {
                "success": True,
                "status_code": resp.status_code,
                "data": data,
            }
        except Exception as exc:
            logger.warning(f"调用攻略服务失败: {exc}")
            return {
                "success": False,
                "status_code": 0,
                "error": str(exc),
            }
