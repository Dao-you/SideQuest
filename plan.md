Project Background
now i am competing hackathon held by Google called Devjam.

here is grading policy

複賽評分標準

技術實現與可行性 ｜30%

Google 技術運用與創新性 ｜25%

問題針對性與影響力                      ｜25%

Demo 展示與技術表達  ｜15%

雲端架設完整性  ｜ 5%

決賽評分標準

技術實現與可行性  ｜35%

市場適配性與技術結合  ｜25%

影響力與落地潛力    ｜20%

Pitch 表現與產品呈現  ｜20%



and this year topic is ”Agent X 智慧城市“

we are on Google Cloud Platfrom Grounp

背景：社群上常見整理周末活動的 IG 帳號，可遇見民眾對於城市裡有什麼活動有高度需求。可以這群人為目標受眾，聚合活動資料來源、群眾聚集程度、氣溫與曝曬情況等，提供民眾一個 Agentic 的資訊整合平台。


參考：
SITCON 2026 對議程做 MCP Server
網路上常有活動整理平台

影響: 
分散人群、減少人流集中之疏運根本原因
提升活動品質，促進消費
讓各種活動有曝光機會
讓民眾可以快速獲得相關建議
竟品
已有的活動平台 (ex. Accupass, Luma)，但本產品的目標反而是幫助活動有更多的引流，可以接入這些網站的資訊進行引流，亦敵亦友
分享活動資訊的社群帳號

輸入資料：
活動資料
人潮聚集資料(如 電信信令、大眾運輸票務資料等)
氣候資料(如 日照資料、氣象資料等)

recommend tech stack：

                  Vue Web
                     │
          Google Maps JavaScript API
                     │
                     ▼
              Cloud Run
          FastAPI + Google ADK
                     │
                     ▼
              Gemini / Vertex AI
                     │
        Agent 自主決定呼叫 Tool
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
 Event Tool      Weather Tool      Crowd Tool
     │               │                │
Firestore      Maps Weather API    Firestore
活動資料         天氣 / UV          人流分數
     │
     ├───────────────┬────────────────┐
     ▼               ▼                ▼
Places Tool      Routes Tool      Solar Tool
Places API       Routes API       Solar API
地點資訊          移動時間          曝曬資訊
     │
     └───────────────┬────────────────┘
                     ▼
              Gemini Ranking
                     │
                     ▼
       「現在最適合你的活動」



Now I'm incharged of Backend and deploy 
Make a implement propasol with SRS