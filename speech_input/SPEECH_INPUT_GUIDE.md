# NagaAgent 语音输入功能指南 🎤

## 概述

NagaAgent现在支持多种语音输入方案，让您可以通过语音与AI助手进行交互。支持Windows 11的原生语音识别、Google Speech Recognition、Azure Speech Service等多种方案。

## 功能特性

- **多种语音识别方案**：支持Windows Speech API、Google Speech Recognition、Azure Speech Service
- **实时语音识别**：支持连续语音输入，无需手动触发
- **多语言支持**：支持中文、英文、日文、韩文等多种语言
- **智能切换**：自动选择最佳的语音识别提供者
- **统一接口**：提供简洁的API接口，易于集成
- **配置灵活**：支持自定义识别参数和语言设置

## 支持的语音识别方案

### 1. Windows Speech API (推荐)
- **优势**：Windows 11原生支持，无需额外配置
- **特点**：基于设备的语音识别，隐私保护好
- **要求**：Windows 10/11系统
- **免费**：完全免费使用

### 2. Google Speech Recognition
- **优势**：识别精度高，支持多种语言
- **特点**：基于云服务的语音识别
- **要求**：需要网络连接
- **免费**：有使用限制，需要API密钥

### 3. Azure Speech Service
- **优势**：企业级语音识别服务
- **特点**：支持高级功能（说话人识别、情感分析等）
- **要求**：需要Azure账户和API密钥
- **费用**：按使用量收费

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：
- `SpeechRecognition>=3.10.0` - 语音识别库
- `azure-cognitiveservices-speech>=1.34.0` - Azure语音服务
- `winrt>=1.0.21033.1` - Windows Runtime支持

### 2. 配置文件设置

在 `config.json` 中添加语音输入配置：

```json
{
  "speech_input": {
    "enabled": true,
    "auto_start": false,
    "language": "zh-CN",
    "confidence_threshold": 0.7,
    "timeout": 30,
    "continuous": true
  },
  "azure": {
    "speech_key": "your_azure_speech_key",
    "speech_region": "eastasia"
  }
}
```

### 3. 权限设置

#### Windows 11 语音权限
1. 打开设置 → 隐私和安全性 → 语音识别
2. 启用"语音识别"和"联机语音识别"
3. 允许应用访问麦克风

## 使用方法

### 基本使用

```python
from voice.speech_input_manager import get_speech_input_manager

# 获取语音输入管理器
manager = get_speech_input_manager()

# 定义回调函数
def on_text_received(text: str):
    print(f"收到语音输入: {text}")
    # 处理语音输入文本

def on_error_received(error: str):
    print(f"语音识别错误: {error}")

def on_status_changed(status: dict):
    print(f"状态变化: {status}")

# 开始语音监听
if manager.start_listening(on_text_received, on_error_received, on_status_changed):
    print("语音监听已启动")
else:
    print("启动语音监听失败")

# 停止语音监听
manager.stop_listening()
```

### 便捷函数使用

```python
from voice.speech_input_manager import start_speech_listening, stop_speech_listening, get_speech_status

# 开始监听
start_speech_listening(
    on_text=lambda text: print(f"语音: {text}"),
    on_error=lambda error: print(f"错误: {error}")
)

# 获取状态
status = get_speech_status()
print(f"当前状态: {status}")

# 停止监听
stop_speech_listening()
```

### 高级功能

#### 切换语音识别提供者

```python
# 获取可用提供者
manager = get_speech_input_manager()
providers = manager.get_status()["available_providers"]
print(f"可用提供者: {providers}")

# 切换到Windows Speech
manager.switch_provider("Windows Speech")

# 切换到Azure Speech
manager.switch_provider("AzureSpeechProvider")
```

#### 设置识别语言

```python
# 设置中文识别
manager.set_language("zh-CN")

# 设置英文识别
manager.set_language("en-US")

# 获取支持的语言
languages = manager.get_supported_languages()
print(f"支持的语言: {languages}")
```

#### 更新配置

```python
# 更新语音输入配置
new_config = {
    "confidence_threshold": 0.8,
    "timeout": 60,
    "continuous": True
}
manager.update_config(new_config)
```

## 集成到主系统

### 在NagaAgent中集成

```python
# 在main.py或相关模块中
from voice.speech_input_manager import get_speech_input_manager

class NagaAgent:
    def __init__(self):
        self.speech_manager = get_speech_input_manager()
        self.init_speech_input()
    
    def init_speech_input(self):
        """初始化语音输入"""
        if self.speech_manager.is_available():
            self.speech_manager.start_listening(
                on_text=self.handle_speech_input,
                on_error=self.handle_speech_error
            )
    
    def handle_speech_input(self, text: str):
        """处理语音输入"""
        # 将语音输入发送给AI助手
        self.send_message_to_ai(text)
    
    def handle_speech_error(self, error: str):
        """处理语音识别错误"""
        print(f"语音识别错误: {error}")
```

### 在GUI界面中集成

```python
# 在PyQt界面中添加语音输入按钮
from PyQt5.QtWidgets import QPushButton
from voice.speech_input_manager import get_speech_input_manager

class ChatWindow:
    def __init__(self):
        self.speech_manager = get_speech_input_manager()
        self.init_voice_button()
    
    def init_voice_button(self):
        """初始化语音按钮"""
        self.voice_button = QPushButton("🎤 语音输入")
        self.voice_button.clicked.connect(self.toggle_voice_input)
        
        # 更新按钮状态
        self.update_voice_button_status()
    
    def toggle_voice_input(self):
        """切换语音输入状态"""
        if self.speech_manager.get_status()["listening"]:
            self.speech_manager.stop_listening()
        else:
            self.speech_manager.start_listening(
                on_text=self.on_voice_text,
                on_status=self.on_voice_status
            )
        self.update_voice_button_status()
    
    def on_voice_text(self, text: str):
        """处理语音文本"""
        # 将语音文本添加到输入框
        self.input_text.append(text)
    
    def on_voice_status(self, status: dict):
        """处理语音状态变化"""
        self.update_voice_button_status()
    
    def update_voice_button_status(self):
        """更新语音按钮状态"""
        status = self.speech_manager.get_status()
        if status["listening"]:
            self.voice_button.setText("🔴 停止语音")
            self.voice_button.setStyleSheet("background-color: #ff4444;")
        else:
            self.voice_button.setText("🎤 开始语音")
            self.voice_button.setStyleSheet("background-color: #44ff44;")
```

## 故障排除

### 常见问题

#### 1. 语音识别不可用
**问题**：`语音识别不可用` 错误
**解决方案**：
- 检查麦克风权限设置
- 确认Windows语音识别已启用
- 检查依赖库是否正确安装

#### 2. 识别精度低
**问题**：语音识别结果不准确
**解决方案**：
- 调整 `confidence_threshold` 参数
- 确保环境噪音较小
- 使用更好的麦克风设备

#### 3. 网络连接问题
**问题**：Azure或Google语音服务连接失败
**解决方案**：
- 检查网络连接
- 验证API密钥是否正确
- 确认服务区域设置

#### 4. 权限问题
**问题**：无法访问麦克风
**解决方案**：
- 检查Windows隐私设置
- 确认应用有麦克风访问权限
- 重启应用或系统

### 调试模式

启用详细日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 获取语音输入管理器
manager = get_speech_input_manager()
print(f"可用性: {manager.is_available()}")
print(f"状态: {manager.get_status()}")
```

## 性能优化

### 1. 选择合适的提供者
- **本地使用**：推荐Windows Speech API
- **高精度需求**：推荐Azure Speech Service
- **免费使用**：推荐Google Speech Recognition

### 2. 调整配置参数
```json
{
  "speech_input": {
    "confidence_threshold": 0.7,  // 置信度阈值
    "timeout": 30,                // 超时时间
    "continuous": true            // 连续识别
  }
}
```

### 3. 资源管理
- 及时停止不需要的语音监听
- 避免同时使用多个语音识别提供者
- 定期清理临时音频文件

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持Windows Speech API
- 支持Google Speech Recognition
- 支持Azure Speech Service
- 提供统一的管理接口

## 贡献

欢迎提交Issue和Pull Request来改进语音输入功能！

## 许可证

本项目采用GNU GPL v3.0协议。
