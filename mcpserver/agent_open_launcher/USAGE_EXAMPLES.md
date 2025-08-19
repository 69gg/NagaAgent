# AppLauncherAgent 使用示例

## 概述

AppLauncherAgent是一个智能应用启动工具，支持从Windows注册表和快捷方式扫描应用并启动。采用简化的设计：一个工具即可获取应用列表或启动应用，优先使用快捷方式启动。

## 基本用法

### 1. 获取应用列表

当用户想要启动应用但不知道具体有哪些应用可用时，可以调用：

```json
{
  "agentType": "mcp",
  "service_name": "AppLauncherAgent",
  "tool_name": "open"
}
```

**返回示例：**
```json
{
  "success": true,
  "status": "apps_ready",
  "message": "成功获取到 45 个可用应用，请从列表中选择要启动的应用",
  "data": {
    "total_count": 45,
    "apps": [
      {
        "name": "7-Zip 24.09 (x64)",
        "description": "从注册表扫描到的应用: 7-Zip 24.09 (x64)",
        "type": "registry",
        "source": "registry"
      },
      {
        "name": "Google Chrome",
        "description": "从快捷方式扫描到的应用: Google Chrome",
        "type": "shortcut",
        "source": "shortcut"
      }
    ],
    "usage_format": {
      "tool_name": "open",
      "app": "应用名称（从上述列表中选择）",
      "args": "启动参数（可选）"
    },
    "example": {
      "tool_name": "open",
      "app": "7-Zip 24.09 (x64)",
      "args": ""
    }
  }
}
```

### 2. 启动指定应用

当用户知道要启动的应用名称时，可以直接调用：

```json
{
  "agentType": "mcp",
  "service_name": "AppLauncherAgent",
  "tool_name": "open",
  "app": "Google Chrome"
}
```

**返回示例：**
```json
{
  "success": true,
  "status": "app_started",
  "message": "已成功通过快捷方式启动应用: Google Chrome",
  "data": {
    "app_name": "Google Chrome",
    "shortcut_path": "C:\\Users\\User\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Google Chrome.lnk",
    "exe_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "args": null,
    "source": "shortcut"
  }
}
```

### 3. 启动应用并传递参数

```json
{
  "agentType": "mcp",
  "service_name": "AppLauncherAgent",
  "tool_name": "open",
  "app": "notepad",
  "args": "C:\\temp\\test.txt"
}
```

## 实际使用场景

### 场景1：用户想要打开浏览器

**用户输入：** "帮我打开浏览器"

**LLM处理流程：**
1. 首先调用工具获取应用列表
2. 从列表中找到浏览器应用（如Google Chrome、Microsoft Edge等）
3. 调用工具启动选定的浏览器

### 场景2：用户想要打开特定应用

**用户输入：** "打开7-Zip"

**LLM处理流程：**
1. 直接调用工具启动7-Zip应用
2. 如果应用不存在，会返回可用应用列表供重新选择

### 场景3：用户想要打开文档编辑器

**用户输入：** "打开记事本编辑文件"

**LLM处理流程：**
1. 调用工具获取应用列表
2. 找到记事本或类似的文本编辑器
3. 调用工具启动应用并传递文件路径参数

## 错误处理示例

### 应用不存在的情况

```json
{
  "agentType": "mcp",
  "service_name": "AppLauncherAgent",
  "tool_name": "open",
  "app": "nonexistent_app"
}
```

**返回示例：**
```json
{
  "success": false,
  "status": "app_not_found",
  "message": "未找到应用 'nonexistent_app'，请从以下可用应用中选择: 7-Zip 24.09 (x64), 7zFM, AntiCheatExpert, Blender, cloudmusic, Cursor (User), DingTalk, Docker Desktop, excel, Git, Google Chrome, Maxon Cinema 4D 2023, Microsoft Office 家庭和学生版 2021 - zh-cn, Microsoft OneNote - zh-cn, msedge, msoadfsb, msoasb, msoxmled, OneNote, powerpnt",
  "data": {
    "requested_app": "nonexistent_app",
    "available_apps": ["7-Zip 24.09 (x64)", "7zFM", "AntiCheatExpert", "Blender", "cloudmusic", "Cursor (User)", "DingTalk", "Docker Desktop", "excel", "Git", "Google Chrome", "Maxon Cinema 4D 2023", "Microsoft Office 家庭和学生版 2021 - zh-cn", "Microsoft OneNote - zh-cn", "msedge", "msoadfsb", "msoasb", "msoxmled", "OneNote", "powerpnt"],
    "total_available": 45,
    "suggestion": "请使用 'open' 工具（不提供app参数）获取完整应用列表"
  }
}
```

## 最佳实践

1. **首次使用**：建议先调用工具获取应用列表，了解可用的应用
2. **应用名称**：使用完整的应用名称，如"Google Chrome"而不是"chrome"
3. **参数传递**：某些应用支持启动参数，如文件路径等
4. **错误处理**：当应用不存在时，会提供可用应用列表供重新选择

## 技术特点

- **综合扫描**：自动从Windows注册表和快捷方式扫描已安装的应用
- **智能匹配**：支持应用名称的精确匹配和模糊匹配
- **优先策略**：当应用同时存在于多个来源时，优先使用快捷方式启动
- **简化设计**：一个工具支持两种功能，减少复杂度
- **错误提示**：提供友好的错误信息和可用选项
