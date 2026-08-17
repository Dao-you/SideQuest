"""Routes API endpoint and visual interactive testing tool."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from app.api.deps import get_places_service_dep
from app.models.places import RouteComfort, RouteComputeRequest
from app.services.interfaces import PlacesServiceInterface

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.post("/compute", response_model=RouteComfort)
async def compute_route(
    request: RouteComputeRequest,
    maps_service: PlacesServiceInterface = Depends(get_places_service_dep),
) -> RouteComfort:
    """Compute transit routing and thermal comfort analysis between origin and destination."""
    dest_name = request.destination_name or "目標活動場館"
    return await maps_service.compute_route(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lng,
        dest_lat=request.destination_lat,
        dest_lng=request.destination_lng,
        dest_name=dest_name,
        prioritize_shade=request.prioritize_shade,
    )


@router.get("/visualize", response_class=HTMLResponse)
async def visualize_routes() -> str:
    """Interactive visual testing tool for Google Routes API & Thermal Comfort Routing."""
    html_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SideQuest | Google Routes & Thermal Comfort Visual Tester</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    :root {
      --bg: #0f172a;
      --card: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --accent: #10b981;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background: var(--card);
      border-bottom: 1px solid var(--border);
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    header h1 {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .badge {
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .main-container {
      display: flex;
      flex: 1;
      height: calc(100vh - 58px);
      overflow: hidden;
    }
    #map {
      flex: 1;
      height: 100%;
      background: #020617;
    }
    .sidebar {
      width: 440px;
      background: var(--card);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 20px;
      gap: 16px;
    }
    .card {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
    }
    .card h3 {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .form-group {
      margin-bottom: 10px;
    }
    label {
      display: block;
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    select, input {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      color: var(--text);
      font-size: 0.85rem;
      outline: none;
    }
    select:focus, input:focus {
      border-color: var(--primary);
    }
    .btn {
      width: 100%;
      background: #0284c7;
      color: white;
      border: none;
      border-radius: 6px;
      padding: 10px;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background 0.2s;
    }
    .btn:hover { background: #0369a1; }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .metric-box {
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px;
      text-align: center;
    }
    .metric-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--primary);
      margin-top: 2px;
    }
    .metric-label {
      font-size: 0.7rem;
      color: var(--text-muted);
    }
    .steps-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 6px;
    }
    .step-item {
      display: flex;
      gap: 10px;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 0.82rem;
      align-items: center;
    }
    .step-icon {
      font-size: 1.1rem;
      min-width: 24px;
      text-align: center;
    }
    .step-content { flex: 1; }
    .step-meta {
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .shaded-tag {
      font-size: 0.65rem;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: inline-block;
      margin-top: 3px;
    }
    pre {
      background: #020617;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px;
      font-size: 0.75rem;
      color: #cbd5e1;
      max-height: 160px;
      overflow: auto;
    }
  </style>
</head>
<body>
  <header>
    <h1>🗺️ SideQuest 智慧路徑與日照遮蔭可視化測試工具</h1>
    <div style="display:flex; gap:8px;">
      <span class="badge">Google Routes API (New)</span>
      <span class="badge">Thermal Comfort Scoring</span>
    </div>
  </header>

  <div class="main-container">
    <div id="map"></div>
    <div class="sidebar">
      <div class="card">
        <h3>📍 測試路徑預設場景 (Presets)</h3>
        <div class="form-group">
          <label>快速選擇經典探索路徑</label>
          <select id="presetSelect" onchange="loadPreset()">
            <option value="p1">1. 華山1914 ➡️ 瓶蓋工廠台北製造所 (南港捷運地下連通)</option>
            <option value="p2">2. 台北車站 ➡️ C-LAB 臺灣當代文化實驗場 (大安藝文避暑)</option>
            <option value="p3">3. 市政府站 ➡️ 松山文創園區 (林蔭步道)</option>
            <option value="p4">4. 圓山花博 ➡️ 中山赤峰街文創聚落 (捷運紅線)</option>
          </select>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <div>
            <label>出發地 (Origin)</label>
            <input type="text" id="originName" value="華山1914文化創意產業園區" readonly />
          </div>
          <div>
            <label>目的地 (Destination)</label>
            <input type="text" id="destName" value="POPOP Taipei 瓶蓋工廠" readonly />
          </div>
        </div>

        <div style="margin-top:10px; display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="prioritizeShade" checked style="width:auto; cursor:pointer;" />
          <label for="prioritizeShade" style="margin:0; cursor:pointer; color:var(--text); font-size:0.8rem;">
            🌲 優先規劃地下街與林蔭遮蔽路徑 (Shade Priority)
          </label>
        </div>

        <button class="btn" style="margin-top: 12px;" onclick="calculateRoute()">
          ⚡ 計算 Google Routes & 熱舒適評估
        </button>
      </div>

      <div class="card">
        <h3>📊 熱舒適與路徑指標 (Metrics)</h3>
        <div class="metrics-grid">
          <div class="metric-box">
            <div class="metric-label">預估交通時間</div>
            <div class="metric-value" id="valDuration">-- 分鐘</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">地下/遮蔭覆蓋率</div>
            <div class="metric-value" id="valShade" style="color:var(--accent);">-- %</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">熱舒適評分</div>
            <div class="metric-value" id="valScore" style="color:#f59e0b;">-- / 100</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">總移動距離</div>
            <div class="metric-value" id="valDist">-- 公尺</div>
          </div>
        </div>
        <div id="routeAdvice" style="font-size:0.8rem; color:var(--text-muted); margin-top:10px; line-height:1.4;">
          請點選計算以取得即時建議。
        </div>
      </div>

      <div class="card">
        <h3>🚶 分段導航與遮蔭細節 (Step by Step)</h3>
        <div id="stepsList" class="steps-list">
          <div style="font-size:0.8rem; color:var(--text-muted); text-align:center; padding:10px;">尚未計算路徑</div>
        </div>
      </div>

      <div class="card">
        <h3>🔍 API 原始 JSON 檢視 (Raw JSON)</h3>
        <pre id="jsonViewer">// 點擊計算後將顯示完整的 RouteComfort 回傳結構</pre>
      </div>
    </div>
  </div>

  <script>
    const presets = {
      p1: {
        originName: "華山1914文創園區",
        originLat: 25.0441, originLng: 121.5294,
        destName: "POPOP Taipei 瓶蓋工廠",
        destLat: 25.0528, destLng: 121.6067
      },
      p2: {
        originName: "台北車站",
        originLat: 25.0478, originLng: 121.5170,
        destName: "C-LAB 臺灣當代文化實驗場",
        destLat: 25.0402, destLng: 121.5392
      },
      p3: {
        originName: "市政府站 (BL18)",
        originLat: 25.0411, originLng: 121.5652,
        destName: "松山文創園區",
        destLat: 25.0438, destLng: 121.5606
      },
      p4: {
        originName: "圓山花博爭豔館",
        originLat: 25.0713, originLng: 121.5201,
        destName: "中山赤峰街文創聚落",
        destLat: 25.0552, destLng: 121.5192
      }
    };

    let map = L.map('map').setView([25.0478, 121.5450], 13);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    }).addTo(map);

    let originMarker = null;
    let destMarker = null;
    let routePolyline = null;
    let currentOrigin = { lat: 25.0441, lng: 121.5294, name: "華山1914文創園區" };
    let currentDest = { lat: 25.0528, lng: 121.6067, name: "POPOP Taipei 瓶蓋工廠" };

    function loadPreset() {
      const pKey = document.getElementById('presetSelect').value;
      const p = presets[pKey];
      currentOrigin = { lat: p.originLat, lng: p.originLng, name: p.originName };
      currentDest = { lat: p.destLat, lng: p.destLng, name: p.destName };
      document.getElementById('originName').value = p.originName;
      document.getElementById('destName').value = p.destName;
      updateMarkers();
      calculateRoute();
    }

    function updateMarkers() {
      if (originMarker) map.removeLayer(originMarker);
      if (destMarker) map.removeLayer(destMarker);

      originMarker = L.circleMarker([currentOrigin.lat, currentOrigin.lng], {
        radius: 9, fillColor: "#38bdf8", color: "#ffffff", weight: 2, fillOpacity: 0.9
      }).addTo(map).bindPopup("<b>出發地:</b> " + currentOrigin.name);

      destMarker = L.circleMarker([currentDest.lat, currentDest.lng], {
        radius: 9, fillColor: "#10b981", color: "#ffffff", weight: 2, fillOpacity: 0.9
      }).addTo(map).bindPopup("<b>目的地:</b> " + currentDest.name);

      const group = new L.featureGroup([originMarker, destMarker]);
      map.fitBounds(group.getBounds().pad(0.3));
    }

    async function calculateRoute() {
      const prioritizeShade = document.getElementById('prioritizeShade').checked;
      const payload = {
        origin_lat: currentOrigin.lat,
        origin_lng: currentOrigin.lng,
        destination_lat: currentDest.lat,
        destination_lng: currentDest.lng,
        destination_name: currentDest.name,
        prioritize_shade: prioritizeShade,
        travel_mode: "TRANSIT"
      };

      try {
        const res = await fetch('/api/v1/routes/compute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        renderResult(data);
      } catch (err) {
        console.error("Route calculation error:", err);
      }
    }

    function renderResult(data) {
      document.getElementById('valDuration').textContent = data.total_duration_minutes + " 分鐘";
      document.getElementById('valShade').textContent = data.underground_or_shaded_percentage + " %";
      document.getElementById('valScore').textContent = data.comfort_score + " 分";
      document.getElementById('valDist').textContent = data.total_distance_meters + " 公尺";
      document.getElementById('routeAdvice').textContent = data.route_advice;
      document.getElementById('jsonViewer').textContent = JSON.stringify(data, null, 2);

      const stepsContainer = document.getElementById('stepsList');
      stepsContainer.innerHTML = '';

      if (data.segments && data.segments.length > 0) {
        data.segments.forEach((s, idx) => {
          let icon = '🚶';
          if (s.mode === 'SUBWAY') icon = '🚇';
          if (s.mode === 'BUS') icon = '🚌';
          if (s.mode === 'UNDERGROUND_WALK') icon = '🏬';

          const item = document.createElement('div');
          item.className = 'step-item';
          item.innerHTML = `
            <div class="step-icon">${icon}</div>
            <div class="step-content">
              <div><b>Step ${idx + 1}:</b> ${s.instruction}</div>
              <div class="step-meta">時間: ${s.duration_minutes} 分鐘 | 距離: ${s.distance_meters} 公尺</div>
              ${s.is_shaded_or_underground ? '<span class="shaded-tag">🛡️ 地下/遮蔭防曬路徑</span>' : ''}
            </div>
          `;
          stepsContainer.appendChild(item);
        });
      }

      // Draw route on map
      if (routePolyline) map.removeLayer(routePolyline);
      const latlngs = [
        [currentOrigin.lat, currentOrigin.lng],
        [(currentOrigin.lat + currentDest.lat)/2 + 0.002, (currentOrigin.lng + currentDest.lng)/2],
        [currentDest.lat, currentDest.lng]
      ];
      routePolyline = L.polyline(latlngs, {
        color: '#38bdf8',
        weight: 5,
        opacity: 0.8,
        dashArray: '8, 8'
      }).addTo(map);
    }

    // Initial load
    updateMarkers();
    calculateRoute();
  </script>
</body>
</html>
"""
    return html_content
