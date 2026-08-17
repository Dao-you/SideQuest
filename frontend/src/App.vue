<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Loader } from '@googlemaps/js-api-loader'
import { Badge, Button, Chip, Input, Progress, Snackbar } from '@varlet/ui'
import { createEventDataSource } from './data/eventDataSource'
import { toEventPlace } from './data/eventPresentation'

const MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
const AGENT_API_URL = import.meta.env.VITE_AGENT_API_URL || ''

const mapElement = ref(null)
const mapState = ref('loading')
const mapError = ref('')
const map = ref(null)
const activeFilter = ref('為你推薦')
const activePlaceId = ref('huashan')
const prompt = ref('')
const isExploring = ref(false)
const eventsLoading = ref(true)
const eventsError = ref('')
const aiReply = ref('')
const aiError = ref('')
const selectedTab = ref('discover')
const markers = new Map()

const filters = ['為你推薦', '室內避暑', '低人流', '免費入場']
const quickPrompts = ['今天下午想看展，不想太熱', '想找人少的地方散步', '今晚信義區有什麼活動？']

const places = ref([])
const eventDataSource = createEventDataSource()
const eventSourceLabel = eventDataSource.label

async function loadEvents() {
  eventsLoading.value = true
  eventsError.value = ''
  try {
    const records = await eventDataSource.list()
    places.value = records.map(toEventPlace)
    activePlaceId.value = places.value[0]?.id ?? ''
  } catch (error) {
    eventsError.value = '活動 CSV 暫時無法載入，請確認前端靜態資料是否存在。'
    console.error(error)
  } finally {
    eventsLoading.value = false
  }
}

const selectedPlace = computed(() => places.value.find((place) => place.id === activePlaceId.value) ?? places.value[0])
const visiblePlaces = computed(() => {
  if (activeFilter.value === '低人流') return [...places.value].sort((a, b) => a.crowd - b.crowd)
  if (activeFilter.value === '室內避暑') return places.value.filter((place) => place.isIndoor || place.sun < 40)
  if (activeFilter.value === '免費入場') return places.value.filter((place) => place.fee.includes('免費'))
  return places.value
})

function crowdLabel(score) {
  if (score < 30) return '舒適'
  if (score < 60) return '適中'
  return '偏熱鬧'
}

function crowdClass(score) {
  if (score < 30) return 'good'
  if (score < 60) return 'medium'
  return 'busy'
}

function selectPlace(place) {
  activePlaceId.value = place.id
  const marker = markers.get(place.id)
  if (marker && map.value) {
    map.value.panTo(place.position)
    map.value.setZoom(14)
    const markerContent = marker.content
    markerContent?.classList.add('is-active')
    window.setTimeout(() => markerContent?.classList.remove('is-active'), 900)
  }
}

function useQuickPrompt(value) {
  prompt.value = value
  nextTick(() => document.querySelector('.prompt-input textarea, .prompt-input input')?.focus())
}

async function explore() {
  if (isExploring.value) return
  if (!prompt.value.trim()) {
    Snackbar.warning('先告訴我你現在想怎麼感受台北')
    return
  }
  isExploring.value = true
  aiReply.value = ''
  aiError.value = ''
  try {
    const response = await fetch(`${AGENT_API_URL}/api/v1/agent/ai-recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: prompt.value.trim(), events: places.value }),
    })
    if (!response.ok) throw new Error(`Agent request failed: ${response.status}`)
    const result = await response.json()
    aiReply.value = result.reply || '我已收到你的需求，先從這些活動開始探索吧。'
    activeFilter.value = '為你推薦'
    activePlaceId.value = places.value[0]?.id ?? ''
    Snackbar.success(`Gemini 已根據 ${result.used_event_count ?? places.value.length} 個活動完成分析`)
  } catch (error) {
    aiError.value = AGENT_API_URL
      ? 'Agent 暫時沒有回應，推薦卡仍可直接瀏覽。'
      : '尚未設定 Agent API 位址；先瀏覽 CSV 活動，部署 backend 後即可啟用 Gemini。'
    console.error(error)
  } finally {
    isExploring.value = false
  }
}

function centerMap() {
  if (!map.value) return
  map.value.panTo({ lat: 25.0478, lng: 121.5319 })
  map.value.setZoom(12)
}

async function addMarker(place, AdvancedMarkerElement) {
  const content = document.createElement('div')
  content.className = 'map-pin'
  content.style.setProperty('--pin-color', place.color)
  const label = document.createElement('span')
  label.textContent = place.label
  content.appendChild(label)
  const marker = new AdvancedMarkerElement({
    map: map.value,
    position: place.position,
    title: place.name,
    content,
  })
  marker.addEventListener('gmp-click', () => selectPlace(place))
  markers.set(place.id, marker)
}

async function initMap() {
  if (!MAPS_API_KEY) {
    mapState.value = 'error'
    mapError.value = '尚未設定 Google Maps API key'
    return
  }

  try {
    const loader = new Loader({
      apiKey: MAPS_API_KEY,
      version: 'weekly',
    })
    await loader.load()
    map.value = new window.google.maps.Map(mapElement.value, {
      center: { lat: 25.0478, lng: 121.5319 },
      zoom: 12,
      mapId: 'DEMO_MAP_ID',
      minZoom: 11,
      maxZoom: 17,
      disableDefaultUI: true,
      clickableIcons: false,
      gestureHandling: 'greedy',
    })
    const { AdvancedMarkerElement } = await window.google.maps.importLibrary('marker')
    await Promise.all(places.value.map((place) => addMarker(place, AdvancedMarkerElement)))
    mapState.value = 'ready'
  } catch (error) {
    mapState.value = 'error'
    mapError.value = error?.message?.includes('RefererNotAllowedMapError')
      ? '此網址尚未加入 API key 的允許來源'
      : 'Google Maps 載入失敗，請檢查 API key 與 Maps JavaScript API 是否啟用'
  }
}

onMounted(async () => {
  await loadEvents()
  await initMap()
})
</script>

<template>
  <main class="app-shell">
    <section class="map-stage" aria-label="台北市地圖">
      <div ref="mapElement" class="google-map"></div>
      <div v-if="mapState === 'loading'" class="map-state map-loading">
        <div class="loader-orbit"></div>
        <span>正在感受台北的脈動…</span>
      </div>
      <div v-if="mapState === 'error'" class="map-state map-error">
        <span class="error-mark">!</span>
        <strong>Google Maps 暫時無法載入</strong>
        <small>{{ mapError }}</small>
      </div>

      <header class="topbar">
        <div class="brand-lockup">
          <div class="brand-mark">SQ</div>
          <div>
            <div class="brand-name">sidequest<span>.</span></div>
            <div class="brand-caption">城市裡的下一站</div>
          </div>
        </div>
        <div class="topbar-actions">
          <div class="city-pill"><span class="status-dot"></span> Taipei City <span class="caret">⌄</span></div>
          <button class="avatar-button" aria-label="開啟個人檔案">YL</button>
        </div>
      </header>

      <div class="map-context-pill">
        <span class="context-icon">☀</span>
        <div><strong>28°</strong><span>體感 30°</span></div>
        <i></i>
        <div><strong>UV 5</strong><span>中等曝曬</span></div>
        <div class="refresh-label">剛剛更新</div>
      </div>

      <button class="map-control locate-control" aria-label="回到台北市中心" @click="centerMap">◎</button>
      <div class="map-control-stack">
        <button class="map-control" aria-label="放大地圖" @click="map?.setZoom((map?.getZoom() ?? 12) + 1)">＋</button>
        <button class="map-control" aria-label="縮小地圖" @click="map?.setZoom((map?.getZoom() ?? 12) - 1)">−</button>
      </div>

      <div class="map-legend">
        <span><b class="legend-dot legend-cool"></b>人流舒適</span>
        <span><b class="legend-dot legend-warm"></b>熱門區域</span>
      </div>
    </section>

    <section class="bottom-sheet" aria-label="SideQuest 探索面板">
      <div class="sheet-handle"></div>
      <div class="sheet-header">
        <div>
          <p class="eyebrow"><span class="eyebrow-dot"></span> 你的城市 Agent</p>
          <h1>今天，想怎麼感受台北？</h1>
        </div>
        <div class="header-badges">
          <Badge value="CSV" type="success" class="data-badge" />
          <Badge value="BETA" type="primary" class="beta-badge" />
        </div>
      </div>

      <div class="prompt-composer">
        <div class="prompt-icon">✦</div>
        <Input
          v-model="prompt"
          class="prompt-input"
          textarea
          :rows="1"
          :resize="false"
          placeholder="告訴我你現在的感受，例如：想找室內展覽，不要太熱、人不要太多…"
          @keydown.enter.exact.prevent="explore"
        />
        <Button class="explore-button" type="primary" round :loading="isExploring" @click="explore">
          <span v-if="!isExploring">探索 <span class="button-arrow">↗</span></span>
        </Button>
      </div>

      <div class="quick-prompts">
        <button v-for="item in quickPrompts" :key="item" class="quick-prompt" @click="useQuickPrompt(item)">
          {{ item }} <span>↗</span>
        </button>
      </div>

      <div v-if="isExploring || aiReply || aiError" class="agent-response" :class="{ failed: aiError }">
        <div class="agent-response-heading"><span>✦</span> Vertex AI · Gemini <em v-if="isExploring">正在理解你的感受…</em></div>
        <p v-if="isExploring" class="agent-loading-copy">正在比較 CSV 裡的活動、日期、地點與人流舒適度。</p>
        <p v-else-if="aiError" class="agent-error-copy">{{ aiError }}</p>
        <p v-else>{{ aiReply }}</p>
      </div>

      <div class="recommendation-header">
        <div>
          <div class="section-kicker">{{ eventSourceLabel }} · {{ places.length }} ACTIVITIES <span class="pulse-dot"></span></div>
          <h2>為你找到的城市提案</h2>
        </div>
        <button class="view-all" @click="activeFilter = '為你推薦'">查看全部 <span>→</span></button>
      </div>

      <div class="filter-row" role="tablist" aria-label="推薦篩選">
        <Chip
          v-for="filter in filters"
          :key="filter"
          :checked="activeFilter === filter"
          checkable
          class="filter-chip"
          @click="activeFilter = filter"
        >
          {{ filter }}
        </Chip>
      </div>

      <div v-if="eventsLoading" class="events-state">正在從 taipeidope_events.csv 讀取活動…</div>
      <div v-else-if="eventsError" class="events-state events-state-error">{{ eventsError }}</div>
      <div v-else class="place-list">
        <article
          v-for="(place, index) in visiblePlaces"
          :key="place.id"
          class="place-card"
          :class="{ selected: activePlaceId === place.id }"
          @click="selectPlace(place)"
        >
          <div class="place-number">0{{ index + 1 }}</div>
          <div class="place-main">
            <div class="place-topline">
              <span class="place-category">{{ place.category }}</span>
              <span class="place-distance">{{ place.distanceShort }} <span>↗</span></span>
            </div>
            <h3>{{ place.name }}</h3>
            <div class="place-meta">{{ place.dateRange || '活動日期請見來源' }} <span>·</span> {{ place.fee }}</div>
            <p>{{ place.description }}</p>
            <div class="metric-row">
              <span class="metric crowd-metric" :class="crowdClass(place.crowd)">
                <i class="metric-icon crowd-icon">♧</i> 人流 {{ crowdLabel(place.crowd) }}
                <strong>{{ place.crowd }}</strong>
              </span>
              <span class="metric">
                <i class="metric-icon sun-icon">◒</i> 曝曬 {{ place.sun }}%
              </span>
              <span class="metric"><i class="metric-icon time-icon">◷</i> {{ place.time }}</span>
            </div>
            <div class="crowd-progress">
              <Progress :value="place.crowd" :color="place.color" track-color="#edece7" :height="4" />
            </div>
          </div>
          <div class="place-arrow" :style="{ '--place-color': place.color }">↗</div>
        </article>
      </div>

      <div class="diversion-note">
        <div class="note-icon">↝</div>
        <div><strong>SideQuest 建議你繞一點路</strong><span>松菸目前人流較高，華山只要多 7 分鐘但舒適度高 32%。</span></div>
        <span class="note-sparkle">✦</span>
      </div>
    </section>

    <nav class="mobile-nav" aria-label="主要導覽">
      <button :class="{ active: selectedTab === 'discover' }" @click="selectedTab = 'discover'"><span>⌂</span>探索</button>
      <button :class="{ active: selectedTab === 'saved' }" @click="selectedTab = 'saved'"><span>♡</span>收藏</button>
      <button :class="{ active: selectedTab === 'profile' }" @click="selectedTab = 'profile'"><span>◌</span>我的</button>
    </nav>
  </main>
</template>
