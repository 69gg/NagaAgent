"""
全局测试配置和夹具定义

为NagaAgent项目提供统一的测试基础设施，包括：
- 临时文件系统管理
- Mock对象配置
- 异步测试支持
- 测试数据工厂
- 模块特定的夹具
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from freezegun import freeze_time

# ============================================================================
# 全局测试配置
# ============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """pytest配置钩子"""
    # 添加自定义标记说明
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试（需要外部服务或数据库）"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试（测试完整业务流程）"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试（执行时间较长）"
    )
    config.addinivalue_line(
        "markers", "gui: GUI测试（需要图形界面）"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    """测试收集后修改项目"""
    # 默认跳过标记为gui的测试（除非明确指定运行）
    if not config.getoption("--run-gui"):
        skip_gui = pytest.mark.skip(reason="需要 --run-gui 选项来运行GUI测试")
        for item in items:
            if "gui" in item.keywords:
                item.add_marker(skip_gui)


# ============================================================================
# 全局夹具
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """为异步测试提供事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录夹具"""
    temp_dir = tempfile.mkdtemp(prefix="nagaagent_test_")
    temp_path = Path(temp_dir)
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_time() -> Generator[None, None, None]:
    """冻结时间夹具"""
    with freeze_time("2024-01-15 10:30:00"):
        yield


# ============================================================================
# Mock夹具
# ============================================================================

@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """模拟LLM响应"""
    return {
        "choices": [
            {
                "message": {
                    "content": "这是一个模拟的LLM响应",
                    "role": "assistant"
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_service() -> Generator[Mock, None, None]:
    """模拟LLM服务"""
    with patch("nagaagent.core.llm_adapter.LLMAdapter") as mock:
        mock_instance = Mock()
        mock_instance.generate_response = AsyncMock(
            return_value="模拟LLM响应"
        )
        mock_instance.generate_streaming_response = AsyncMock(
            return_value=["流式", "响应", "块"]
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_mqtt_client() -> Generator[Mock, None, None]:
    """模拟MQTT客户端"""
    with patch("paho.mqtt.client.Client") as mock:
        mock_instance = Mock()
        mock_instance.connect = Mock(return_value=0)
        mock_instance.disconnect = Mock()
        mock_instance.publish = Mock(return_value=(0, 0))
        mock_instance.subscribe = Mock(return_value=(0, 0))
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_audio_device() -> Generator[Mock, None, None]:
    """模拟音频设备"""
    with patch("sounddevice.OutputStream") as mock:
        mock_instance = Mock()
        mock_instance.start = Mock()
        mock_instance.stop = Mock()
        mock_instance.write = Mock()
        mock.return_value = mock_instance
        yield mock_instance


# ============================================================================
# 模块特定的夹具
# ============================================================================

# agentserver模块夹具
@pytest.fixture
def mock_agent_manager() -> Mock:
    """模拟Agent管理器"""
    manager = Mock()
    manager.get_agent = Mock(return_value=Mock())
    manager.list_agents = Mock(return_value=["agent1", "agent2"])
    manager.start_agent = AsyncMock(return_value=True)
    manager.stop_agent = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_task_scheduler() -> Mock:
    """模拟任务调度器"""
    scheduler = Mock()
    scheduler.schedule_task = AsyncMock(return_value="task_123")
    scheduler.cancel_task = AsyncMock(return_value=True)
    scheduler.get_task_status = AsyncMock(return_value="completed")
    return scheduler


# apiserver模块夹具
@pytest.fixture
def test_client() -> Any:
    """FastAPI测试客户端（需要时动态导入）"""
    # 延迟导入以避免不必要的依赖
    from fastapi.testclient import TestClient
    from apiserver.api_server import app
    return TestClient(app)


@pytest.fixture
def mock_fastapi_request() -> Mock:
    """模拟FastAPI请求"""
    request = Mock()
    request.headers = {"Authorization": "Bearer test_token"}
    request.query_params = {}
    request.path_params = {}
    return request


# game模块夹具
@pytest.fixture
def mock_game_config() -> Dict[str, Any]:
    """模拟游戏配置"""
    return {
        "llm_provider": "mock",
        "max_agents": 5,
        "timeout_seconds": 30,
        "debug_mode": True
    }


@pytest.fixture
def mock_task_data() -> Dict[str, Any]:
    """模拟任务数据"""
    return {
        "task_id": "test_task_001",
        "description": "测试任务描述",
        "domain": "测试领域",
        "requirements": ["需求1", "需求2"],
        "constraints": ["约束1", "约束2"]
    }


# summer_memory模块夹具
@pytest.fixture
def mock_knowledge_graph() -> Mock:
    """模拟知识图谱"""
    graph = Mock()
    graph.add_entity = Mock(return_value=True)
    graph.query = Mock(return_value=[{"entity": "test", "relation": "has", "target": "value"}])
    graph.save = Mock()
    graph.load = Mock()
    return graph


@pytest.fixture
def mock_embedding_model() -> Mock:
    """模拟嵌入模型"""
    model = Mock()
    model.embed = Mock(return_value=[0.1, 0.2, 0.3])
    model.embed_batch = Mock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    return model


# ============================================================================
# 测试数据工厂
# ============================================================================

@pytest.fixture
def sample_agent_data() -> Dict[str, Any]:
    """示例Agent数据"""
    return {
        "agent_id": "test_agent_001",
        "name": "测试Agent",
        "description": "用于测试的Agent",
        "capabilities": ["capability1", "capability2"],
        "status": "idle"
    }


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """示例任务数据"""
    return {
        "task_id": "test_task_001",
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": "medium",
        "deadline": "2024-01-20T10:00:00",
        "assignee": "test_agent_001"
    }


@pytest.fixture
def sample_message_data() -> Dict[str, Any]:
    """示例消息数据"""
    return {
        "message_id": "msg_001",
        "content": "测试消息内容",
        "sender": "user_001",
        "receiver": "agent_001",
        "timestamp": "2024-01-15T10:30:00",
        "metadata": {"type": "text", "format": "plain"}
    }


# ============================================================================
# 测试工具函数
# ============================================================================

def assert_async_call(mock_obj: Mock, method_name: str, *args, **kwargs) -> None:
    """断言异步方法被调用"""
    method = getattr(mock_obj, method_name)
    method.assert_called_once_with(*args, **kwargs)


def create_temp_file(temp_dir: Path, content: str = "", suffix: str = ".txt") -> Path:
    """创建临时文件"""
    import tempfile
    with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=suffix, delete=False, mode="w") as f:
        f.write(content)
        return Path(f.name)


async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """等待条件成立"""
    import asyncio
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)
    return False


# ============================================================================
# 测试配置覆盖
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """自动设置测试环境"""
    # 设置测试模式
    monkeypatch.setenv("NAGAAGENT_TEST_MODE", "true")
    monkeypatch.setenv("NAGAAGENT_LLM_PROVIDER", "mock")
    
    # 禁用实际的外部API调用
    monkeypatch.setattr("requests.post", Mock())
    monkeypatch.setattr("httpx.AsyncClient.post", AsyncMock())
    
    # 禁用实际的GUI操作
    monkeypatch.setattr("pyautogui.click", Mock())
    monkeypatch.setattr("pyautogui.typewrite", Mock())
    
    # 禁用实际的音频播放
    monkeypatch.setattr("sounddevice.play", Mock())
    monkeypatch.setattr("simpleaudio.play_buffer", Mock())
    
    # 禁用实际的MQTT连接
    monkeypatch.setattr("paho.mqtt.client.Client.connect", Mock(return_value=0))