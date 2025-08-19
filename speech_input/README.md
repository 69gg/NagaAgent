# 语音输入模块 🎤

## 概述

语音输入模块是NagaAgent的独立语音识别功能模块，基于Windows Runtime Speech APIs重构，提供完整的语音识别功能，包括权限检查、约束配置、UI选项等。

## 目录结构

```
speech_input/
├── __init__.py                    # 模块初始化文件
├── README.md                      # 本文件
├── SPEECH_INPUT_GUIDE.md          # 详细使用指南
├── speech_input_manager.py        # 语音输入管理器（主要接口）
├── windows_speech_input.py        # Windows Speech API实现（重构版）
├── test_speech_input.py           # 功能测试脚本
└── example_usage.py               # 使用示例脚本
```

## 重构特性

### 🆕 新增功能
- **权限检查**：自动检查麦克风权限和设备可用性
- **约束配置**：支持听写、网络搜索、列表约束等多种识别模式
- **UI选项**：可自定义语音识别UI的提示文本和显示选项
- **异步支持**：提供异步和同步两种调用方式
- **状态监控**：实时监控语音识别状态变化
- **配置管理**：统一的配置管理和应用机制

### 🔧 改进功能
- **错误处理**：更完善的异常处理和错误恢复
- **性能优化**：优化的资源管理和内存使用
- **代码结构**：更清晰的模块化设计
- **文档完善**：详细的使用说明和示例

## 依赖安装

### WinRT依赖安装说明

本模块基于Windows Runtime (WinRT) API，需要安装特定的Python包。根据官方文档，需要安装以下依赖：

#### 1. 核心依赖包

```bash
# 核心运行时支持
pip install winrt-runtime

# 基础类型和异步支持
pip install winrt-Windows.Foundation
pip install winrt-Windows.Foundation.Collections

# 语音识别相关
pip install winrt-Windows.Media.SpeechRecognition
pip install winrt-Windows.Media.Capture
pip install winrt-Windows.Media.MediaProperties

# 全局化和系统支持
pip install winrt-Windows.Globalization
pip install winrt-Windows.System
```

#### 2. 一键安装命令

推荐使用以下命令一次性安装所有必需依赖：

```bash
pip install winrt-runtime \
  winrt-Windows.Foundation \
  winrt-Windows.Foundation.Collections \
  winrt-Windows.Globalization \
  winrt-Windows.Media.SpeechRecognition \
  winrt-Windows.Media.Capture \
  winrt-Windows.Media.MediaProperties \
  winrt-Windows.System
```

或者使用提供的requirements.txt文件：

```bash
pip install -r requirements.txt
```

#### 3. 常见依赖问题解决

**问题1：`ModuleNotFoundError: No module named 'winrt.windows.media.speechrecognition'`**
- 解决：安装 `winrt-Windows.Media.SpeechRecognition` 包

**问题2：`ModuleNotFoundError: No module named 'winrt.windows.foundation.collections'`**
- 解决：安装 `winrt-Windows.Foundation.Collections` 包

**问题3：`ImportError: DLL load failed while importing _winrt`**
- 解决：确保Python版本为3.9+，且架构匹配（32位/64位）

**问题4：`No matching distribution found for winrt`**
- 解决：不要安装过时的`winrt`包，应使用`winrt-runtime`+namespace包的方式

#### 4. 依赖包说明

| Python模块（import语句） | 必需PyPI包名 | 主要功能 |
|------------------------|-------------|----------|
| winrt.windows.media.speechrecognition | winrt-Windows.Media.SpeechRecognition | 语音识别API |
| winrt.windows.foundation | winrt-Windows.Foundation | 基础类型、异步支持 |
| winrt.windows.foundation.collections | winrt-Windows.Foundation.Collections | 集合协议支持 |
| winrt.windows.globalization | winrt-Windows.Globalization | 多语言、本地化 |
| winrt.windows.media.capture | winrt-Windows.Media.Capture | 音频/视频捕获 |
| winrt.windows.media.mediaproperties | winrt-Windows.Media.MediaProperties | 媒体属性 |
| winrt.windows.system | winrt-Windows.System | 系统管理 |

#### 5. 环境要求

- **Python版本**：3.9或更高版本
- **操作系统**：Windows 10/11
- **架构**：x64（推荐）
- **权限**：麦克风访问权限

## 快速开始

### 1. 导入模块

```python
# 导入整个模块
import speech_input

# 或者导入特定功能
from speech_input import get_speech_input_manager, start_speech_listening
```

### 2. 基本使用

```python
from speech_input import get_speech_input_manager

# 获取语音输入管理器
manager = get_speech_input_manager()

# 定义回调函数
def on_text_received(text: str):
    print(f"收到语音输入: {text}")

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

### 3. 便捷函数使用

```python
from speech_input import start_speech_listening, stop_speech_listening

# 开始监听
start_speech_listening(
    on_text=lambda text: print(f"语音: {text}"),
    on_error=lambda error: print(f"错误: {error}")
)

# 停止监听
stop_speech_listening()
```

## 高级功能

### 1. 约束配置

```python
from speech_input import get_speech_input_manager

manager = get_speech_input_manager()

# 添加列表约束（特定词汇识别）
manager.add_list_constraint("commands", ["开始", "停止", "退出", "帮助"])

# 启用网络搜索约束
manager.set_web_search_enabled(True)

# 设置UI选项
manager.set_ui_options({
    "audible_prompt": "请说出您的命令...",
    "example_text": "例如：'开始录音'、'停止录音'"
})
```

### 2. UI识别模式

```python
from speech_input import recognize_with_ui

# 使用Windows默认UI进行单次识别
result = recognize_with_ui(
    on_text=lambda text: print(f"识别结果: {text}"),
    on_error=lambda error: print(f"识别错误: {error}")
)

if result:
    print(f"最终结果: {result}")
```

### 3. 配置管理

```python
from speech_input import get_speech_input_manager

manager = get_speech_input_manager()

# 获取当前配置
config = manager.get_config()
print(f"当前配置: {config}")

# 更新配置
new_config = {
    "speech_config": {
        "confidence_threshold": 0.8,
        "auto_stop_silence_timeout": 5
    },
    "ui_options_config": {
        "audible_prompt": "新的提示音...",
        "example_text": "新的示例文本"
    }
}
manager.update_config(new_config)
```

## 支持的语音识别方案

### Windows Speech API (推荐)
- **优势**：Windows 11原生支持，无需额外配置
- **特点**：基于设备的语音识别，隐私保护好
- **要求**：Windows 10/11系统
- **免费**：完全免费使用
- **新功能**：支持约束配置、UI选项、权限检查

## 配置

在 `config.json` 中添加语音输入配置：

```json
{
  "speech_input": {
    "enabled": true,
    "auto_start": false,
    "language": "zh-CN",
    "confidence_threshold": 0.7,
    "timeout": 30,
    "continuous": true,
    "use_ui": false,
    "auto_stop_silence_timeout": 3
  },
  "speech_constraints": {
    "dictation": true,
    "web_search": false,
    "list_constraints": [
      ["commands", ["开始", "停止", "退出"]]
    ]
  },
  "speech_ui_options": {
    "audible_prompt": "请说话...",
    "example_text": "例如：'今天天气怎么样'",
    "is_readback_enabled": true,
    "show_confirmation": true
  }
}
```

## 依赖

主要依赖包括：
- `winrt-runtime>=3.2.1` - Windows Runtime支持
- `winrt-Windows.Foundation>=3.2.1` - 基础类型支持
- `winrt-Windows.Foundation.Collections>=3.2.1` - 集合协议支持
- `winrt-Windows.Globalization>=3.2.1` - 多语言支持
- `winrt-Windows.Media.SpeechRecognition>=3.2.1` - 语音识别API
- `winrt-Windows.Media.Capture>=3.2.1` - 媒体捕获
- `winrt-Windows.Media.MediaProperties>=3.2.1` - 媒体属性
- `winrt-Windows.System>=3.2.1` - 系统管理

## 测试

运行测试脚本验证功能：

```bash
cd speech_input
python test_speech_input.py
```

测试内容包括：
- Windows Speech API导入
- 音频捕获权限检查
- 语音输入模块功能
- 语音识别功能
- UI识别功能
- 高级配置功能

## 故障排除

### 常见问题

#### 1. 依赖导入错误
**问题**：`ModuleNotFoundError: No module named 'winrt.windows.xxx'`
**解决方案**：
- 确保已安装对应的`winrt-Windows.xxx`包
- 检查Python版本是否为3.9+
- 重新安装依赖包

#### 2. 权限问题
**问题**：无法访问麦克风
**解决方案**：
- 检查Windows隐私设置
- 确认应用有麦克风访问权限
- 重启应用或系统

#### 3. 语音识别不可用
**问题**：`Windows Speech Runtime不可用`
**解决方案**：
- 确保Windows 10/11系统
- 检查Windows语音识别服务是否启用
- 确认已安装所有必需依赖

## 详细文档

更多详细信息请参考：
- [SPEECH_INPUT_GUIDE.md](SPEECH_INPUT_GUIDE.md) - 完整使用指南
- [故障排除](SPEECH_INPUT_GUIDE.md#故障排除) - 常见问题解决方案

## 版本信息

- 版本：2.0.0 (重构版)
- 作者：NagaAgent Team
- 许可证：GNU GPL v3.0

## 更新日志

### v2.0.0 (2024-01-XX) - 重构版
- 🆕 新增权限检查功能
- 🆕 新增约束配置支持
- 🆕 新增UI选项自定义
- 🆕 新增异步调用支持
- 🆕 新增状态监控功能
- 🔧 改进错误处理机制
- 🔧 优化代码结构
- 📚 完善文档和示例
- 🔧 修复WinRT依赖安装问题

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持Windows Speech API
- 基本语音识别功能
