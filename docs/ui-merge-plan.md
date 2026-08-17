# UI 改善 Merge 計畫

## 目前狀態

- UI 分支：`ui/visual-polish`
- 基線：`main` / `e0db3b2`
- 本分支 commits：
  - `3cc0076 docs(ui): audit visual polish opportunities`
  - `538d7b6 fix(frontend): polish responsive activity UI`
- 驗證：`npm test` 9/9、`npm run build`、`git diff --check` 通過
- Cloud Run 測試副本：已部署至 `sidequest-demo-ui-polish`
- 測試網址：<https://sidequest-demo-ui-polish-cjpexdy77a-de.a.run.app>
- 測試 image：`frontend-ui-polish`
- 地圖修正驗證：Cloud Build `7041d8b4-7919-4f9a-8b46-fdff6f2c8a0f` 成功，revision `sidequest-demo-ui-polish-00002-9vb` 已載入 Google Maps 與活動標記

## 建議合併流程

1. 等 main 的當前功能提交告一段落，先更新本機 main：

   ```powershell
   git switch main
   git pull --ff-only origin main
   ```

2. 將最新 main 合入 UI 分支，不直接覆蓋 main：

   ```powershell
   git switch ui/visual-polish
   git merge --no-ff main
   npm test --prefix frontend
   npm run build --prefix frontend
   git diff --check
   ```

3. 若只有 `frontend/src/App.vue` 或 `frontend/src/styles.css` 衝突，優先保留新功能的資料/事件處理，再把本分支的 UI 規則重新套回去。重點規則包括：

   - 首頁與清單不顯示 PRD、Backend API、Demo Login 等內部標記。
   - `.bottom-sheet` 使用 `--sheet-collapsed-height`，詳情開啟時展開，返回清單時恢復半高。
   - 主要按鈕、icon button、filter、route preference 保留一致的 40–44px 觸控尺寸與 focus ring。
   - 不讓 emoji 作為主要按鈕幾何或語意的唯一來源。
   - 390px 行動版的地圖錯誤提示、地圖控制、bottom sheet、bottom nav 不可互相遮擋。

4. 在 UI 回歸通過後，才合回 main：

   ```powershell
   git switch main
   git merge --no-ff ui/visual-polish
   npm test --prefix frontend
   npm run build --prefix frontend
   ```

5. 若要部署測試副本，使用獨立 Cloud Run service，不使用預設的 `sidequest-demo`：

   ```powershell
   $env:GCP_PROJECT_ID = 'devjam26aug17tpe-1290'
   $env:GCP_REGION = 'asia-east1'
   $env:SERVICE_NAME = 'sidequest-demo-ui-polish'
   bash deploy.sh
   ```

   部署前需先完成 gcloud 認證。此 UI 分支沒有新增或變更後端 API，因此不需要 Swagger 更新。

## Main 新功能通病檢查清單

目前已檢查 main 內的活動推薦卡、日照情境、路線偏好、多模式交通卡、地圖浮動控制、行動版導覽與活動詳情。後續每次 main 加入前端功能，合併前重跑：

- 桌面預設視窗：檢查標題、主要 CTA、卡片三欄、詳情四個動作是否對齊。
- 390 × 844：檢查抽屜高度、底部導覽、地圖控制、長標題與長費用是否溢出。
- 文案掃描：不要把 PRD、Backend、Mock、MVP、內部資料源名稱直接當主要 UI 文案。
- 元件掃描：按鈕需有清楚文字或 aria-label、最小觸控區、focus-visible 狀態；可點擊的卡片需可用鍵盤操作。
- 空間掃描：提示只保留能幫助決策的內容；工程狀態改成使用者可理解的載入/錯誤訊息。
- 驗證命令：`npm test --prefix frontend`、`npm run build --prefix frontend`、`git diff --check`。
