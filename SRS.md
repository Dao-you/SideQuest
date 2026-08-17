# 軟體需求規格說明書 (Software Requirements Specification, SRS)
## 專案名稱：SideQuest (智慧城市 Agentic 活動與人潮疏導決策系統)
**競賽：Google DevJam 2026｜組別：Google Cloud Platform (GCP)｜主題：Agent X 智慧城市**

---

## 1. 引言 (Introduction)

### 1.1 目的 (Purpose)
本規格書旨在詳細定義 **SideQuest** 智慧城市 Agentic 推薦與人流疏導後端系統之功能需求、非功能需求、架構設計、Google 技術整合標準與雲端佈署方案。本專案為參加 Google DevJam「Agent X 智慧城市」競賽所設計，專注於解決都市週末活動資訊破碎、熱門商圈極度擁擠、酷暑高溫曝曬與小眾藝文活動曝光不足之核心痛點。

### 1.2 產品願景與背景 (Product Vision & Background)
在現代都會生活（如大台北生活圈），民眾於週末尋求休閒活動時常面臨四大困境：
1. **資訊破碎且被動**：活動資訊散落於社群媒體（Instagram 整理帳號）、售票平台（Accupass、Klook）及政府開放資料，缺乏整合且無法根據當下即時情境動態調整。
2. **人潮過度集中**：少數熱門景點（如華山、松菸、信義商圈）在尖峰時段人滿為患，交通擁塞且降低遊憩體驗。
3. **極端氣候與高溫曝曬**：夏季高溫與高紫外線（UV）指數使戶外活動容易引發熱傷害，民眾難以及時根據即時微氣候與日照情況切換室內/林蔭方案。
4. **小眾/非熱門活動曝光不足**：中小型展覽或隱藏景點缺乏推廣資源，無法被有相應偏好的市民發現。

**SideQuest** 結合 **Google Gemini / Vertex AI**、**Google Maps Platform (Places, Routes, Solar, Weather)**、**Google Cloud Run** 與 **Firestore**，打造具備自主決策與工具調用（Function Calling / Tool Calling）能力的智慧城市 Agent。Agent 不僅推薦「你想去的活動」，更推薦「**現在最適合你、最不擁擠、氣候最適宜**」的活動路線，達成**民眾獲取最佳體驗**與**城市智慧疏導人流**之雙贏目標。

### 1.3 術語與縮寫定義 (Definitions & Acronyms)
| 術語 | 說明 |
| :--- | :--- |
| **Agent / Agentic System** | 具備自主感知情境、規劃行動路徑、調用外部工具並綜合評估產出決策之智慧代理人。 |
| **Tool Calling / Function Calling** | Gemini 模型依據使用者意圖主動產生結構化參數以呼叫後端定義之 API 工具。 |
| **Crowd Heat Score (人潮指數)** | 0 ~ 100 之正規化指數，綜合電信信令密度、捷運進出站流量與景點容留率計算所得。 |
| **Solar / Shade Comfort Index** | 依據日照輻射量、遮蔽度與紫外線指數綜合計算之環境舒適度指標。 |
| **Crowd Dispersal Routing** | 人流疏散演算法，主動對人潮過載區域進行降權，並獎勵具備相近體驗之低負載活動/路線。 |
| **GCP** | Google Cloud Platform，包含 Cloud Run, Firestore, Secret Manager, Cloud Build 等。 |

---

## 2. 總體描述 (Overall Description)

### 2.1 產品架構總覽 (Product Architecture Overview)
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

### 2.2 使用者角色 (User Personas)
1. **都會探險者 (Weekend Explorer - Persona A)**:
   - 痛點：週六下午想出門喝咖啡或看展，討厭排隊人擠人，容易因天氣炎熱中暑放棄出門。
   - 需求：一鍵取得「步行15分鐘內、有冷氣/遮蔭、當前不擁擠、氣氛佳」的活動方案。
2. **親子家庭 (Family Adventurer - Persona B)**:
   - 痛點：推嬰兒車需要無障礙環境、強烈要求避開烈日曝曬與極度擁塞場所。
   - 需求：戶外公園與室內場館兼具之低人潮舒適休閒提案。
3. **城市活動主辦方與治理者 (City Planner / Event Host - Persona C)**:
   - 痛點：中小型活動難以與大型商業活動競爭人流，熱門區域周邊交通經常癱瘓。
   - 需求：透過 Agent 智慧分流獲得精準受眾引流，促進城市整體商圈均衡消費。

---

## 3. 功能需求規格 (Functional Requirements)

### 3.1 模組一：Agent 核心與自主工具調用系統 (Agent Core & Tool Orchestration)
- **FR-1.1 自然語言意圖理解**：支援多語言（繁體中文、英文）自然語言查詢，能抽取出時間、地點、興趣標籤（咖啡、展覽、親子、戶外、手作）、伴侶情境（單人、情侶、家庭）與環境限制（怕熱、怕擠、搭捷運）。
- **FR-1.2 自主工具調用 (Tool Calling)**：
  - Agent 具備至少 6 個獨立工具之 Function Calling 描述定義。
  - Agent 能根據使用者查詢主動發起單次或多輪並行工具調用（例如先查活動 -> 同步查詢各活動地點當前人潮與紫外線指數 -> 規劃捷運遮蔭路徑）。
- **FR-1.3 多準則智慧排序 (Multi-Criteria Smart Ranking & Dispersal)**：
  - 綜合評分公式：
    $$\text{Score} = w_1 \cdot \text{Match} + w_2 \cdot (100 - \text{CrowdScore}) + w_3 \cdot \text{WeatherComfort} + w_4 \cdot \text{Accessibility}$$
  - 當特定活動之 `CrowdScore > 80` 時，觸發「人流疏導懲罰（Crowd Penalty）」，主動推薦 1-2 個距離在 1.5km 內但人潮指數低於 40 之「隱藏版替代方案 (Hidden Gem)」。
- **FR-1.4 SSE 串流式即時推論 (Server-Sent Events Streaming)**：
  - 後端提供 `/api/v1/agent/chat/stream`，將 Agent 的思考過程、所調用的工具（如 `Tool: WeatherTool (UV: 8, Temp: 32C)`）、工具回傳結果與最終生成的 Markdown 回應以事件流即時推送至前端。

### 3.2 模組二：城市情境感知工具集 (City Context Sensing Tools)
- **FR-2.1 EventTool (活動感知工具)**：
  - 支援依類別（art, music, food, outdoor, tech, family）、室內/室外屬性、預算、時間區間進行篩選。
  - 支援地理圍欄半徑搜尋（預設 5km 內）。
- **FR-2.2 WeatherTool (微氣候與紫外線工具)**：
  - 提供目標經緯度之即時溫度、降雨機率、相對濕度與紫外線指數（UV Index）。
  - 若 `UV Index >= 6` 或 `Rain Probability >= 60%`，主動提示室內或陰涼替代建議。
- **FR-2.3 CrowdTool (即時人潮熱度與疏散工具)**：
  - 模擬/整合電信基地台信令與捷運站流量指數（0-100）。
  - 提供即時熱度等級：`LOW (<35)`、`MODERATE (35-70)`、`HIGH (>70)`、`OVERLOADED (>85)`。
  - 提供人流回報與預測趨勢分析。
- **FR-2.4 PlacesTool (Google Places API New 整合)**：
  - 取得目標活動地點之地點評分、評論摘要、營業狀態、地址與實景圖片參照。
- **FR-2.5 RoutesTool (Google Routes API 整合)**：
  - 計算使用者位置至活動地點之多運具移動時間（步行、大眾運輸、開車）。
  - 評估路線舒適度（例如捷運地下街步行比例 vs 戶外大太陽步行比例）。
- **FR-2.6 SolarTool (Google Solar API / 遮蔽日照工具)**：
  - 提供目標座標區域之日照強度與陰影遮蔽建議，避免使用者曝曬於極端日照中。

### 3.3 模組三：活動與地圖圖層管理 (Events & Geo Layer Services)
- **FR-3.1 活動查詢與檢索 API (`GET /api/v1/events`)**：支援分頁、分類、地理位置搜尋。
- **FR-3.2 人潮熱力圖層 API (`GET /api/v1/crowd/heatmap`)**：提供地圖前端繪製熱力圖所需之 GeoJSON / 座標權重點資料。
- **FR-3.3 景點推薦清單 API (`POST /api/v1/agent/recommend`)**：提供快速單次呼叫之推薦結果 JSON。

---

## 4. 非功能需求規格 (Non-Functional Requirements)

### 4.1 效能與可擴展性 (Performance & Scalability)
- **NFR-1.1 API 響應時間**：一般查詢 API 延遲 $\le 150\text{ms}$；Agent 推論首次 Token 串流輸出（Time to First Token）$\le 800\text{ms}$。
- **NFR-1.2 彈性擴展 (Auto-scaling)**：基於 Google Cloud Run，支援 $0 \to N$ 自動水平擴展，無流量時 Scale-to-Zero 節省成本，尖峰時期可承載 500+ QPS。
- **NFR-1.3 非同步與連線池化 (Async I/O & Connection Pooling)**：全面採用 Python `asyncio`、`httpx.AsyncClient` 與非同步 Firestore Client，避免阻塞執行緒。

### 4.2 可靠性與容錯 (Reliability & Resilience)
- **NFR-2.1 Graceful Degradation (優雅降級)**：當未配置外部 Google API Key 或網路異常時，系統自動啟用內建 High-Fidelity Mock Engine，確保 Demo 與評審評分過程 100% 不中斷。
- **NFR-2.2 健康檢查**：提供 `/healthz` 與 `/readiness` 端點供 Cloud Run 與 Load Balancer 進行存活探測。

### 4.3 安全性 (Security)
- **NFR-3.1 憑證管理**：所有 API Key（Gemini, Google Maps）皆透過環境變數或 Google Secret Manager 注入，嚴禁硬編碼於程式碼中。
- **NFR-3.2 跨來源資源共用 (CORS)**：配置可自訂的 CORS Policy，允許前端 Vue 應用跨域呼叫。

---

## 5. Google 技術深度整合清單 (Google Tech Alignment)

| Google 技術項目 | 於本專案中的具體角色與價值 |
| :--- | :--- |
| **Gemini 2.0 Flash / Pro (Vertex AI)** | 系統大腦：負責自然語言理解、自主工具呼叫（Tool Calling）與多準則人流疏導決策。 |
| **Google Cloud Run** | 無伺服器運算平台：託管高效能 FastAPI 後端，具備快速冷啟動與自動彈性擴縮能力。 |
| **Google Cloud Firestore** | NoSQL 文件資料庫：儲存活動結構化資料、地點元數據與人潮動態評分。 |
| **Google Maps Places API (New)** | 空間資訊：提供即時地點評分、營業時間、實景照片與室內/室外分類。 |
| **Google Maps Routes API** | 路網運算：計算大眾運輸與步行時間，結合陰涼路徑評估。 |
| **Google Maps Solar / Weather** | 微環境感知：提供日照分析、紫外線指數與降雨預警，引導民眾抗曝曬。 |
| **Google Cloud Build & Artifact Registry** | CI/CD 流程：全自動建置 Container Image 並安全佈署至 Cloud Run。 |

---

## 6. 競賽評分標準映射 (Hackathon Rubric Alignment)

```
┌───────────────────────────────────┬─────────┬────────────────────────────────────────────────────────┐
│ 評分面向                           │ 佔比    │ 本專案具體落地與亮點                                     │
├───────────────────────────────────┼─────────┼────────────────────────────────────────────────────────┤
│ 1. 技術實現與可行性 (Feasibility)  │ 30%-35% │ - 完整非同步 FastAPI 架構，模組化 Tool 架構              │
│                                   │         │ - 具備 SSE 串流輸出與 Graceful Degradation               │
│                                   │         │ - 具備單元與整合測試覆蓋率                               │
├───────────────────────────────────┼─────────┼────────────────────────────────────────────────────────┤
│ 2. Google 技術運用與創新性        │ 25%     │ - 深度結合 Gemini Tool Calling + Maps (Places/Routes/  │
│    (Google Tech & Innovation)     │         │   Solar/Weather) + Cloud Run + Firestore 完整生態系    │
│                                   │         │ - 創新人潮疏導 (Crowd Dispersal) 與 抗日照推薦機制     │
├───────────────────────────────────┼─────────┼────────────────────────────────────────────────────────┤
│ 3. 問題針對性與影響力 (Impact)     │ 20%-25% │ - 直擊市民「假日何處去、怕熱、怕擠」之真實生活痛點       │
│                                   │         │ - 為城市創造「分散擁擠人流、賦能小眾藝文經濟」之公共價值 │
├───────────────────────────────────┼─────────┼────────────────────────────────────────────────────────┤
│ 4. Demo 展示與技術表達 (Demo)      │ 15%-20% │ - SSE 串流展示 Agent 思考步驟（調用了哪些工具、即時數據） │
│                                   │         │ - 豐富的即時地圖熱力圖與互動式 Swagger API 文件         │
├───────────────────────────────────┼─────────┼────────────────────────────────────────────────────────┤
│ 5. 雲端架設完整性 (Cloud Deploy)  │ 5%      │ - 包含 Dockerfile、Cloud Build 配置、一鍵部署腳本        │
│                                   │         │ - 100% 雲端原生無伺服器 (Serverless) 架構               │
└───────────────────────────────────┴─────────┴────────────────────────────────────────────────────────┘
```
