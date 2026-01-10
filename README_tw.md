# NagaAgent

[简体中文](README.md)|[繁體中文](README_tw.md)|[English](README_en.md)

![NagaAgent Logo](https://img.shields.io/badge/NagaAgent-4.0-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

![Star History](https://img.shields.io/github/stars/Xxiii8322766509/NagaAgent?style=social)![Forks](https://img.shields.io/github/forks/Xxiii8322766509/NagaAgent?style=social)![Issues](https://img.shields.io/github/issues/Xxiii8322766509/NagaAgent)![Pull Requests](https://img.shields.io/github/issues-pr/Xxiii8322766509/NagaAgent)
![UI 預覽](ui/img/README.jpg)
---

## [此處獲取教學影片與一鍵執行整合包](https://www.pylindex.top/naga)


## 介紹

NagaAgent 是一個功能豐富的智慧對話助理系統，具有以下特色功能：

### 🎯 核心功能
- **智慧對話系統**：支援串流對話和工具呼叫循環
- **多Agent協作**：基於博弈論的智慧任務調度
- **知識圖譜記憶**：GRAG系統支援長期記憶和智慧檢索
- **完整語音互動**：即時語音輸入輸出處理
- **現代化介面**：PyQt5 GUI + Live2D虛擬形象
- **系統匣整合**：背景執行和快捷操作

### 🛠️ 技術架構

#### 系統整體架構
```mermaid
graph TB
    %% 使用者介面層
    subgraph "使用者介面層 (UI Layer)"
        UI[PyQt5 GUI介面]
        Live2D[Live2D虛擬形象]
        Tray[系統匣]
        Chat[聊天介面]
    end

    %% 核心服務層
    subgraph "核心服務層 (Core Services)"
        API[API伺服器<br/>:8000]
        Agent[Agent伺服器<br/>:8001]
        MCP[MCP伺服器<br/>:8003]
        TTS[TTS伺服器<br/>:5048]
    end

    %% 業務邏輯層
    subgraph "業務邏輯層 (Business Logic)"
        Game[博弈論系統<br/>多Agent協作]
        Memory[GRAG記憶系統<br/>知識圖譜]
        Voice[語音處理系統<br/>即時語音互動]
        Tools[工具呼叫系統<br/>MCP協議]
    end

    %% 資料儲存層
    subgraph "資料儲存層 (Data Storage)"
        Neo4j[(Neo4j圖資料庫<br/>知識圖譜儲存)]
        Files[檔案系統<br/>設定/日誌/快取]
        MemoryCache[記憶體快取<br/>會話狀態]
    end

    %% 外部服務層
    subgraph "外部服務層 (External Services)"
        LLM[LLM服務商<br/>OpenAI/通義千問等]
        Portal[NagaPortal<br/>門戶服務]
        MQTT[物聯網裝置<br/>MQTT通訊]
        Web[網路爬蟲<br/>線上搜尋]
    end

    %% 連接關係
    UI --> API
    UI --> Agent
    UI --> MCP
    UI --> TTS

    API --> Game
    API --> Memory
    API --> Voice
    API --> Tools

    Agent --> Game
    Agent --> Tools

    MCP --> Tools
    MCP --> Portal
    MCP --> MQTT
    MCP --> Web

    TTS --> Voice

    Game --> Memory
    Memory --> Neo4j
    Voice --> LLM
    Tools --> LLM

    API --> MemoryCache
    Agent --> MemoryCache
    MCP --> MemoryCache

    %% 樣式
    classDef uiLayer fill:#e1f5fe
    classDef coreLayer fill:#f3e5f5
    classDef businessLayer fill:#e8f5e8
    classDef dataLayer fill:#fff3e0
    classDef externalLayer fill:#fce4ec

    class UI,Live2D,Tray,Chat uiLayer
    class API,Agent,MCP,TTS coreLayer
    class Game,Memory,Voice,Tools businessLayer
    class Neo4j,Files,MemoryCache dataLayer
    class LLM,Portal,MQTT,Web externalLayer

```

#### 核心特性
- **多服務並行**：API伺服器(8000)、Agent伺服器(8001)、MCP伺服器(8003)、TTS伺服器(5048)
- **模組化設計**：各服務獨立執行，支援熱插拔
- **設定驅動**：即時設定熱更新，無需重啟
- **跨平台支援**：Windows、macOS、Linux

### 🔧 技術棧

#### 技術棧架構
```mermaid
graph TB
    %% 前端技術棧
    subgraph "前端技術棧 (Frontend Stack)"
        PyQt5[PyQt5<br/>GUI框架]
        Live2D[Live2D<br/>虛擬形象]
        QSS[QSS<br/>樣式表]
    end

    %% 後端技術棧
    subgraph "後端技術棧 (Backend Stack)"
        FastAPI[FastAPI<br/>Web框架]
        Uvicorn[Uvicorn<br/>ASGI伺服器]
        AsyncIO[AsyncIO<br/>非同步程式設計]
    end

    %% 資料庫技術棧
    subgraph "資料庫技術棧 (Database Stack)"
        Neo4j[Neo4j<br/>圖資料庫]
        GRAG[GRAG<br/>知識圖譜]
        Memory[記憶體快取<br/>會話管理]
    end

    %% AI技術棧
    subgraph "AI技術棧 (AI Stack)"
        OpenAI[OpenAI API<br/>GPT模型]
        Qwen[通義千問<br/>多模態模型]
        MCP[MCP協議<br/>工具呼叫]
    end

    %% 語音技術棧
    subgraph "語音技術棧 (Voice Stack)"
        ASR[語音辨識<br/>ASR]
        TTS[語音合成<br/>TTS]
        Realtime[即時語音<br/>WebRTC]
    end

    %% 網路技術棧
    subgraph "網路技術棧 (Network Stack)"
        HTTP[HTTP/HTTPS<br/>RESTful API]
        WebSocket[WebSocket<br/>即時通訊]
        MQTT[MQTT<br/>物聯網協議]
    end

    %% 樣式
    classDef frontend fill:#e3f2fd
    classDef backend fill:#f1f8e9
    classDef database fill:#fff3e0
    classDef ai fill:#fce4ec
    classDef voice fill:#e8f5e8
    classDef network fill:#f3e5f5

    class PyQt5,Live2D,QSS frontend
    class FastAPI,Uvicorn,AsyncIO backend
    class Neo4j,GRAG,Memory database
    class OpenAI,Qwen,MCP ai
    class ASR,TTS,Realtime voice
    class HTTP,WebSocket,MQTT network
```

#### 核心技術
- **Python 3.11** + PyQt5 + FastAPI
- **Neo4j圖資料庫** + GRAG知識圖譜
- **MCP (Model Context Protocol)** 工具呼叫
- **OpenAI相容API** + 多種LLM服務商支援


---

## 部署執行教學

### 環境要求
- Python 3.11
- 可選：uv工具（加速依賴安裝，且無需特定python版本）

### 快速開始

>  如果您的部署有困難，可以參考影片教學或下載一鍵執行整合包。

#### 1. 安裝依賴
##### 使用setup腳本

```bash
# 可選：先安裝uv
pip install uv

# 使用 setup.py 自動初始化
python setup.py

# 或使用 setup.sh (Linux/macOS)
./setup.sh

# 或使用 setup.bat (Windows)
setup.bat
```

初始化腳本會自動：
- 偵測Python版本
- 建立虛擬環境
- 安裝依賴套件
- 複製設定檔範本
- 開啟設定檔供編輯
</details>

<details><summary>手動部署</summary>

```bash
# 無uv
python -m venv .venv

# linux/Mac OS
source .venv/bin/activate
# Windows
.\.venv\Scripts\activate

pip install -r requirements.txt

# 使用uv
uv sync
```
</details>

#### 2. 設定LLM API
編輯 `config.json` 檔案，設定您的LLM API資訊：
```json
{
  "api": {
    "api_key": "你的api_key",
    "base_url": "模型服務商OPENAI API端點",
    "model": "模型名稱"
  }
}
```

<details><summary>可選設定</summary>

#### 啟用知識圖譜記憶

使用 `docker` 安裝 `neo4j` 或安裝 `neo4j desktop` 並在 `config.json` 中設定 Neo4j 連接參數：
```json
{
  "grag": {
    "enabled": true,
    "neo4j_uri": "neo4j://127.0.0.1:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "你安裝neo4j時設定的密碼"
  }
}
```

#### 啟用語音輸出功能
```json
{
  "system": {
    "voice_enabled": true
  },
  "tts": {
    "port": 5048
  }
}
```

#### Live2D 相關設定

```json5
  "live2d": {
    "enabled": false, # 是否啟用Live2D
    "model_path": "ui/live2d_local/live2d_models/重音テト/重音テト.model3.json", # Live2D模型路徑
    "fallback_image": "ui/img/standby.png", # 備用圖片
    "auto_switch": true, # 是否自動切換
    "animation_enabled": true, # 是否啟用動畫
    "touch_interaction": true # 是否啟用觸摸互動
  },
  ```

#### 啟用 GPT-SoVITS 語音合成

GPT-SoVITS 是一個高效能的 TTS 系統，支援聲音克隆功能。啟用後，將使用外部部署的 GPT-SoVITS 服務取代預設的 edge-tts。

**設定步驟：**

1. **部署 GPT-SoVITS 服務**（如果尚未部署）
   ```bash
   # 參考 GPT-SoVITS 官方倉庫部署
   # 預設執行在 http://127.0.0.1:9880
   ```

2. **準備參考音訊**
   - 選擇一段清晰的音訊檔案（建議 10-30 秒）
   - 精確記錄該音訊對應的文字內容
   - 確保 GPT-SoVITS 服務可以存取參考音訊路徑

3. **設定 config.json**
   ```json
   {
     "tts": {
       "sovits": {
         "enabled": true,      // 啟用 GPT-SoVITS（優先級最高）
         "api_url": "http://127.0.0.1:9880",  // SoVITS API 位址
         "reference_audio": "/path/to/reference.wav",  // 參考音訊路徑
         "reference_text": "參考音訊的文字內容",  // 必須與音訊相符
         "language": "zh",       // 語言代碼：zh/ja/en
         "timeout": 120         // 請求逾時時間（秒）
       }
     }
   }
   ```

**功能特性：**

- **聲音克隆**：使用參考音訊克隆特定音色
- **串流支援**：串流模式下遇到標點（。；！？）立即合成
- **順序播放**：確保多個音訊按句子順序播放，不會亂序
- **自動清理**：播放完成後自動刪除臨時音訊檔案
- **優先級高**：`sovits.enabled = true` 時將無視其他 TTS 設定

**注意事項：**

- 確保參考音訊路徑是 GPT-SoVITS 服務可以存取的絕對路徑
- `reference_text` 必須精確匹配參考音訊的內容
- 如果 SoVITS 推理較慢，可適當增加 `timeout` 值
- 串流模式標點：。；！？.\\?\\!\\;（不包含逗號）
- 非串流模式：按句號切割後異步生成

> 其他設定項可參考註解

</details>

#### 3. 啟動應用
```bash
# 使用啟動腳本
./start.sh          # Linux/macOS
start.bat           # Windows


# 或直接執行py檔案
# linux/Mac OS
source .venv/bin/activate
# Windows
.\.venv\Scripts\activate
python main.py

# uv
uv run main.py
```

> 程式會自動偵測上次系統偵測時間，如果偵測通過且超過7天，會自動執行更新並重啟。

#### 手動更新
```bash
# 使用更新腳本
./update.sh         # Linux/macOS
update.bat          # Windows

# 或直接執行py檔案
python update.py
```

更新腳本會自動執行 git pull（自動偵測當前分支）和 uv sync 同步依賴。


<details><summary>故障排除</summary>

1. **Python 版本不相容**：確保使用Python 3.11
2. **埠被佔用**：檢查8000、8001、8003、5048埠是否可用
3. **Neo4j 連接失敗**：確保Neo4j服務正在執行
4. **偵測 Neo4j 連接時出現 json 解析錯誤**：退出並重新啟動程式
5. **未知錯誤**：請建立issue以回饋

</details>

<details><summary>環境偵測</summary>

```bash
# 執行系統環境偵測
python main.py --check-env --force-check

# 快速偵測
python main.py --quick-check
```

</details>


## 授權條款

[NagaAgent License](LICENSE)


## 貢獻

歡迎建立Issue和Pull Request！

<details><summary>建構一鍵執行整合包</summary>

```bash
python build.py
```
建構完成的檔案位於`dist/`目錄下

</details>

[![Star History Chart](https://api.star-history.com/svg?repos=Xxiii8322766509/NagaAgent&type=date&legend=top-left)](https://www.star-history.com/#Xxiii8322766509/NagaAgent&type=date&legend=top-left)

<div align="center">

**感謝所有開發者對本專案做出的貢獻**

**⭐ 如果這個專案對您有幫助，請考慮給我們一個 Star**

</div>
