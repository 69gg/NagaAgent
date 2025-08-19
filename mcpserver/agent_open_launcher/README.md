# AppLauncherAgent（综合版）

智能应用启动Agent，支持从Windows注册表和快捷方式扫描应用并启动。采用智能交互方式：一个工具即可获取应用列表或启动应用，优先使用快捷方式启动。  # 简介 #

## 功能特点

- **综合扫描**: 从Windows注册表和快捷方式自动扫描已安装的应用  # 功能 #
- **智能交互**: 一个工具即可获取应用列表或启动应用  # 功能 #
- **智能匹配**: 支持应用名称的智能匹配和错误提示  # 功能 #
- **优先策略**: 当应用同时存在于注册表和快捷方式时，优先使用快捷方式启动  # 功能 #
- **简化设计**: 减少工具数量，提高使用效率  # 功能 #

## 可用工具

### `open` - 智能应用启动工具
智能应用启动工具，支持两种使用方式：
1. 获取应用列表（不提供app参数）
2. 启动指定应用（提供app参数）

**使用方式1 - 获取应用列表:**
```json
{"tool_name": "open"}
```

**使用方式2 - 启动指定应用:**
```json
{"tool_name": "open", "app": "notepad"}
```

**参数说明:**
- `app`: 应用名称（可选，不提供则返回应用列表）
- `args`: 启动参数（可选）

**返回格式示例（获取应用列表）:**
```json
{
  "success": true,
  "status": "apps_ready",
  "message": "成功获取到X个可用应用，请从列表中选择要启动的应用",
  "data": {
    "total_count": X,
    "apps": [
      {
        "name": "应用名",
        "description": "从注册表扫描到的应用: 应用名",
        "type": "registry"
      }
    ],
    "usage_format": {
      "tool_name": "open",
      "app": "应用名称（从上述列表中选择）",
      "args": "启动参数（可选）"
    },
    "example": {
      "tool_name": "open",
      "app": "notepad",
      "args": ""
    }
  }
}
```

## 使用流程

1. **获取应用列表**: 调用`open`工具（不提供app参数）获取可用应用列表  # 流程 #
2. **选择应用**: 从返回的列表中选择要启动的应用名称  # 流程 #
3. **启动应用**: 调用`open`工具（提供app参数）启动选定的应用  # 流程 #

## 扫描范围

### 注册表扫描
- **App Paths**: `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths`  # 扫描范围 #
- **系统卸载**: `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`  # 扫描范围 #
- **用户卸载**: `HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`  # 扫描范围 #

### 快捷方式扫描
- **开始菜单**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs`  # 扫描范围 #
- **启动文件夹**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`  # 扫描范围 #
- **系统程序**: `C:\ProgramData\Microsoft\Windows\Start Menu\Programs`  # 扫描范围 #
- **桌面**: `%USERPROFILE%\Desktop`  # 扫描范围 #

## 错误处理

- **应用未找到**: 如果指定的应用不存在，会返回可用应用列表供重新选择  # 错误处理 #
- **启动失败**: 如果应用启动失败，会返回详细的错误信息  # 错误处理 #
- **注册表访问失败**: 如果无法访问注册表，会返回相应的错误信息  # 错误处理 #

## 架构说明

- **综合扫描器**: 使用`ComprehensiveAppScanner`类从Windows注册表和快捷方式扫描应用信息  # 架构 #
- **智能交互**: 一个工具支持两种功能，简化使用流程  # 架构 #
- **缓存机制**: 应用列表会被缓存，提高响应速度  # 架构 #
- **优先策略**: 当应用同时存在于多个来源时，优先选择快捷方式  # 架构 #
- **错误提示**: 当应用未找到时，会提供可用应用列表供LLM重新选择  # 架构 #

## 与旧版本的区别

- **数据源**: 从单一注册表扫描扩展为注册表+快捷方式综合扫描  # 区别 #
- **启动策略**: 根据应用来源选择不同的启动方式，优先使用快捷方式  # 区别 #
- **覆盖范围**: 大幅提升应用发现率，覆盖更多应用类型  # 区别 #
- **智能匹配**: 支持精确匹配和模糊匹配，提高应用查找成功率  # 区别 #
- **架构优化**: 简化了代码结构，提高了可维护性  # 区别 #

## 配置说明

- 无需额外配置，系统会自动扫描Windows注册表和快捷方式  # 配置 #
- 应用信息会被缓存以提高性能  # 配置 #
- 支持自动去重和排序，优先选择快捷方式  # 配置 #
- 需要安装win32com模块以支持快捷方式解析  # 配置 #
