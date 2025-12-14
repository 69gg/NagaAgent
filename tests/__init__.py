"""
NagaAgent 测试套件

此包包含 NagaAgent 项目的所有测试代码。
按照模块组织，每个子目录对应一个主要功能模块。

测试结构：
tests/
├── __init__.py          # 此文件
├── conftest.py         # 全局测试夹具
├── agentserver/        # Agent服务器测试
├── apiserver/          # API服务器测试
├── game/              # 游戏系统测试
├── mcpserver/         # MCP服务器测试
├── summer_memory/     # 知识图谱记忆系统测试
├── system/            # 系统配置测试
├── mqtt_tool/         # MQTT工具测试
├── ui/                # 用户界面测试
└── voice/             # 语音功能测试

运行测试：
    uv run pytest tests/ -v

生成覆盖率报告：
    uv run pytest tests/ --cov=nagaagent --cov-report=html
"""