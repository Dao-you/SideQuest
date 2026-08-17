<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Loader } from '@googlemaps/js-api-loader'
import { Badge, Button, Chip, Input, Progress, Snackbar } from '@varlet/ui'

const MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY

const mapElement = ref(null)
const mapState = ref('loading')
const mapError = ref('')
const map = ref(null)
const activeFilter = ref('為你推薦')
const activePlaceId = ref('huashan')
const prompt = ref('')
const isExploring = ref(false)
const selectedTab = ref('discover')
const markers = new Map()

const filters = ['為你推薦', '室內避暑', '低人流', '免費入場']
const quickPrompts = ['今天下午想看展，不想太熱', '想找人少的地方散步', '今晚信義區有什麼活動？']

const places = [
  {
    id: 'huashan',
    name: '華山 1914 文化創意產業園區',
    shortName: '華山 1914',
    category: '展覽 · 室內',
    address: '中正區八德路一段 1 號',
    description: '今天有兩個展覽正在進行，園區周邊也有適合慢慢逛的選物店。',
    crowd: 42,
    sun: 18,
    distance: '捷運 18 分鐘',
    distanceShort: '18 min',
    rating: '4.6',
    time: '10:00 – 20:00',
    color: '#e9855f',
    position: { lat: 25.0441, lng: 121.5298 },
    label: 'A',
  },
  {
    id: 'dadaocheng',
    name: '大稻埕碼頭・河岸散步',
    shortName: '大稻埕碼頭',
    category: '戶外 · 散步',
    address: '大同區民生西路底',
    description: '午後風勢舒服，河岸人流分散，適合沿著迪化街一路散步到碼頭。',
    crowd: 27,
    sun: 63,
    distance: '捷運 24 分鐘',
    distanceShort: '24 min',
    rating: '4.5',
    time: '全天開放',
    color: '#5b8f89',
    position: { lat: 25.0566, lng: 121.5085 },
    label: 'B',
  },
  {
    id: 'songshan',
    name: '松山文創園區・松菸小賣所',
    shortName: '松山文創園區',
    category: '設計 · 選物',
    address: '信義區光復南路 133 號',
    description: '內容很豐富，但熱門展區目前人潮偏高，建議先逛文創小賣所。',
    crowd: 74,
    sun: 36,
    distance: '捷運 31 分鐘',
    distanceShort: '31 min',
    rating: '4.4',
    time: '09:00 – 18:00',
    color: '#d9a441',
    position: { lat: 25.0438, lng: 121.5608 },
    label: 'C',
  },
  {
    id: 'beitou',
    name: '北投圖書館・綠建築散策',
    shortName: '北投圖書館',
    category: '建築 · 室內',
    address: '北投區光明路 251 號',
    description: '樹蔭充足、室內涼爽，適合把午後留給一本書。',
    crowd: 19,
    sun: 12,
    distance: '捷運 38 分鐘',
    distanceShort: '38 min',
    rating: '4.8',
    time: '09:00 – 17:00',
    color: '#7b7bb1',
    position: { lat: 25.1367, lng: 121.5067 },
    label: 'D',
  },
]

const selectedPlace = computed(() => places.find((place) => place.id === activePlaceId.value) ?? places[0])
const visiblePlaces = computed(() => {
  if (activeFilter.value === '低人流') return [...places].sort((a, b) => a.crowd - b.crowd)
  if (activeFilter.value === '室內避暑') return places.filter((place) => place.sun < 40)
  if (activeFilter.value === '免費入場') return places.filter((place) => ['dadaocheng', 'beitou'].includes(place.id))
  return places
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

function explore() {
  if (isExploring.value) return
  isExploring.value = true
  window.setTimeout(() => {
    isExploring.value = false
    activeFilter.value = '為你推薦'
    activePlaceId.value = 'huashan'
    Snackbar.success('已依照你的感受，更新 4 個城市提案')
  }, 700)
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
    await Promise.all(places.map((place) => addMarker(place, AdvancedMarkerElement)))
    mapState.value = 'ready'
  } catch (error) {
    mapState.value = 'error'
    mapError.value = error?.message?.includes('RefererNotAllowedMapError')
      ? '此網址尚未加入 API key 的允許來源'
      : 'Google Maps 載入失敗，請檢查 API key 與 Maps JavaScript API 是否啟用'
  }
}

onMounted(initMap)
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
        <Badge value="BETA" type="primary" class="beta-badge" />
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

      <div class="recommendation-header">
        <div>
          <div class="section-kicker">LIVE IN TAIPEI <span class="pulse-dot"></span></div>
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

      <div class="place-list">
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
