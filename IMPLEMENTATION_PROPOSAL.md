# SideQuest 實作提案與架構白皮書 (Implementation Proposal)
## Google DevJam 2026: Agent X 智慧城市｜GCP 雲端架構與後端實現方案

---

## 1. 提案摘要 (Executive Summary)
**SideQuest** 是一個基於 **Google Cloud Platform (GCP)** 與 **Gemini Agentic AI** 的智慧城市週末探險與活動決策平台。

本提案針對都會區活動資訊碎片化、熱門景點極端擁擠以及夏日高溫曝曬等問題，提出一套以 **Gemini 2.0 / Vertex AI 為大腦**，自主調用 **6 大專用工具 (Event, Weather, Crowd, Places, Routes, Solar)** 的多代理協作系統。透過即時動態感知、多準則決策演算法（Multi-Criteria Decision Making）與**人流智慧疏導（Crowd Dispersal Routing）**，SideQuest 不僅為使用者客製化最佳遊憩動線，更為城市創造「分散過載人潮、扶植小眾藝文聚落」之公共治理效益。

---

## 2. 系統架構設計 (System Architecture)

### 2.1 總體架構圖
```mermaid
flowchart TD
    subgraph ClientLayer ["前端客戶端 (Frontend Layer)"]
        VueApp["Vue 3 + Tailwind Web App"]
        GoogleMapsJS["Google Maps JavaScript API<br/>(熱力圖 / 遮蔭路徑視覺化)"]
    end

    subgraph GCPCloudRun ["GCP Cloud Run (Serverless Backend)"]
        FastAPI["FastAPI App (Python 3.12+ Async)"]
        
        subgraph AgentEngine ["SideQuest Agentic Core"]
            Gemini["Gemini 2.0 Flash / Vertex AI<br/>(Function Calling & Multi-Step Reasoning)"]
            DispersalEngine["Crowd Dispersal & Ranking Engine"]
        end

        subgraph ToolSuite ["Agent Tool Suite"]
            T1["EventTool<br/>(Firestore Catalog)"]
            T2["WeatherTool<br/>(Temp / Rain / UV)"]
            T3["CrowdTool<br/>(Telco & MRT Flux)"]
            T4["PlacesTool<br/>(Google Places API)"]
            T5["RoutesTool<br/>(Google Routes API)"]
            T6["SolarTool<br/>(Google Solar API)"]
        end
    end

    subgraph DataStorage ["GCP Data & API Services"]
        Firestore[("Google Cloud Firestore<br/>Events, Venues, Cache")]
        MapsAPI["Google Maps Platform<br/>(Places, Routes, Solar, Weather)"]
        SecretMgr["GCP Secret Manager"]
    end

    VueApp <-->|REST API & SSE EventStream| FastAPI
    FastAPI <--> Gemini
    Gemini --> ToolSuite
    T1 <--> Firestore
    T2 <--> MapsAPI
    T3 <--> Firestore
    T4 <--> MapsAPI
    T5 <--> MapsAPI
    T6 <--> MapsAPI
    Gemini --> DispersalEngine
    DispersalEngine --> FastAPI
```

---

## 3. Agent 核心決策與工具調用流程 (Agent Decision Graph)

### 3.1 決策工作流程 (Workflow)
```mermaid
sequenceDiagram
    autonumber
    actor User as 使用者 / 前端 (Vue)
    participant API as Cloud Run (FastAPI)
    participant Agent as Gemini 2.0 Agent
    participant Tools as Tool Suite (Firestore / Maps)
    participant DB as Firestore & Google APIs

    User->>API: 發送自然語言請求 (ex. "今天下午信義區好熱，想看展喝咖啡，不要人擠人")
    API->>Agent: 注入 System Prompt + 工具元數據定義 (Tools Schema)
    
    rect rgb(240, 248, 255)
    Note over Agent: 第一階段：意圖解析與初步檢索
    Agent->>API: 觸發 Tool Call: EventTool(category="art,cafe", area="Xinyi")
    API->>Tools: 執行 EventTool
    Tools->>DB: 檢索候選活動 (5-8 項)
    DB-->>Tools: 回傳候選活動資料
    Tools-->>Agent: 回傳結構化活動候選清單
    end

    rect rgb(255, 250, 240)
    Note over Agent: 第二階段：環境情境感知 (氣候、日照、即時人潮)
    Agent->>API: 並行呼叫 WeatherTool, CrowdTool, SolarTool
    API->>Tools: 批次查詢目標地點環境指標
    Tools->>DB: 取得即時熱度 (Crowd Score) 與 UV/日照指數
    DB-->>Tools: 回傳數據 (如松菸: 熱度 88, 華山: 92, 南港瓶蓋工廠: 28)
    Tools-->>Agent: 回傳微環境感知矩陣
    end

    rect rgb(240, 255, 240)
    Note over Agent: 第三階段：人流疏導與路徑最優化
    Agent->>Agent: 評估人流過載懲罰與室內遮蔭權重
    Agent->>API: 呼叫 RoutesTool (計算捷運/遮蔭移動路徑)
    API->>Tools: 查詢 Google Routes API (ComputeRoutes)
    Tools-->>Agent: 回傳移動時間與最佳路徑
    end

    Agent-->>API: 產出結構化推薦 (含精確理由、人潮預警、陰涼路線)
    API-->>User: 以 SSE 串流即時輸出思考過程 + 最終推薦卡片
```

---

## 4. 人流疏導與多準則評估演算法 (Crowd Dispersal Scoring Algorithm)

為了具體達成「分散人群、減少擁擠、提升遊憩品質」之目標，系統在 Agent 決策鏈中引入**動態加權評分公式**：

$$\text{TotalScore}(E_i) = S_{\text{match}}(E_i) \times w_{\text{match}} + (100 - C(E_i)) \times w_{\text{crowd}} + W_{\text{comfort}}(E_i) \times w_{\text{weather}} + A(E_i) \times w_{\text{access}}$$

其中：
- $S_{\text{match}}$: 使用者興趣與活動主題契合度 (0~100)
- $C(E_i)$: 即時人潮擁擠指數 (0~100)
- $W_{\text{comfort}}$: 微氣候舒適指數（若 UV 指數高但為室內活動則加分；若為烈日下戶外則扣分）
- $A(E_i)$: 交通易達性（距離捷運站步程與陰涼路徑覆蓋率）
- **Crowd Penalty (過載懲罰)**：當 $C(E_i) \ge 80$，系統主動降低其推薦排序，並在對話中提示：「*華山目前人潮指數高達 90，建議您可前往 10 分鐘捷運車程外的南港瓶蓋工廠手作展，人潮指數僅 28，享有更舒適的看展空間！*」

---

## 5. API 介面規格設計 (REST & SSE Specification)

### 5.1 Agent 互動端點
- `POST /api/v1/agent/chat/stream` (SSE Server-Sent Events)
  - 串流輸出 Agent 的思考、工具調用紀錄（Tool Invocation Traces）以及最終回答，提供前端極致流暢的 UI 體驗。
- `POST /api/v1/agent/recommend`
  - 快速單次呼叫，直接回傳多準則排序後的精選活動卡片結構化 JSON。

### 5.2 城市活動與地圖圖層端點
- `GET /api/v1/events`：檢索活動清單（支援分類、關鍵字、地理圍欄、室內/室外篩選）。
- `GET /api/v1/events/{event_id}`：活動詳細資訊（包含 Google Places 評價、圖片、即時人流）。
- `GET /api/v1/crowd/heatmap`：提供前端 Google Maps 渲染人潮熱力圖所需之經緯度權重點。
- `GET /api/v1/weather/current`：指定經緯度之微氣候、降雨機率與 UV 指數。

### 5.3 系統維運端點
- `GET /healthz`：Kubernetes / Cloud Run 存活探針 (Liveness probe)。
- `GET /readiness`：確認 Firestore、GCP 服務連線狀態 (Readiness probe)。

---

## 6. 資料庫模型設計 (Firestore Data Schema)

### 6.1 `events` Collection
```json
{
  "id": "event_taipei_art_01",
  "title": "2026 數位藝術未來特展",
  "category": "art",
  "venue_name": "松山文創園區 2號倉庫",
  "location": {
    "latitude": 25.0438,
    "longitude": 121.5607,
    "address": "台北市信義區光復南路133號"
  },
  "is_indoor": true,
  "ac_available": true,
  "start_time": "2026-08-20T10:00:00Z",
  "end_time": "2026-08-23T18:00:00Z",
  "tags": ["展覽", "科技藝術", "室內吹冷氣", "情侶約會"],
  "price_type": "free",
  "capacity": 300,
  "rating": 4.7,
  "source_url": "https://accupass.com/event/demo"
}
```

### 6.2 `venues_live` Collection (即時狀態快取)
```json
{
  "venue_id": "venue_songshan",
  "venue_name": "松山文創園區",
  "crowd_score": 78,
  "crowd_level": "HIGH",
  "uv_index": 7.5,
  "temperature_c": 33.2,
  "last_updated": "2026-08-17T16:00:00Z"
}
```

---

## 7. 雲端部署架構 (GCP Cloud Run Deployment)

```
                    ┌─────────────────────────┐
                    │      Git Repository     │
                    └────────────┬────────────┘
                                 │ git push
                                 ▼
                    ┌─────────────────────────┐
                    │    Google Cloud Build   │
                    │  - Docker build & test  │
                    │  - Push to Artifact Reg │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ GCP Artifact Registry   │
                    │ (gcr.io / asia-east1)   │
                    └────────────┬────────────┘
                                 │ deploy
                                 ▼
                    ┌─────────────────────────┐
                    │    Google Cloud Run     │
                    │ - Min instances: 0      │
                    │ - Max instances: 10     │
                    │ - Concurrency: 80       │
                    │ - Auto HTTPS (SSL)      │
                    │ - Secret Manager Bound  │
                    └─────────────────────────┘
```

### 7.1 Cloud Run 特性亮點
1. **極致彈性 (Scale to Zero)**：在無請求時縮容至 0 實例，節省運算成本。
2. **高併發 (Concurrency 80+)**：Python Async FastAPI 在單一 Container 即可處理高達 80 個並行請求。
3. **無縫整合 Secret Manager**：直接將 `GEMINI_API_KEY` 與 `MAPS_API_KEY` 掛載為環境變數，兼顧最高安全性。

---

## 8. 競賽致勝策略 (Hackathon Winning Strategy)

1. **技術實現與可行性 (30-35%)**：
   - 完整、乾淨、型別嚴謹的 Python 3.12+ FastAPI 非同步架構。
   - 優雅降級設計：具備完整 Realistic Mock Data，斷網或無金鑰環境仍能流暢展示。
2. **Google 技術運用與創新性 (25%)**：
   - 充分發揮 Gemini Function Calling 之自主決策能力。
   - 深度串聯 Google Maps Places, Routes, Solar, Weather 與 Cloud Run、Firestore。
3. **問題針對性與公共影響力 (20-25%)**：
   - 直擊都會週末「人擠人、曬傷、展覽踩雷」痛點。
   - 透過「人流疏導推薦演算法」協助智慧城市交通與商圈均衡發展。
4. **Demo 展示性 (15-20%)**：
   - 透過 SSE 串流將 Agent 思考每一步（如 "正在調用 Google Solar API 評估曝曬指數..."）動態可視化呈現，極具科技感與說服力。
