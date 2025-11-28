# NagaAgent 3.42.1

> NagaAgent V3.42.1仅为娱乐，不代表原始项目进度，基于NagaAgent V3.2。

**🐍 智能对话助手 | 多平台支持 | 基于知识图谱的长期记忆系统**

[核心功能](#核心功能) • [快速开始](#快速开始) • [安装指南](#详细安装指南) • [GRAG记忆系统简介](#grag记忆系统简介) • [配置说明](#配置说明) • [API文档](#restful-api服务) • [技术文档](GRAG_MEMORY_TECHNICAL.md)

---

## 🎯 项目亮点

✅ **🧠 GRAG知识图谱记忆**: 基于Neo4j的智能记忆系统，AI自动决定何时存储/查询
✅ **🔧 丰富生态**: 支持多种MCP服务和Agent系统，动态服务发现
✅ **🎤 语音交互**: OpenAI兼容的流式语音合成，完全异步处理
✅ **🖥️ 现代界面**: 基于PyQt5的图形界面，支持透明背景和Markdown
✅ **🌐 完整API**: FastAPI RESTful API和流式输出，自动文档生成
✅ **📱 系统托盘**: 最小化到托盘，支持开机自启动
✅ **🤖 多Agent协作**: 独立的AgentManager系统，会话隔离和TTL管理
✅ **🌳 深度思考**: 基于遗传算法的多分支思考引擎
✅ **🔄 配置热更新**: 实时配置变更，无需重启应用
✅ **💾 持久化上下文**: 重启后自动恢复历史对话

---

## 🚀 快速开始

### 📋 系统要求

- **操作系统**: Windows 10/11, macOS 10.15+, Linux
- **Python**: 3.10+ (推荐 3.11)
- **内存**: 建议 4GB 以上
- **存储**: 建议 2GB 以上可用空间
- **Neo4j**: Docker环境（用于记忆系统）

### 🔧 一键安装

<details>
<summary><strong>Windows 用户</strong></summary>

```powershell
# 克隆项目
git clone https://github.com/Xxiii8322766509/NagaAgent.git
cd NagaAgent

# 一键配置（自动安装依赖、检查环境）
.\setup.ps1

# 启动Neo4j
docker run -d --restart always --publish=7474:7474 --publish=7687:7687 --env NEO4J_AUTH=neo4j/your_password --volume=neo4j_data:/data neo4j:latest

# 复制配置
cp config.json.example config.json
# 编辑config.json，填入API密钥等信息
```
</details>

<details>
<summary><strong>macOS 用户</strong></summary>

```bash
# 克隆项目
git clone https://github.com/Xxiii8322766509/NagaAgent.git
cd NagaAgent

# 一键配置
chmod +x setup_mac.sh
./setup_mac.sh

# 启动Neo4j
docker run -d --restart always --publish=7474:7474 --publish=7687:7687 --env NEO4J_AUTH=neo4j/your_password --volume=neo4j_data:/data neo4j:latest

# 复制配置
cp config.json.example config.json
# 编辑config.json，填入API密钥等信息
```
</details>

<details>
<summary><strong>Linux 用户</strong></summary>

```bash
# 克隆项目
git clone https://github.com/Xxiii8322766509/NagaAgent.git
cd NagaAgent

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动Neo4j
docker run -d --restart always --publish=7474:7474 --publish=7687:7687 --env NEO4J_AUTH=neo4j/your_password --volume=neo4j_data:/data neo4j:latest

# 复制配置
cp config.json.example config.json
# 编辑config.json，填入API密钥等信息
```
</details>

### 🚀 启动应用

```bash
# Windows托盘模式（推荐）
.\start_with_tray.bat

# Windows普通模式
.\start.bat

# macOS
./start_mac.sh

# Linux
./start.sh
```

启动后将自动开启：
- 🖥️ PyQt5图形界面
- 🌐 RESTful API服务器 (http://127.0.0.1:8000)
- 🎤 语音交互服务
- 🧠 GRAG知识图谱记忆系统
- 🔄 配置热更新系统

访问API文档: http://127.0.0.1:8000/docs

---

## 🧠 GRAG记忆系统简介

NagaAgent使用革命性的**GRAG (Graph-based Retrieval-Augmented Generation)**记忆系统，自动从对话中提取知识并智能查询。

### 工作原理

**存储流程**:
```
对话输入 → AI决策(是否存储?) → 提取五元组 → 语义去重 → 并行存储到文件+Neo4j
```

**查询流程**:
```
用户问题 → AI决策(是否查询?) → 关键词提取 → 并行查询文件/Neo4j → 时间衰减处理 → 返回记忆上下文
```

### 记忆类型

系统支持四种类型的记忆：
- **事实记忆 (fact)**: 客观知识、定义、数据
- **过程记忆 (process)**: 操作步骤、工作流程
- **情感记忆 (emotion)**: 态度偏好、情感表达
- **元记忆 (meta)**: 反思总结、关于记忆的记忆

### 特点

✅ **智能决策**: AI自动判断何时存储/查询，避免盲目存储
✅ **语义去重**: 自动检测相似内容，避免重复存储
✅ **时间感知**: 旧记忆自动降权（指数衰减，半衰期30天）
✅ **结构化管理**: 使用五元组格式（主语-谓语-宾语）存储知识

**详细技术文档**: [GRAG_MEMORY_TECHNICAL.md](GRAG_MEMORY_TECHNICAL.md)

---

## 🌟 核心功能

### 🧠 智能对话系统
- **多模型支持**: 兼容 OpenAI、DeepSeek、Anthropic 等主流 LLM
- **上下文记忆**: 智能维护对话历史，多轮对话上下文
- **流式输出**: 实时显示 AI 回复
- **工具调用**: 自动执行 LLM 返回的工具调用指令
- **记忆增强**: GRAG系统自动提供相关历史信息

### 🔍 在线搜索系统
- **SearXNG集成**: 隐私保护搜索引擎
- **多引擎支持**: Google、Bing等
- **智能结果处理**: 自动格式化搜索结果

### 🗺️ GRAG知识图谱记忆系统
- **五元组提取**: 自动提取实体-关系-属性的结构化知识
- **智能检索**: 基于相似度、时间、重要性的多维度查询
- **时间轴管理**: 智能时间衰减，优先召回近期重要记忆
- **语义去重**: 基于AI的语义相似度去重
- **历史导入**: 兼容旧版对话记录的批量导入

### 🎤 语音交互系统
- **流式合成**: 基于 Edge-TTS 的实时语音合成
- **智能分句**: 自动识别句子边界
- **异步处理**: 文本显示和音频播放完全分离

### 🖥️ 用户界面
- **现代化 GUI**: 基于 PyQt5 的精美界面
- **Markdown支持**: 完整的 Markdown 语法和代码高亮
- **响应式设计**: 自适应不同屏幕尺寸

### 🌐 API 服务
- **RESTful API**: 完整的 HTTP 接口
- **流式支持**: Server-Sent Events 流式输出
- **自动文档**: Swagger交互式文档

### 📱 系统托盘
- **后台运行**: 最小化到系统托盘
- **自启动**: 开机自动启动
- **托盘菜单**: 快捷操作菜单

### 🔧 MCP 服务生态
- **动态服务发现**: 自动扫描和注册所有 MCP 服务
- **即插即用**: 新增服务无需重启
- **多服务协作**: 支持多个 Agent 协同工作

### 🤖 AgentManager系统
- **独立Agent管理**: 动态加载和管理Agent
- **会话隔离**: 多用户会话完全隔离
- **占位符替换**: 支持环境变量、时间等动态内容
- **热重载**: 支持运行时重新加载配置

### 🌳 深度思考引擎
- **多分支并行思考**: 自动生成多条不同类型的思考路线
- **问题难度评估**: 通过文本长度、关键词等判断复杂度
- **遗传算法剪枝**: 适应度评估、交叉融合、精英保留

---

## ⚙️ 配置说明

编辑 `config.json` 文件：

```json
{
  "api": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 10000,
    "max_history_rounds": 10
  },
  "api_server": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8000
  },
  "grag": {
    "enabled": true,
    "neo4j_uri": "neo4j://127.0.0.1:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "your_password",
    "similarity_threshold": 0.8,
    "max_workers": 3
  },
  "online_search": {
    "searxng_url": "https://searxng.pylindex.top",
    "num_results": 5
  }
}
```

### 关键配置说明

- **api.api_key**: LLM服务商的API密钥（必需）
- **base_url**: API地址（如：https://api.deepseek.com/v1）
- **grag.neo4j_password**: Neo4j密码（需与docker启动时一致）
- **grag.similarity_threshold**: 语义去重相似度阈值（0.0-1.0，默认0.8）
  - 值越高，去重越严格（建议0.8-0.9）
- **grag.max_workers**: 任务并发数（根据CPU调整，建议2-5）

### 配置热更新

支持运行时动态更新配置，无需重启：

```python
from config_manager import update_config

# 更新配置
update_config({
    "api": {"temperature": 0.8},
    "grag": {"similarity_threshold": 0.85}
})
```

详细文档: [CONFIG_HOT_RELOAD_GUIDE.md](CONFIG_HOT_RELOAD_GUIDE.md)

---

## 🌐 RESTful API 服务

### 基础信息

- **地址**: http://127.0.0.1:8000
- **文档**: http://127.0.0.1:8000/docs

### 主要接口

#### 对话接口

```bash
# 普通对话
POST /chat
{
  "message": "你好",
  "session_id": "optional-session-id"
}

# 流式对话 (SSE)
POST /chat/stream
{
  "message": "请介绍一下人工智能"
}
```

#### 记忆系统接口

```bash
# 获取记忆统计
GET /memory/stats

# 查询记忆
POST /memory/query
{
  "query": "用户喜欢什么编程语言?",
  "top_k": 5
}
```

#### 系统管理接口

```bash
# 获取系统信息
GET /system/info

# 获取Agent列表
GET /agents

# 切换开发者模式
POST /system/devmode
```

---

## 🔧 工具调用

NagaAgent支持MCP服务和Agent两种工具调用格式：

### MCP服务调用

```json
{
  "agentType": "mcp",
  "service_name": "file",
  "tool_name": "read",
  "path": "test.txt"
}
```

### Agent调用

```json
{
  "agentType": "agent",
  "agent_name": "ExampleAgent",
  "prompt": "请分析这份数据"
}
```

---

## 🏗️ 技术架构

```
用户界面
  ├─ PyQt5 GUI
  ├─ RESTful API
  └─ 语音交互
       ↓
   对话核心
       ↓
  ┌────┴────┐
  ↓         ↓
GRAG记忆    工具调用
  ↓            ↓
Neo4j      MCP/Agent服务
```

**详细技术架构**: [GRAG_MEMORY_TECHNICAL.md](GRAG_MEMORY_TECHNICAL.md#技术架构)

---

## 📁 目录结构

```
NagaAgent/
├── main.py                     # 主入口
├── config.py                   # 全局配置
├── config.json.example         # 配置模板
├── conversation_core.py        # 对话核心
├── summer_memory/              # GRAG记忆系统
├── mcpserver/                  # MCP服务和Agent
├── thinking/                   # 深度思考引擎
├── ui/                         # 图形界面
├── voice/                      # 语音交互
├── apiserver/                  # API服务器
└── logs/                       # 日志和记忆数据
```

---

## 🆙 历史对话导入

支持将旧版txt对话导入GRAG记忆系统：

1. **激活升级指令**：
   ```
   #夏园系统兼容升级
   ```

2. **导入全部历史**：
   ```bash
   python summer_memory/main.py import all
   ```

3. **选择导入**（如第1、3、5-8条）：
   ```bash
   python summer_memory/main.py import 1,3,5-8
   ```

---

## 🔍 开发模式

输入 `#devmode` 进入开发者模式：
- 对话不写入GRAG记忆（仅测试）
- 显示详细调试信息
- 工具调用日志更详细

再次输入 `#devmode` 退出。

---

## ❓ 常见问题

### 环境检查

```bash
python check_env.py
```

### 接入问题

**Neo4j连接失败**:
- 检查Docker容器: `docker ps | grep neo4j`
- 确认配置: `config.json`中的`neo4j_uri`, `neo4j_user`, `neo4j_password`

**API调用失败**:
- 检查API密钥是否正确
- 检查`base_url`格式（需/v1结尾）

**依赖安装失败**:
- **Windows**: 安装Microsoft Visual C++ Build Tools
- **macOS**: `brew install portaudio`
- **Linux**: `sudo apt install python3-dev portaudio19-dev`

详细排查: [GRAG_MEMORY_TECHNICAL.md](GRAG_MEMORY_TECHNICAL.md)

### 运行问题

**程序崩溃**:
- 检查Python版本（需3.10+）
- 检查内存（建议4GB+）
- 查看日志: `logs/app.log`

**记忆不工作**:
- 确认`grag.enabled: true`
- 检查记忆文件: `logs/knowledge_graph/`

**工具调用失败**:
- 检查`MAX_handoff_LOOP_STREAM`配置
- 确认MCP服务已注册

---

## 📊 性能优化

快速优化建议：

1. **Neo4j索引**:
   ```cypher
   CREATE INDEX ON :Memory(subject)
   CREATE INDEX ON :Memory(timestamp_raw)
   ```

2. **调整工作线程**:
   ```json
   "max_workers": 3  # 根据CPU核心数调整
   ```

3. **调整相似度阈值**:
   ```json
   "similarity_threshold": 0.8  # 0.75-0.9之间调整
   ```

详细策略: [GRAG_MEMORY_TECHNICAL.md#性能优化](GRAG_MEMORY_TECHNICAL.md#性能优化策略)

---

## 🤝 贡献指南

欢迎报告问题、提出建议、代码贡献和文档改进！

- **Issues**: [GitHub Issues](https://github.com/Xxiii8322766509/NagaAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Xxiii8322766509/NagaAgent/discussions)

开发规范：遵循 PEP 8，添加注释和文档。

---

## 📄 许可证

MIT许可证 - 详见 [LICENSE](LICENSE) 文件

---

**⭐ 如果项目对您有帮助，请给我们一个 Star！**
