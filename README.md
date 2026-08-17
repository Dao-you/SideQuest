# 🧭 SideQuest - 智慧城市 Agentic 活動決策與人流疏導系統
> **Google DevJam 2026 參賽作品｜組別：Google Cloud Platform (GCP)｜主題：Agent X 智慧城市**

[![GCP Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?logo=google-cloud&logoColor=white)](https://cloud.google.com/run)
[![Gemini 3.7](https://img.shields.io/badge/Gemini-3.7_Flash-8E75B2?logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Astral uv](https://img.shields.io/badge/Package_Manager-uv_0.12+-DE5FE9?logo=astral&logoColor=white)](https://astral.sh/uv)
[![Firestore](https://img.shields.io/badge/Database-Firestore-FFCA28?logo=firebase&logoColor=black)](https://cloud.google.com/firestore)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## 🌟 專案願景與解決痛點

社群上常見整理週末活動的 IG 帳號，顯示民眾對於「**城市裡現在有什麼活動**」具有高度需求。然而，傳統活動平台與資訊整合面臨四大挑戰：
1. **資訊破碎且被動**：資訊散落於 Accupass、Luma、社群帳號，缺乏即時情境感知。
2. **人潮過度集中**：少數熱門景點（如華山、松菸）在尖峰時段人滿為患，遊憩品質低落。
3. **酷暑與極端曝曬**：夏季高溫與高紫外線 (UV) 易引發熱傷害，缺乏避暑與遮蔭路網引導。
4. **小眾活動曝光不足**：中小型藝文與工作坊缺乏流量，商圈發展失衡。

**SideQuest** 以 Google 頂尖旗艦 **Gemini 3.7 Flash / Vertex AI 為 Agent 大腦**，自主感知微氣候 (Weather/UV)、日照遮蔽率 (Solar)、即時信令與捷運人流 (Crowd Flux)，並調用 Google Maps (Places/Routes) 規劃最優動線。透過創新的**人流疏導懲罰演算法（Crowd Dispersal Algorithm）**，主動推薦舒適的私房替代方案，實現**民眾極致體驗**與**城市智慧治理**的雙贏。

---

## 🏗️ 系統架構圖 (System Architecture)

```
                   ┌───────────────────────────────────────┐
                   │               Frontend                │
                   │        Vue Web + Google Maps JS       │
                   └───────────────────┬───────────────────┘
                                       │ HTTPS / SSE
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Google Cloud Run (Backend)                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │                FastAPI Application Framework                     │  │
 │  │   - REST Endpoints (/api/v1/events, /api/v1/crowd, /healthz)     │  │
 │  │   - SSE Streaming Agent Discovery (/api/v1/agent/chat/stream)   │  │
 │  └──────────────────────────────────┬───────────────────────────────┘  │
 │                                     │                                  │
 │                                     ▼                                  │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │           SideQuest Agent Core (Gemini 2.0 / Vertex AI)          │  │
 │  │   - Autonomous Multi-step Tool Calling & Planning                │  │
 │  │   - Multi-Criteria Smart Decision & Crowd-Dispersal Ranking      │  │
 │  └──────────────────┬───────────────────────────────┬───────────────┘  │
 │                     │                               │                  │
 │                     ▼                               ▼                  │
 │       ┌───────────────────────────┐   ┌───────────────────────────┐    │
 │       │     City Data Tools       │   │ Google Maps & Geo Tools   │    │
 │       │ - EventTool (Firestore)   │   │ - PlacesTool (Places API) │    │
 │       │ - CrowdTool (Live Flux)   │   │ - RoutesTool (Routes API) │    │
 │       │ - WeatherTool (Meteo/UV)  │   │ - SolarTool (Solar API)   │    │
 │       └─────────────┬─────────────┘   └─────────────┬─────────────┘    │
 └─────────────────────┼───────────────────────────────┼──────────────────┘
                       │                               │
                       ▼                               ▼
       ┌───────────────────────────────┐ ┌───────────────────────────────┐
       │     Google Cloud Firestore    │ │    Google Maps Platform       │
       │ - Events & Venues Metadata    │ │ - Places API (New)            │
       │ - Real-time Crowd Signals     │ │ - Routes API (ComputeRoutes)  │
       │ - Cache & Historical Metrics  │ │ - Solar & Geocoding API       │
       └───────────────────────────────┘ └───────────────────────────────┘
```

---

## 🧰 Agent 6 大自主調用工具 (Tool Suite)

| 工具名稱 | 說明 | 對應資料來源 / API |
| :--- | :--- | :--- |
| `search_events` | 依據主題、室內冷氣、行政區與關鍵字篩選活動 | Google Cloud Firestore / Event Catalog |
| `check_weather` | 查詢指定座標之即時溫度、體感溫度、降雨與紫外線 (UV) | Maps Weather / Open-Meteo API |
| `check_crowd_density` | 查詢場館即時擁擠指數 (0-100)、人流趨勢與等候時間 | 電信信令與捷運流量模擬模型 / Firestore |
| `get_place_details` | 取得場館評分、評論摘要、營業狀態與無障礙設施 | Google Maps Places API (New) |
| `compute_route` | 計算捷運/步行移動時間與地下街/林蔭遮蔽比例 | Google Maps Routes API (ComputeRoutes) |
| `get_solar_exposure` | 評估日照輻射量與陰影覆蓋率，提供防曬建議 | Google Maps Solar API |

---

## 📂 專案目錄結構 (Directory Tree)

```
SideQuest/
├── SRS.md                              # 軟體需求規格說明書 (IEEE-830 標準)
├── IMPLEMENTATION_PROPOSAL.md          # 完整技術實作提案與架構白皮書
├── plan.md                             # 競賽原始規劃與背景
├── README.md                           # 本文件
├── frontend/                           # Vue 3 + Varlet + Google Maps demo
│   ├── src/App.vue                     # 台北市 hardcode 景點、地圖與推薦面板
│   ├── Dockerfile                      # Cloud Run static frontend image
│   ├── cloudbuild.yaml                 # Cloud Build image pipeline
│   └── nginx.conf                      # SPA fallback 與靜態資產快取
└── backend/
    ├── Dockerfile                      # Cloud Run 多階段建置 Dockerfile
    ├── docker-compose.yml              # 本地容器化啟動配置
    ├── cloudbuild.yaml                 # GCP Cloud Build CI/CD 自動化管線
    ├── deploy.sh                       # 一鍵自動化佈署至 Cloud Run 腳本
    ├── requirements.txt                # Python 套件依賴
    ├── pyproject.toml                  # 專案套件管理配置
    ├── .env.example                    # 環境變數範例檔
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                     # FastAPI 核心入口與生命週期
    │   ├── config.py                   # Pydantic Settings 環境配置
    │   ├── models/                     # Pydantic 資料結構定義
    │   │   ├── event.py                # 活動資料與推薦卡片模型
    │   │   ├── crowd.py                # 人潮熱度與熱力圖點模型
    │   │   ├── weather.py              # 天氣、紫外線與日照模型
    │   │   ├── places.py               # Google Places & Routes 模型
    │   │   └── agent.py                # Agent 對話、思考步驟與請求模型
    │   ├── agent/                      # Agentic 核心
    │   │   ├── gemini_agent.py         # Gemini 2.0 Function Calling & 疏導推論器
    │   │   ├── prompt_templates.py     # Agent System Prompt 定義
    │   │   └── tools/                  # 6 大 Agent 工具實作
    │   │       ├── event_tool.py
    │   │       ├── weather_tool.py
    │   │       ├── crowd_tool.py
    │   │       ├── places_tool.py
    │   │       ├── routes_tool.py
    │   │       └── solar_tool.py
    │   ├── services/                   # 外部服務與資料存取層
    │   │   ├── firestore_service.py    # Firestore 連線與本地優雅降級快取
    │   │   ├── maps_service.py         # Google Maps Platform 介接
    │   │   └── mock_data_seeder.py     # 18+ 筆大台北高擬真活動與場館種子資料
    │   └── api/                        # REST & SSE 路由層
    │       ├── deps.py                 # FastAPI 依賴注入
    │       └── routes/
    │           ├── agent.py            # /api/v1/agent (Chat, Stream, Recommend)
    │           ├── events.py           # /api/v1/events (活動查詢與分類)
    │           ├── crowd.py            # /api/v1/crowd (熱力圖與場館流量)
    │           ├── weather.py          # /api/v1/weather (微氣候與日照)
    │           └── health.py           # /healthz & /readiness (健康檢查)
    └── tests/                          # 完整單元與整合測試
        ├── test_tools.py               # 6 大工具測試
        ├── test_agent.py               # Agent 疏導演算法測試
        └── test_api.py                 # FastAPI 端點整合測試
```

---

## 🚀 快速開始 (Quick Start)

### 1. 本地環境建置與局域網 (LAN) 開發 (推薦使用 Astral `uv`)

```bash
# 1. 進入後端目錄
cd backend

# 2. 使用 uv 一鍵安裝並同步虛擬環境
uv sync

# 3. 配置環境變數
cp .env.example .env
# 可填入 GEMINI_API_KEY 與 GOOGLE_MAPS_API_KEY (留空時自動啟用 High-Fidelity Mock 引擎)

# 4. 啟動支援局域網 (LAN) 之開發伺服器 (綁定 0.0.0.0)
uv run dev
# 或：uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

> 💡 *若使用傳統 pip，亦可執行 `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`。*

### 1.5 前端 SideQuest Demo

前端 demo 使用 Vue 3、Varlet 與 Google Maps JavaScript API。活動資料透過 `EventDataSource` 介面載入，目前的 `CsvEventDataSource` 讀取 `frontend/public/data/taipeidope_events.csv`；Agent 則透過 `AgentService` 介面使用 `MockAgentService`。這一版完全只跑前端，之後可切換 `ApiEventDataSource` 與 `HttpAgentService`，不需要重寫 UI。

```powershell
cd frontend
npm install
$env:VITE_EVENT_SOURCE = 'csv'
$env:VITE_AGENT_SOURCE = 'mock'
$env:VITE_GOOGLE_MAPS_API_KEY = '<your browser-restricted key>'
npm run dev
```

若要預覽未來 backend adapter 的介面，改用 `VITE_EVENT_SOURCE=api` 或 `VITE_AGENT_SOURCE=http`，並設定對應的 `VITE_EVENTS_API_URL` / `VITE_AGENT_API_URL`；目前 demo 不需要 backend 才能操作。

部署 Cloud Run 時，請用 gcloud 取得受限 API key 後透過 Cloud Build substitution 注入，不要把 key 寫進 repository：

```powershell
$gcloud = 'C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$project = 'YOUR_PROJECT_ID'
$keyName = & $gcloud services api-keys list --project=$project --format='value(name)' --filter='displayName:SideQuest Maps Browser Key' | Select-Object -First 1
$mapsKey = & $gcloud services api-keys get-key-string $keyName --project=$project --format='value(keyString)'
& $gcloud builds submit . --config=cloudbuild.yaml --project=$project --substitutions="_MAPS_API_KEY=$mapsKey,_REGION=asia-east1,_REPOSITORY=sidequest"
```

### 2. 測試 API 與互動式文件
- **本機 Swagger UI**：[http://localhost:8080/docs](http://localhost:8080/docs)
- **局域網 (LAN) 存取**：`http://<您的本機IP>:8080/docs`（伺服器啟動時會自動偵測並印出）
- **存活健康檢查**：[http://localhost:8080/healthz](http://localhost:8080/healthz)

### 3. 執行自動化測試 (17 項測試 100% 通過)

```bash
cd backend
uv run pytest -v
```

---

## 📡 API 核心端點說明

### 1. Agent 思考與推薦串流 (SSE Stream)
- **Endpoint**: `POST /api/v1/agent/chat/stream`
- **Request Body**:
```json
{
  "message": "今天下午台北好熱，想找個捷運方便、有冷氣吹的展覽或手作市集，不要人擠人",
  "user_latitude": 25.0330,
  "user_longitude": 121.5654,
  "avoid_crowd_strict": true
}
```
- **SSE Event Stream 回應**:
  - `event: thought` ➔ 即時推送 Agent 思考狀態（例如「正在查詢 UV 與即時人潮」）
  - `event: tool_result` ➔ 回傳各工具執行結果
  - `event: markdown_chunk` ➔ 串流輸出 Markdown 文本
  - `event: recommendation_cards` ➔ 推送結構化活動推薦卡片 JSON

### 2. 地圖人潮熱力圖數據
- **Endpoint**: `GET /api/v1/crowd/heatmap`
- **Response**:
```json
[
  {
    "latitude": 25.0441,
    "longitude": 121.5294,
    "weight": 0.92,
    "venue_name": "華山1914文化創意產業園區 東2館"
  },
  {
    "latitude": 25.0531,
    "longitude": 121.6062,
    "weight": 0.28,
    "venue_name": "POPOP Taipei 瓶蓋工廠台北製造所"
  }
]
```

---

## ☁️ Google Cloud Run 部署指南

### 一鍵自動化佈署
```bash
cd backend
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="asia-east1"

# 執行部署腳本
./deploy.sh
```

### 腳本執行步驟：
1. 自動啟用 Cloud Run、Cloud Build、Artifact Registry、Firestore 等必要 GCP APIs。
2. 建立 Artifact Registry 容器儲存庫。
3. 透過 Google Cloud Build 建置高輕量化 Production Docker 映像檔。
4. 佈署至 Google Cloud Run，設定 `Scale to Zero`（閒置不計費）與 `Concurrency=80`。

---

## 🏆 DevJam 競賽評分標準對應 (Grading Alignment)

- ✅ **技術實現與可行性 (30-35%)**：完整非同步 FastAPI 架構、Pydantic v2 型別嚴謹、具備 SSE 即時串流與 100% 測試覆蓋率。
- ✅ **Google 技術運用與創新性 (25%)**：深度整合 Gemini 2.0 Autonomous Tool Calling、Google Maps (Places/Routes/Solar/Weather) 與 GCP (Cloud Run, Firestore, Cloud Build)。創新人流疏導演算法。
- ✅ **問題針對性與影響力 (20-25%)**：直擊都會假日「怕熱、怕擠、資訊破碎」痛點，助益城市人流智慧分流與小眾藝文經濟。
- ✅ **Demo 展示與技術表達 (15-20%)**：SSE 動態展示 Agent 工具調用軌跡、Swagger UI 互動式端點、精美地圖熱力圖圖層。
- ✅ **雲端架設完整性 (5%)**：提供生產級 Dockerfile、Cloud Build 配置檔與一鍵部署腳本。
