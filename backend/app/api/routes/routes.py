"""Routes API endpoint and Google Maps interactive visual testing tool."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from app.api.deps import get_places_service_dep
from app.config import settings
from app.models.places import RouteComfort, RouteComputeRequest
from app.services.interfaces import PlacesServiceInterface

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.post("/compute", response_model=RouteComfort, summary="計算多元偏好之大眾運輸與遮陽抗熱路徑")
async def compute_route(
    request: RouteComputeRequest,
    maps_service: PlacesServiceInterface = Depends(get_places_service_dep),
) -> RouteComfort:
    """
    計算起點至目的地的大眾運輸與多運具出行方案，並評估遮陽抗熱舒適度與無障礙可行性。

    支援路線偏好（Route Preferences）：
    - `fastest` (經典/最快速)
    - `wheelchair` (無障礙/推車/大件行李)
    - `more_bus` (公車優先)
    - `more_subway` (軌道/捷運優先)
    - `less_walking` (少走點/減少步行)
    - `more_shading` (遮陽避曬/地下街優先)
    - `less_crowded` (避開擁擠/舒適車廂)
    - `mixed` (多元混合模式：YouBike+捷運+步行)
    """
    dest_name = request.destination_name or "目標活動場館"
    pref_val = request.preference.value if hasattr(request.preference, "value") else str(request.preference)
    return await maps_service.compute_route(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lng,
        dest_lat=request.destination_lat,
        dest_lng=request.destination_lng,
        dest_name=dest_name,
        prioritize_shade=request.prioritize_shade,
        preference=pref_val,
        wheelchair_accessible=request.wheelchair_accessible,
        departure_time=request.departure_time,
    )


@router.get("/visualize", response_class=HTMLResponse)
async def visualize_routes(key: str = Query(default="", description="Optional Google Maps API Key")) -> str:
    """Interactive visual testing tool supporting Google Maps JavaScript API and Leaflet fallback."""
    initial_key = key or settings.GOOGLE_MAPS_API_KEY or ""
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SideQuest | Google Maps & Routes API Visual Tester</title>
  
  <!-- Leaflet Fallback Resources -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    :root {{
      --bg: #0b0f19;
      --card: #151d30;
      --border: #263554;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --accent: #10b981;
      --warning: #f59e0b;
      --google-blue: #4285F4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background: var(--card);
      border-bottom: 1px solid var(--border);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      z-index: 1000;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    header h1 {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      background: rgba(66, 133, 244, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(66, 133, 244, 0.35);
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .header-controls {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .key-input-wrapper {{
      display: flex;
      align-items: center;
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 8px;
      gap: 6px;
    }}
    .key-input {{
      background: transparent;
      border: none;
      color: var(--text);
      font-size: 0.78rem;
      width: 220px;
      outline: none;
    }}
    .btn-sm {{
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 4px;
      padding: 4px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .btn-sm:hover {{ background: #1d4ed8; }}
    .map-toggle-btn {{
      background: #1e293b;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 0.78rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .map-toggle-btn.active {{
      border-color: var(--primary);
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
    }}
    .main-container {{
      display: flex;
      flex: 1;
      height: calc(100vh - 54px);
      overflow: hidden;
      position: relative;
    }}
    #map-container {{
      flex: 1;
      height: 100%;
      position: relative;
      background: #020617;
    }}
    #google-map, #leaflet-map {{
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
    }}
    .sidebar {{
      width: 440px;
      background: var(--card);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 16px;
      gap: 14px;
      z-index: 10;
    }}
    .card {{
      background: rgba(11, 15, 25, 0.75);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      backdrop-filter: blur(8px);
    }}
    .card h3 {{
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .form-group {{ margin-bottom: 10px; }}
    label {{
      display: block;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    select, input[type="text"] {{
      width: 100%;
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      color: var(--text);
      font-size: 0.82rem;
      outline: none;
    }}
    select:focus, input[type="text"]:focus {{ border-color: var(--primary); }}
    .btn-action {{
      width: 100%;
      background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
      color: white;
      border: none;
      border-radius: 6px;
      padding: 10px;
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
      transition: all 0.2s;
    }}
    .btn-action:hover {{
      box-shadow: 0 6px 16px rgba(2, 132, 199, 0.4);
      transform: translateY(-1px);
    }}
    .pref-btn {{
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid var(--border);
      border-radius: 9999px;
      padding: 5px 11px;
      font-size: 0.74rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .pref-btn:hover {{
      border-color: var(--primary);
      color: #ffffff;
    }}
    .pref-btn.active {{
      background: rgba(16, 185, 129, 0.2);
      border-color: #10b981;
      color: #34d399;
      font-weight: 600;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }}
    .metric-box {{
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px;
      text-align: center;
    }}
    .metric-value {{
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--primary);
      margin-top: 2px;
    }}
    .metric-label {{
      font-size: 0.68rem;
      color: var(--text-muted);
    }}
    .steps-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 6px;
    }}
    .step-item {{
      display: flex;
      gap: 10px;
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 0.8rem;
      align-items: flex-start;
    }}
    .step-icon {{
      font-size: 1.15rem;
      min-width: 26px;
      text-align: center;
      margin-top: 2px;
    }}
    .step-content {{ flex: 1; }}
    .step-meta {{
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-top: 3px;
    }}
    .shaded-tag {{
      font-size: 0.65rem;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: inline-block;
      margin-top: 4px;
      font-weight: 600;
    }}
    pre {{
      background: #050811;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px;
      font-size: 0.72rem;
      color: #cbd5e1;
      max-height: 150px;
      overflow: auto;
    }}
    .map-banner {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--border);
      backdrop-filter: blur(8px);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 500;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <h1>🗺️ SideQuest 智慧路徑與 Google Maps 可視化工具</h1>
      <span class="badge">Google Routes API (New)</span>
    </div>
    <div class="header-controls">
      <div class="key-input-wrapper">
        <span style="font-size:0.75rem; color:var(--text-muted);">🔑 Maps Key:</span>
        <input type="password" id="apiKeyInput" class="key-input" placeholder="貼上 Google Maps API Key" value="{initial_key}" />
        <button class="btn-sm" onclick="applyApiKey()">啟用 Google Map</button>
      </div>
      <button id="toggleMapBtn" class="map-toggle-btn active" onclick="toggleMapMode()">
        🗺️ <span id="mapModeLabel">Google Maps 模式</span>
      </button>
    </div>
  </header>

  <div class="main-container">
    <div id="map-container">
      <div id="google-map"></div>
      <div id="leaflet-map" style="display: none;"></div>
      <div id="mapBanner" class="map-banner">
        <span>📍 模式：<b id="activeMapName" style="color:var(--primary);">Google Maps JavaScript API (向量地圖 + Transit 圖層)</b></span>
      </div>
    </div>

    <div class="sidebar">
      <div class="card">
        <h3>📍 路線測試場景 (Route Presets)</h3>
        <div class="form-group">
          <label>快速載入台北藝文與避暑活動場景</label>
          <select id="presetSelect" onchange="loadPreset()">
            <option value="p1">1. 華山1914 ➡️ 瓶蓋工廠台北製造所 (南港捷運地下街連通)</option>
            <option value="p2">2. 台北車站 ➡️ C-LAB 臺灣當代文化實驗場 (大安藝文避暑)</option>
            <option value="p3">3. 市政府站 (BL18) ➡️ 松山文創園區 (林蔭遮蔽步道)</option>
            <option value="p4">4. 圓山花博爭豔館 ➡️ 中山赤峰街文創聚落 (捷運紅線直達)</option>
            <option value="p5">5. 西門紅樓 ➡️ 臺北流行音樂中心 TMC (板南線直通)</option>
          </select>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <div>
            <label>出發地 (Origin)</label>
            <input type="text" id="originName" value="華山1914文創園區" />
          </div>
          <div>
            <label>目的地 (Destination)</label>
            <input type="text" id="destName" value="POPOP Taipei 瓶蓋工廠" />
          </div>
        </div>

        <div class="form-group" style="margin-top:10px;">
          <label>路線偏好策略 (Route Preference)</label>
          <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:4px;">
            <button type="button" class="pref-btn active" data-pref="fastest" onclick="setPreference('fastest', this)">🟢 經典最快</button>
            <button type="button" class="pref-btn" data-pref="wheelchair" onclick="setPreference('wheelchair', this)">♿ 無障礙友善</button>
            <button type="button" class="pref-btn" data-pref="more_bus" onclick="setPreference('more_bus', this)">🚌 公車+</button>
            <button type="button" class="pref-btn" data-pref="more_subway" onclick="setPreference('more_subway', this)">🚇 軌道/捷運+</button>
            <button type="button" class="pref-btn" data-pref="less_walking" onclick="setPreference('less_walking', this)">🚶 少走點</button>
            <button type="button" class="pref-btn" data-pref="more_shading" onclick="setPreference('more_shading', this)">🛡️ 遮陽避曬</button>
            <button type="button" class="pref-btn" data-pref="less_crowded" onclick="setPreference('less_crowded', this)">👥 避開人潮</button>
            <button type="button" class="pref-btn" data-pref="mixed" onclick="setPreference('mixed', this)">🚲 混合運具</button>
          </div>
        </div>

        <button class="btn-action" style="margin-top: 12px;" onclick="calculateRoute()">
          ⚡ 計算 Google Routes & 多運具偏好分析
        </button>
      </div>

      <div class="card">
        <h3>🚲 多運具概覽比較 (Multimodal Estimates)</h3>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
          <div class="metric-box">
            <div class="metric-label">🚶 步行估算</div>
            <div class="metric-value" id="valWalk" style="font-size:0.9rem; color:#94a3b8;">-- 卡 / -- 分鐘</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">🚲 YouBike 2.0</div>
            <div class="metric-value" id="valBike" style="font-size:0.9rem; color:#38bdf8;">-- 卡 / $20</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">🚕 計程車 / 專車</div>
            <div class="metric-value" id="valTaxi" style="font-size:0.9rem; color:#f59e0b;">~-- 分鐘 / $--</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">🚇 大眾運輸</div>
            <div class="metric-value" id="valTransit" style="font-size:0.9rem; color:#10b981;">-- 分鐘</div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>📊 熱舒適與無障礙指標 (Metrics)</h3>
        <div class="metrics-grid">
          <div class="metric-box">
            <div class="metric-label">預估總耗時</div>
            <div class="metric-value" id="valDuration">-- 分鐘</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">地下/遮蔭覆蓋率</div>
            <div class="metric-value" id="valShade" style="color:var(--accent);">-- %</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">舒適度評分</div>
            <div class="metric-value" id="valScore" style="color:var(--warning);">-- / 100</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">總移動距離</div>
            <div class="metric-value" id="valDist">-- 公尺</div>
          </div>
        </div>
        <div id="routeAdvice" style="font-size:0.8rem; color:var(--text-muted); margin-top:10px; line-height:1.45;">
          請點選計算以取得即時建議。
        </div>
        <div id="accessNotes" style="font-size:0.75rem; color:#60a5fa; margin-top:6px; line-height:1.4;"></div>
        <div id="crowdNotes" style="font-size:0.75rem; color:#34d399; margin-top:4px; line-height:1.4;"></div>
      </div>

      <div class="card">
        <h3>🚶 分段導航細節 (Step-by-Step Directions)</h3>
        <div id="stepsList" class="steps-list">
          <div style="font-size:0.8rem; color:var(--text-muted); text-align:center; padding:10px;">尚未計算路徑</div>
        </div>
      </div>

      <div class="card">
        <h3>🔍 API 原始 JSON 結構 (Raw JSON)</h3>
        <pre id="jsonViewer">// 點擊計算後將顯示 RouteComfort 完整回傳結構</pre>
      </div>
    </div>
  </div>

  <script>
    const presets = {{
      p1: {{
        originName: "華山1914文創園區",
        originLat: 25.0441, originLng: 121.5294,
        destName: "POPOP Taipei 瓶蓋工廠",
        destLat: 25.0528, destLng: 121.6067
      }},
      p2: {{
        originName: "台北車站",
        originLat: 25.0478, originLng: 121.5170,
        destName: "C-LAB 臺灣當代文化實驗場",
        destLat: 25.0402, destLng: 121.5392
      }},
      p3: {{
        originName: "市政府站 (BL18)",
        originLat: 25.0411, originLng: 121.5652,
        destName: "松山文創園區",
        destLat: 25.0438, destLng: 121.5606
      }},
      p4: {{
        originName: "圓山花博爭豔館",
        originLat: 25.0713, originLng: 121.5201,
        destName: "中山赤峰街文創聚落",
        destLat: 25.0552, destLng: 121.5192
      }},
      p5: {{
        originName: "西門紅樓",
        originLat: 25.0423, originLng: 121.5068,
        destName: "臺北流行音樂中心 TMC",
        destLat: 25.0519, destLng: 121.5982
      }}
    }};

    let currentOrigin = {{ lat: 25.0441, lng: 121.5294, name: "華山1914文創園區" }};
    let currentDest = {{ lat: 25.0528, lng: 121.6067, name: "POPOP Taipei 瓶蓋工廠" }};
    let activeMapMode = 'google'; // 'google' | 'leaflet'

    // Google Maps Instances
    let gMap = null;
    let gOriginMarker = null;
    let gDestMarker = null;
    let gPolyline = null;
    let gTransitLayer = null;

    // Leaflet Instances
    let lMap = null;
    let lOriginMarker = null;
    let lDestMarker = null;
    let lPolyline = null;

    // Retrieve saved Google API key
    const savedKey = localStorage.getItem('sidequest_gmap_key') || document.getElementById('apiKeyInput').value;
    if (savedKey) {{
      document.getElementById('apiKeyInput').value = savedKey;
    }}

    function initLeafletMap() {{
      if (lMap) return;
      lMap = L.map('leaflet-map').setView([25.0478, 121.5450], 13);
      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
      }}).addTo(lMap);
      
      lMap.on('click', function(e) {{
        currentDest = {{ lat: e.latlng.lat, lng: e.latlng.lng, name: "自訂地圖目標點" }};
        document.getElementById('destName').value = currentDest.name;
        updateMapMarkers();
        calculateRoute();
      }});
    }}

    function loadGoogleMapsScript(apiKey) {{
      return new Promise((resolve, reject) => {{
        if (window.google && window.google.maps) {{
          resolve();
          return;
        }}
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${{apiKey}}&libraries=places,geometry&callback=onGoogleMapsLoaded`;
        script.async = true;
        script.defer = true;
        window.onGoogleMapsLoaded = () => resolve();
        script.onerror = () => reject(new Error('Google Maps JS script load failed'));
        document.head.appendChild(script);
      }});
    }}

    async function initGoogleMap() {{
      const apiKey = document.getElementById('apiKeyInput').value.trim();
      if (!apiKey) {{
        console.warn("No Google Maps API Key provided, defaulting to Leaflet Dark Mode.");
        switchToLeaflet();
        return;
      }}

      try {{
        await loadGoogleMapsScript(apiKey);
        const mapDiv = document.getElementById('google-map');
        gMap = new google.maps.Map(mapDiv, {{
          center: {{ lat: 25.0478, lng: 121.5450 }},
          zoom: 13,
          styles: [
            {{ elementType: "geometry", stylers: [{{ color: "#17263c" }}] }},
            {{ elementType: "labels.text.stroke", stylers: [{{ color: "#242f3e" }}] }},
            {{ elementType: "labels.text.fill", stylers: [{{ color: "#746855" }}] }},
            {{ featureType: "road", elementType: "geometry", stylers: [{{ color: "#38414e" }}] }},
            {{ featureType: "road", elementType: "geometry.stroke", stylers: [{{ color: "#212a37" }}] }},
            {{ featureType: "road", elementType: "labels.text.fill", stylers: [{{ color: "#9ca5b3" }}] }},
            {{ featureType: "water", elementType: "geometry", stylers: [{{ color: "#17263c" }}] }}
          ],
          mapTypeControl: true,
          streetViewControl: true,
          fullscreenControl: true,
        }});

        // Add Google Transit Layer (Subways and Transit)
        gTransitLayer = new google.maps.TransitLayer();
        gTransitLayer.setMap(gMap);

        // Click listener on Google Map
        gMap.addListener('click', (e) => {{
          currentDest = {{ lat: e.latLng.lat(), lng: e.latLng.lng(), name: "自訂地圖目標點" }};
          document.getElementById('destName').value = currentDest.name;
          updateMapMarkers();
          calculateRoute();
        }});

        updateMapMarkers();
      }} catch (err) {{
        console.error("Failed to initialize Google Maps JS API:", err);
        switchToLeaflet();
      }}
    }}

    function applyApiKey() {{
      const key = document.getElementById('apiKeyInput').value.trim();
      if (key) {{
        localStorage.setItem('sidequest_gmap_key', key);
        activeMapMode = 'google';
        document.getElementById('google-map').style.display = 'block';
        document.getElementById('leaflet-map').style.display = 'none';
        document.getElementById('activeMapName').textContent = "Google Maps JavaScript API (向量地圖 + Transit 圖層)";
        initGoogleMap().then(() => {{
          calculateRoute();
        }});
      }}
    }}

    function toggleMapMode() {{
      if (activeMapMode === 'google') {{
        switchToLeaflet();
      }} else {{
        activeMapMode = 'google';
        document.getElementById('google-map').style.display = 'block';
        document.getElementById('leaflet-map').style.display = 'none';
        document.getElementById('mapModeLabel').textContent = "Google Maps 模式";
        document.getElementById('activeMapName').textContent = "Google Maps JavaScript API (向量地圖 + Transit 圖層)";
        initGoogleMap();
      }}
    }}

    function switchToLeaflet() {{
      activeMapMode = 'leaflet';
      document.getElementById('google-map').style.display = 'none';
      document.getElementById('leaflet-map').style.display = 'block';
      document.getElementById('mapModeLabel').textContent = "OpenStreetMap 模式";
      document.getElementById('activeMapName').textContent = "Leaflet Dark Map (高對比開源圖層)";
      initLeafletMap();
      updateMapMarkers();
      if (lMap) setTimeout(() => lMap.invalidateSize(), 200);
    }}

    function loadPreset() {{
      const pKey = document.getElementById('presetSelect').value;
      const p = presets[pKey];
      currentOrigin = {{ lat: p.originLat, lng: p.originLng, name: p.originName }};
      currentDest = {{ lat: p.destLat, lng: p.destLng, name: p.destName }};
      document.getElementById('originName').value = p.originName;
      document.getElementById('destName').value = p.destName;
      updateMapMarkers();
      calculateRoute();
    }}

    function updateMapMarkers() {{
      // Update Google Map Markers
      if (activeMapMode === 'google' && gMap) {{
        if (gOriginMarker) gOriginMarker.setMap(null);
        if (gDestMarker) gDestMarker.setMap(null);

        gOriginMarker = new google.maps.Marker({{
          position: {{ lat: currentOrigin.lat, lng: currentOrigin.lng }},
          map: gMap,
          title: "出發地: " + currentOrigin.name,
          label: "A",
        }});

        gDestMarker = new google.maps.Marker({{
          position: {{ lat: currentDest.lat, lng: currentDest.lng }},
          map: gMap,
          title: "目的地: " + currentDest.name,
          label: "B",
        }});

        const bounds = new google.maps.LatLngBounds();
        bounds.extend({{ lat: currentOrigin.lat, lng: currentOrigin.lng }});
        bounds.extend({{ lat: currentDest.lat, lng: currentDest.lng }});
        gMap.fitBounds(bounds);
      }}

      // Update Leaflet Map Markers
      if (activeMapMode === 'leaflet' && lMap) {{
        if (lOriginMarker) lMap.removeLayer(lOriginMarker);
        if (lDestMarker) lMap.removeLayer(lDestMarker);

        lOriginMarker = L.circleMarker([currentOrigin.lat, currentOrigin.lng], {{
          radius: 9, fillColor: "#38bdf8", color: "#ffffff", weight: 2, fillOpacity: 0.9
        }}).addTo(lMap).bindPopup("<b>出發地:</b> " + currentOrigin.name);

        lDestMarker = L.circleMarker([currentDest.lat, currentDest.lng], {{
          radius: 9, fillColor: "#10b981", color: "#ffffff", weight: 2, fillOpacity: 0.9
        }}).addTo(lMap).bindPopup("<b>目的地:</b> " + currentDest.name);

        const group = new L.featureGroup([lOriginMarker, lDestMarker]);
        lMap.fitBounds(group.getBounds().pad(0.3));
      }}
    }}

    let selectedPreference = 'fastest';

    function setPreference(pref, btn) {{
      selectedPreference = pref;
      document.querySelectorAll('.pref-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      calculateRoute();
    }}

    async function calculateRoute() {{
      const payload = {{
        origin_lat: currentOrigin.lat,
        origin_lng: currentOrigin.lng,
        destination_lat: currentDest.lat,
        destination_lng: currentDest.lng,
        destination_name: currentDest.name,
        prioritize_shade: selectedPreference === 'more_shading',
        preference: selectedPreference,
        wheelchair_accessible: selectedPreference === 'wheelchair',
        travel_mode: "TRANSIT"
      }};

      try {{
        const res = await fetch('/api/v1/routes/compute', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        const data = await res.json();
        renderResult(data);
      }} catch (err) {{
        console.error("Route calculation error:", err);
      }}
    }}

    function renderResult(data) {{
      document.getElementById('valDuration').textContent = data.total_duration_minutes + " 分鐘";
      document.getElementById('valShade').textContent = data.underground_or_shaded_percentage + " %";
      document.getElementById('valScore').textContent = data.comfort_score + " 分";
      document.getElementById('valDist').textContent = data.total_distance_meters + " 公尺";
      document.getElementById('routeAdvice').textContent = data.route_advice;
      
      if (data.multimodal) {{
        document.getElementById('valWalk').textContent = `${{data.multimodal.walk_calories}} 卡 / ${{data.multimodal.walk_duration_minutes}} 分鐘`;
        document.getElementById('valBike').textContent = `${{data.multimodal.bike_calories}} 卡 / $${{data.multimodal.bike_cost_twd}}`;
        document.getElementById('valTaxi').textContent = `~${{data.multimodal.taxi_duration_minutes}} 分鐘 / $${{data.multimodal.taxi_cost_twd}}`;
        document.getElementById('valTransit').textContent = `${{data.total_duration_minutes}} 分鐘`;
      }}
      
      document.getElementById('accessNotes').textContent = data.accessibility_note ? `♿ ${{data.accessibility_note}}` : '';
      document.getElementById('crowdNotes').textContent = data.crowd_note ? `👥 ${{data.crowd_note}}` : '';
      document.getElementById('jsonViewer').textContent = JSON.stringify(data, null, 2);

      const stepsContainer = document.getElementById('stepsList');
      stepsContainer.innerHTML = '';

      if (data.segments && data.segments.length > 0) {{
        data.segments.forEach((s, idx) => {{
          let icon = '🚶';
          if (s.mode === 'SUBWAY') icon = '🚇';
          if (s.mode === 'BUS') icon = '🚌';
          if (s.mode === 'UNDERGROUND_WALK') icon = '🏬';

          const item = document.createElement('div');
          item.className = 'step-item';
          item.innerHTML = `
            <div class="step-icon">${{icon}}</div>
            <div class="step-content">
              <div><b>Step ${{idx + 1}}:</b> ${{s.instruction}}</div>
              <div class="step-meta">時間: ${{s.duration_minutes}} 分鐘 | 距離: ${{s.distance_meters}} 公尺</div>
              ${{s.is_shaded_or_underground ? '<span class="shaded-tag">🛡️ 地下/遮蔭防曬路徑</span>' : ''}}
            </div>
          `;
          stepsContainer.appendChild(item);
        }});
      }}

      // Render Polyline on Google Map
      if (activeMapMode === 'google' && gMap) {{
        if (gPolyline) gPolyline.setMap(null);

        let pathCoords = [];
        if (data.encoded_polyline && window.google && window.google.maps.geometry) {{
          pathCoords = google.maps.geometry.encoding.decodePath(data.encoded_polyline);
        }} else {{
          pathCoords = [
            {{ lat: currentOrigin.lat, lng: currentOrigin.lng }},
            {{ lat: (currentOrigin.lat + currentDest.lat)/2 + 0.002, lng: (currentOrigin.lng + currentDest.lng)/2 }},
            {{ lat: currentDest.lat, lng: currentDest.lng }}
          ];
        }}

        gPolyline = new google.maps.Polyline({{
          path: pathCoords,
          geodesic: true,
          strokeColor: '#38bdf8',
          strokeOpacity: 0.9,
          strokeWeight: 5,
          map: gMap,
        }});
      }}

      // Render Polyline on Leaflet Map
      if (activeMapMode === 'leaflet' && lMap) {{
        if (lPolyline) lMap.removeLayer(lPolyline);
        const latlngs = [
          [currentOrigin.lat, currentOrigin.lng],
          [(currentOrigin.lat + currentDest.lat)/2 + 0.002, (currentOrigin.lng + currentDest.lng)/2],
          [currentDest.lat, currentDest.lng]
        ];
        lPolyline = L.polyline(latlngs, {{
          color: '#38bdf8',
          weight: 5,
          opacity: 0.85,
          dashArray: '8, 8'
        }}).addTo(lMap);
      }}
    }}

    // Bootstrapping
    const initialKey = document.getElementById('apiKeyInput').value.trim();
    if (initialKey) {{
      initGoogleMap().then(() => {{
        calculateRoute();
      }});
    }} else {{
      switchToLeaflet();
      calculateRoute();
    }}
  </script>
</body>
</html>
"""
    return html_content
