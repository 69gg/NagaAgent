import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from apiserver import naga_auth
from apiserver.agentic_tool_loop import format_tool_result_for_display
from apiserver.routes import openai_proxy
from apiserver.routes.tools import _build_tool_result_blocks
from system import config as system_config


class _ApiSettings:
    def __init__(self, use_gateway: bool) -> None:
        self.use_gateway = use_gateway


class _Settings:
    def __init__(self, use_gateway: bool) -> None:
        self.api = _ApiSettings(use_gateway)


class ConfigAndToolTests(unittest.TestCase):
    def test_bootstrap_config_from_project_example(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            runtime_config = tmp_path / "runtime" / "config.json"
            example_config = tmp_path / "project" / "config.json.example"
            example_config.parent.mkdir(parents=True)
            example_config.write_text('{"api": {"model": "demo-model"}}', encoding="utf-8")

            with (
                patch.object(system_config, "IS_PACKAGED", False),
                patch.object(
                    system_config,
                    "_get_project_config_template_paths",
                    lambda _path: [runtime_config.with_name("config.json.example"), example_config],
                ),
            ):
                system_config.bootstrap_config_from_example(str(runtime_config))

            self.assertTrue(runtime_config.exists())
            loaded = json.loads(runtime_config.read_text(encoding="utf-8"))
            self.assertEqual(loaded["api"]["model"], "demo-model")

    def test_should_use_model_gateway_respects_config(self) -> None:
        with (
            patch.object(naga_auth, "is_authenticated", lambda: True),
            patch("system.config.get_config", lambda: _Settings(use_gateway=False)),
        ):
            self.assertFalse(naga_auth.should_use_model_gateway())

        with (
            patch.object(naga_auth, "is_authenticated", lambda: True),
            patch("system.config.get_config", lambda: _Settings(use_gateway=True)),
        ):
            self.assertTrue(naga_auth.should_use_model_gateway())

    def test_format_tool_result_for_display_unwraps_common_json_payload(self) -> None:
        raw = json.dumps(
            {
                "status": "success",
                "message": "ok",
                "data": {"items": [{"title": "结果", "url": "https://example.test"}]},
            },
            ensure_ascii=False,
        )

        self.assertEqual(
            format_tool_result_for_display(raw),
            {"items": [{"title": "结果", "url": "https://example.test"}]},
        )

    def test_build_tool_result_blocks_for_mcp_callback(self) -> None:
        blocks = _build_tool_result_blocks(
            [
                {
                    "service_name": "weather",
                    "tool_name": "today",
                    "status": "ok",
                    "result": {"city": "上海", "temperature": 26},
                }
            ]
        )

        self.assertIn("```tool-result", blocks)
        self.assertIn("✅ weather: today", blocks)
        self.assertIn('"city": "上海"', blocks)

    def test_openai_proxy_uses_local_api_when_gateway_disabled(self) -> None:
        class _ProxyApiSettings:
            base_url = "https://local.example/v1"
            api_key = "sk-local"

        class _ProxySettings:
            api = _ProxyApiSettings()

        with (
            patch.object(naga_auth, "should_use_model_gateway", lambda: False),
            patch("system.config.config", _ProxySettings()),
        ):
            self.assertEqual(
                openai_proxy._get_upstream_url(),
                "https://local.example/v1/chat/completions",
            )


if __name__ == "__main__":
    unittest.main()
