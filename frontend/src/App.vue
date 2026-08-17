<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Loader } from '@googlemaps/js-api-loader'
import { Badge, Button, Chip, Input, Progress, Snackbar } from '@varlet/ui'
import { createEventDataSource } from './data/eventDataSource'
import { SHADE_TIME_SCENARIOS, toEventPlace } from './data/eventPresentation'
import { createAgentService } from './services/agentService'
import { weatherService } from './services/weatherService'
import { crowdService } from './services/crowdService'
import { applyShadeScenarioToGoogleRoute, routesService } from './services/routesService'
import { userService } from './services/userService'

const rawEnvMapsKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
const TAIPEI_CENTER = { lat: 25.0478, lng: 121.5170 }
const mapElement = ref(null)
const sheetElement = ref(null)
const mapState = ref('loading')
const mapError = ref('')
const map = ref(null)
const userLocation = ref({ ...TAIPEI_CENTER })
const hasUserLocation = ref(false)
const locationState = ref('idle')
const activeFilter = ref('推薦')
const activePlaceId = ref('')
const prompt = ref('')
const isExploring = ref(false)
const eventsLoading = ref(true)
const eventsError = ref('')
const detailPlaceId = ref('')
const selectedTab = ref('discover')
const sheetExpanded = ref(false)
const sheetMinimized = ref(false)
const sheetDragging = ref(false)
const sheetDragHeight = ref(null)

// Weather & Microclimate State
const weather = ref({
  temperature: 28,
  apparentTemperature: 30,
  uvIndex: 5,
  comfortLevel: 'MODERATE',
  description: '正在獲取微氣候…',
  advice: '午後部分場館人潮較多，建議優先選擇地下街連通或室內空調景點',
  sunExposureLevel: 'MODERATE',
  heatWarning: false,
  isMock: false,
})
const weatherLoading = ref(false)

// Deterministic shade scenarios for hackathon acceptance testing
const shadeTimePeriod = ref('morning')

// User & Persona State (PRD 7.1)
const personas = ref([])
const activePersona = ref({
  id: 'demo_weekend_explorer',
  name: '林宥廷 (週末文藝探索者)',
  account_type: 'WEEKEND_EXPLORER',
  interest_tags: ['當代藝術', '獨立手作', '手沖咖啡', '動漫展覽'],
})
const showPersonaModal = ref(false)
const favoritePlaceIds = ref(new Set())

// Agent Decision & Reasoning State (PRD 7.3 & 7.4)
const aiReply = ref('')
const aiError = ref('')
const aiThoughtSteps = ref([])
const aiParsedCriteria = ref(null)
const aiRecommendations = ref([])
const aiDispersalSummary = ref('')
const aiOneSentenceSummary = ref('')
const aiEvaluatedCount = ref(0)
const agentSessionId = ref(null)
const showThoughtTrace = ref(false)
const feedbackMap = ref(new Map())

// Routes & Thermal Comfort State (PRD 10 & Route Preferences)
const activeRoute = ref(null)
const routeLoading = ref(false)
const routePreference = ref('fastest') // 'fastest' | 'wheelchair' | 'more_bus' | 'more_subway' | 'less_walking' | 'more_shading' | 'less_crowded' | 'mixed'
const routeDepartureTime = ref('現在出發')
const showDepartureDropdown = ref(false)
const routeOriginSwapped = ref(false)
const selectedModalTab = ref('transit') // 'overview' | 'youbike' | 'transit' | 'taxi'

const routePreferencesList = [
  { id: 'fastest', label: '最快抵達', icon: '●', desc: '最快速抵達' },
  { id: 'wheelchair', label: '無障礙', icon: '♿', desc: '電梯/推車/大件行李友善' },
  { id: 'more_bus', label: '公車優先', icon: '公', desc: '公車直達優先' },
  { id: 'more_subway', label: '捷運優先', icon: '捷', desc: '捷運軌道優先' },
  { id: 'less_walking', label: '少走路', icon: '走', desc: '少走路/少換乘' },
  { id: 'more_shading', label: '較少曝曬', icon: '蔭', desc: '地下街與林蔭遮蔽' },
  { id: 'less_crowded', label: '避開人潮', icon: '人', desc: '舒適離峰車廂' },
  { id: 'mixed', label: '混合交通', icon: '混', desc: 'YouBike+捷運組合' },
]

const departureTimeOptions = [
  '現在出發',
  '10 分鐘後出發',
  '30 分鐘後出發',
  '1 小時後出發',
]

let currentPolyline = null
const currentRoutePolylines = []
let routeRequestVersion = 0
let userLocationOverlay = null

// Heatmap State (PRD 8)
const heatmapVisible = ref(false)
const heatmapOverlays = []
const heatmapIsMock = ref(true)

// Quick Prompts State (PRD 7.2)
const quickPrompts = ref([
  '8月22日下午想和另一半約會，看展再喝咖啡',
  '明天晚上想找適合約會的活動，不要太擠',
  '想找人少安靜的地方散步喝咖啡',
])
const quickTags = ref([])

const places = ref([])
const eventRecords = ref([])
const eventDataSource = createEventDataSource()
const eventSourceLabel = eventDataSource.label
const agentService = createAgentService()
const markers = new Map()
let sheetDragStartY = 0
let sheetDragStartHeight = 0
let mapFocusTimer = null

const filters = computed(() => {
  const base = ['推薦', '室內', '低人流', '免費']
  const tagLabelMap = {
    室內避暑: '室內',
    免費入場: '免費',
  }
  if (quickTags.value.length > 0) {
    quickTags.value.forEach((tag) => {
      const label = tagLabelMap[tag.label] || tag.label
      if (!base.includes(label)) base.push(label)
    })
  }
  return base
})

const sheetStyle = computed(() =>
  sheetDragHeight.value ? { '--sheet-height': `${sheetDragHeight.value}px` } : undefined
)

const sheetHandleLabel = computed(() => {
  if (sheetMinimized.value) return '向上展開探索'
  if (sheetExpanded.value) return '向下回到半高'
  return '向上展開 · 下滑收到底'
})

const avatarInitials = computed(() => {
  const name = activePersona.value?.name || 'SideQuest'
  return name.slice(0, 2).toUpperCase()
})

const selectedPlace = computed(() => places.value.find((place) => place.id === activePlaceId.value) ?? places.value[0])
const detailPlace = computed(() => places.value.find((place) => place.id === detailPlaceId.value) ?? null)
const activeShadeScenario = computed(() =>
  SHADE_TIME_SCENARIOS.find((scenario) => scenario.id === shadeTimePeriod.value) ?? SHADE_TIME_SCENARIOS[0]
)

const bookmarkedPlaces = computed(() =>
  places.value.filter((p) => favoritePlaceIds.value.has(p.id))
)

const visiblePlaces = computed(() => {
  if (selectedTab.value === 'saved') {
    return bookmarkedPlaces.value
  }
  if (activeFilter.value === '低人流') {
    return places.value
      .filter((place) => Number.isFinite(place.crowd))
      .sort((a, b) => a.crowd - b.crowd)
  }
  if (activeFilter.value === '室內') {
    return places.value.filter((place) => place.isIndoor)
  }
  if (activeFilter.value === '免費') {
    return places.value.filter((place) => place.fee.includes('免費'))
  }
  // If filter matches a category
  const matching = places.value.filter((p) => p.category?.includes(activeFilter.value))
  if (matching.length > 0) return matching

  return places.value
})

function crowdLabel(score) {
  if (!Number.isFinite(score)) return '暫無人流資料'
  if (score < 35) return '舒適少人'
  if (score < 65) return '人流適中'
  return '人潮偏多'
}

function crowdClass(score) {
  if (!Number.isFinite(score)) return 'unknown'
  if (score < 35) return 'good'
  if (score < 65) return 'medium'
  return 'busy'
}

function routeStepContext(step) {
  const mode = String(step?.mode || '').toUpperCase()
  if (!['WALK', 'WALKING', 'UNDERGROUND_WALK'].includes(mode)) return '🚇 大眾運輸路段'
  if (Number.isFinite(Number(step?.shade_percentage))) {
    return `◒ ${activeShadeScenario.value.label}遮蔭情境 ${Number(step.shade_percentage)}%`
  }
  return step?.is_shaded_or_underground ? '🛡️ 遮蔭/地下通道' : '☀️ 戶外步行路段'
}

async function loadWeather() {
  weatherLoading.value = true
  try {
    const data = await weatherService.getCurrentWeather(userLocation.value.lat, userLocation.value.lng)
    weather.value = data
  } catch (err) {
    console.error('Weather load error:', err)
  } finally {
    weatherLoading.value = false
  }
}

async function loadUserAndPersonas() {
  try {
    const [personaList, profile] = await Promise.all([
      userService.listPersonas(),
      userService.getProfile(activePersona.value.id),
    ])
    personas.value = personaList
    if (profile) {
      activePersona.value = profile
      favoritePlaceIds.value = new Set(profile.favorited_event_ids || [])
    }
  } catch (err) {
    console.error('User persona load error:', err)
  }
}

async function switchPersona(persona) {
  try {
    const profile = await userService.mockLogin(persona.id)
    activePersona.value = profile
    favoritePlaceIds.value = new Set(profile.favorited_event_ids || [])
    showPersonaModal.value = false
    Snackbar.success(`已切換為：${profile.name}`)
    // Prompt agent with tailored persona
    if (!prompt.value) {
      prompt.value = `我是${profile.name}，想找符合我偏好的台北活動`
    }
  } catch (err) {
    console.error('Switch persona error:', err)
  }
}

async function toggleBookmark(place) {
  if (!place) return
  const isCurrentlyFavorited = favoritePlaceIds.value.has(place.id)
  try {
    const res = await userService.toggleFavorite(activePersona.value.id, place.id)
    if (res.is_favorited) {
      favoritePlaceIds.value.add(place.id)
      Snackbar.success(`已將「${place.name}」加入收藏夾`)
    } else {
      favoritePlaceIds.value.delete(place.id)
      Snackbar.info(`已從收藏夾移除「${place.name}」`)
    }
  } catch (err) {
    // Optimistic fallback
    if (isCurrentlyFavorited) {
      favoritePlaceIds.value.delete(place.id)
      Snackbar.info(`已移出收藏`)
    } else {
      favoritePlaceIds.value.add(place.id)
      Snackbar.success(`已加入收藏`)
    }
  }
}

async function loadQuickPrompts() {
  try {
    const data = await agentService.getQuickPrompts()
    if (data?.example_prompts?.length) {
      quickPrompts.value = data.example_prompts.map((p) => p.prompt || p.title)
    }
    if (data?.quick_tags?.length) {
      quickTags.value = data.quick_tags
    }
  } catch (err) {
    console.error('Quick prompts load error:', err)
  }
}

function rebuildPlaces() {
  places.value = eventRecords.value.map((record, index) =>
    toEventPlace(record, index, shadeTimePeriod.value)
  )
}

async function selectShadeTimePeriod(period) {
  if (period === shadeTimePeriod.value || !SHADE_TIME_SCENARIOS.some((scenario) => scenario.id === period)) return

  const shouldRefreshRoute = Boolean(activeRoute.value)
  const routePlaceId = detailPlaceId.value || activePlaceId.value
  shadeTimePeriod.value = period
  rebuildPlaces()

  if (shouldRefreshRoute) {
    const place = places.value.find((candidate) => candidate.id === routePlaceId)
    if (place?.position) await planRouteToPlace(place)
  }
}

async function loadEvents() {
  eventsLoading.value = true
  eventsError.value = ''
  try {
    const [records, venueStatuses] = await Promise.all([
      eventDataSource.list(),
      crowdService.getVenuesStatus(),
    ])
    const crowdByVenue = new Map(venueStatuses.map((venue) => [venue.venue_id, venue]))
    eventRecords.value = records.map((record) => {
      const venueStatus = crowdByVenue.get(record.venueId)
      return {
        ...record,
        crowdScore: venueStatus?.crowd_score,
        // The current backend venue feed comes from MockDataSeeder.
        crowdIsMock: Boolean(venueStatus),
      }
    })
    rebuildPlaces()
    activePlaceId.value = places.value[0]?.id ?? ''
    if (map.value) {
      markers.forEach((m) => m.overlay?.setMap(null))
      markers.clear()
      places.value.filter((place) => place.position).forEach(addMarker)
      syncMarkerSelection()
    }
  } catch (error) {
    eventsError.value = '活動清單暫時無法載入，請稍後再試。'
    console.error(error)
  } finally {
    eventsLoading.value = false
  }
}

function syncMarkerSelection() {
  const recommendedIds = new Set(
    aiRecommendations.value.map((card) => card.event?.id).filter(Boolean),
  )
  markers.forEach((markerRecord, id) => {
    markerRecord.content?.classList.toggle('is-active', id === activePlaceId.value)
    markerRecord.content?.classList.toggle('is-recommended', recommendedIds.has(id))
    if (markerRecord.content) {
      markerRecord.content.style.zIndex = id === activePlaceId.value
        ? '100'
        : (recommendedIds.has(id) ? '50' : '1')
    }
  })
}

function getMapBottomInset() {
  if (!mapElement.value || !sheetElement.value) return 0
  const mapRect = mapElement.value.getBoundingClientRect()
  const sheetRect = sheetElement.value.getBoundingClientRect()
  const horizontalOverlap = Math.min(mapRect.right, sheetRect.right) - Math.max(mapRect.left, sheetRect.left)
  if (horizontalOverlap <= 0 || sheetRect.top >= mapRect.bottom) return 0
  const overlap = mapRect.bottom - Math.max(mapRect.top, sheetRect.top)
  return Math.max(0, Math.min(overlap, mapRect.height - 80))
}

function focusPlaceInVisibleMap(place, { settle = true } = {}) {
  if (!map.value || !place?.position) return
  const applyFocus = () => {
    const bottomInset = getMapBottomInset()
    const projection = map.value.getProjection()
    const placePoint = projection?.fromLatLngToPoint(place.position)
    const zoom = map.value.getZoom() ?? 14
    if (!projection || !placePoint || !window.google?.maps?.Point) {
      map.value.panTo(place.position)
      return
    }

    const zoomScale = 2 ** zoom
    const centerPoint = new window.google.maps.Point(
      placePoint.x,
      placePoint.y + (bottomInset / 2) / zoomScale,
    )
    map.value.panTo(projection.fromPointToLatLng(centerPoint))
  }

  window.requestAnimationFrame(applyFocus)
  window.clearTimeout(mapFocusTimer)
  if (settle) mapFocusTimer = window.setTimeout(applyFocus, 380)
}

function refocusSelectedPlace() {
  const place = places.value.find((candidate) => candidate.id === activePlaceId.value)
  if (place) focusPlaceInVisibleMap(place)
}

function selectPlace(place) {
  if (!place) return
  activePlaceId.value = place.id
  if (markers.has(place.id) && map.value && place.position) {
    focusPlaceInVisibleMap(place)
    syncMarkerSelection()
  }
}

async function openPlaceDetails(place) {
  resetRouteState()
  detailPlaceId.value = place.id
  sheetExpanded.value = true
  sheetMinimized.value = false
  selectPlace(place)
  await nextTick()
  sheetElement.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

async function closePlaceDetails() {
  resetRouteState()
  detailPlaceId.value = ''
  sheetExpanded.value = false
  await nextTick()
  sheetElement.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function revealPlaceOnMap(place) {
  selectPlace(place)
  minimizeSheet()
}

// Interactive Route Planning (PRD 10)
function clearMapRouteLayers() {
  while (currentRoutePolylines.length > 0) {
    currentRoutePolylines.pop()?.setMap(null)
  }
  if (currentPolyline) {
    currentPolyline.setMap(null)
    currentPolyline = null
  }
}

function fitRouteInVisibleMap(bounds) {
  const bottomInset = getMapBottomInset()
  map.value.fitBounds(bounds, {
    top: 70,
    right: 70,
    bottom: bottomInset + 70,
    left: 70,
  })
}

function formatZhTwStepInstruction(step, actualMode) {
  // If transit details are present from DirectionsService step
  const transit = step.transit || step.transitDetails
  if (transit) {
    const line = transit.line?.short_name || transit.line?.name || transit.transitLine?.shortName || transit.transitLine?.name || '大眾運輸'
    const departure = transit.departure_stop?.name || transit.departureStop?.name || ''
    const arrival = transit.arrival_stop?.name || transit.arrivalStop?.name || ''
    const headsign = (transit.headsign || transit.transitLine?.headsign) ? `（往 ${transit.headsign || transit.transitLine?.headsign}）` : ''
    const numStops = (transit.num_stops || transit.stopCount) ? `，共 ${transit.num_stops || transit.stopCount} 站` : ''
    if (departure && arrival) {
      return `從 ${departure} 搭乘 ${line}${headsign} 至 ${arrival}${numStops}`
    }
    return `搭乘 ${line}${headsign}${numStops}`
  }

  let text = step.instructions ? step.instructions.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim() : ''

  if (!text) {
    const travelModeStr = String(step.travel_mode || step.travelMode || '')
    if (travelModeStr.includes('WALK') || actualMode === window.google?.maps?.TravelMode?.WALKING) {
      return '沿騎樓／人行道步行前進'
    }
    if (travelModeStr.includes('BICYCLE') || actualMode === window.google?.maps?.TravelMode?.BICYCLING) {
      return '沿自行車專用道／市區林蔭道路騎乘 YouBike 前進'
    }
    return '依地圖路線前進'
  }

  // Comprehensive Google Directions English -> zh-TW dictionary replacement
  const translations = [
    { re: /\bHead\s+north\s+on\b/gi, zh: '往北沿著' },
    { re: /\bHead\s+south\s+on\b/gi, zh: '往南沿著' },
    { re: /\bHead\s+east\s+on\b/gi, zh: '往東沿著' },
    { re: /\bHead\s+west\s+on\b/gi, zh: '往西沿著' },
    { re: /\bHead\s+northeast\s+on\b/gi, zh: '往東北沿著' },
    { re: /\bHead\s+northwest\s+on\b/gi, zh: '往西北沿著' },
    { re: /\bHead\s+southeast\s+on\b/gi, zh: '往東南沿著' },
    { re: /\bHead\s+southwest\s+on\b/gi, zh: '往西南沿著' },
    { re: /\bTurn\s+right\s+onto\b/gi, zh: '右轉進入' },
    { re: /\bTurn\s+left\s+onto\b/gi, zh: '左轉進入' },
    { re: /\bTurn\s+right\b/gi, zh: '右轉' },
    { re: /\bTurn\s+left\b/gi, zh: '左轉' },
    { re: /\bSlight\s+right\s+onto\b/gi, zh: '向右微轉進入' },
    { re: /\bSlight\s+left\s+onto\b/gi, zh: '向左微轉進入' },
    { re: /\bSlight\s+right\b/gi, zh: '向右微轉' },
    { re: /\bSlight\s+left\b/gi, zh: '向左微轉' },
    { re: /\bContinue\s+straight\s+onto\b/gi, zh: '直行進入' },
    { re: /\bContinue\s+onto\b/gi, zh: '繼續前行進入' },
    { re: /\bContinue\s+straight\b/gi, zh: '直行' },
    { re: /\bWalk\s+to\b/gi, zh: '步行至' },
    { re: /\bTake\s+the\b/gi, zh: '搭乘' },
    { re: /\bDestination\s+will\s+be\s+on\s+the\s+right\b/gi, zh: '目的地在右側' },
    { re: /\bDestination\s+will\s+be\s+on\s+the\s+left\b/gi, zh: '目的地在左側' },
    { re: /\bAt\s+the\s+roundabout,\s+take\s+the\b/gi, zh: '於圓環進入' },
    { re: /\bPass\s+by\b/gi, zh: '經過' },
  ]

  for (const { re, zh } of translations) {
    text = text.replace(re, zh)
  }

  return text
}

const preferenceColorMap = {
  fastest: '#10b981',      // Emerald Green
  wheelchair: '#6366f1',   // Indigo (Accessible)
  more_bus: '#2563eb',     // Royal Blue (Bus)
  more_subway: '#059669',  // MRT Green
  less_walking: '#0d9488', // Teal
  more_shading: '#15803d', // Shaded Forest Green
  less_crowded: '#0891b2', // Cyan
  mixed: '#ea580c',        // YouBike Sunset Orange
}

function queryDirectionsService(service, req) {
  return new Promise((resolve, reject) => {
    service.route(req, (result, status) => {
      if (status === 'OK' && result?.routes?.[0]) {
        resolve(result)
      } else {
        reject(new Error(`Directions status: ${status}`))
      }
    })
  })
}

async function renderGoogleDirections(origin, destination, preference = 'fastest', isCurrentRequest = () => true) {
  if (!map.value || !window.google?.maps?.DirectionsService) return null
  if (!isCurrentRequest()) return null

  const directionsService = new window.google.maps.DirectionsService()
  const originLatLng = new window.google.maps.LatLng(origin.lat, origin.lng)
  const destLatLng = new window.google.maps.LatLng(destination.lat, destination.lng)

  let primaryMode = window.google.maps.TravelMode.TRANSIT
  let transitOptions = {}

  if (preference === 'mixed') {
    primaryMode = window.google.maps.TravelMode.BICYCLING
  } else if (preference === 'more_bus') {
    transitOptions = {
      modes: [window.google.maps.TransitMode.BUS],
    }
  } else if (preference === 'more_subway') {
    transitOptions = {
      modes: [window.google.maps.TransitMode.SUBWAY, window.google.maps.TransitMode.TRAIN],
    }
  } else if (preference === 'less_walking') {
    transitOptions = {
      routingPreference: window.google.maps.TransitRoutePreference.LESS_WALKING,
    }
  }

  let response = null
  let actualMode = primaryMode

  // Primary attempt with selected mode & options
  try {
    const req = {
      origin: originLatLng,
      destination: destLatLng,
      travelMode: primaryMode,
    }
    if (primaryMode === window.google.maps.TravelMode.TRANSIT) {
      req.transitOptions = transitOptions
    }
    response = await queryDirectionsService(directionsService, req)
  } catch (err) {
    console.warn(`Primary DirectionsService mode ${primaryMode} failed (${err.message}), trying street road modes...`)
  }

  // Fallback 1: If TRANSIT failed (e.g. no transit schedule at this hour), try WALKING / BICYCLING / DRIVING
  if (!response) {
    const fallbacks = [
      window.google.maps.TravelMode.TRANSIT,
      window.google.maps.TravelMode.WALKING,
      window.google.maps.TravelMode.BICYCLING,
      window.google.maps.TravelMode.DRIVING,
    ]
    for (const fbMode of fallbacks) {
      if (fbMode === primaryMode) continue
      try {
        response = await queryDirectionsService(directionsService, {
          origin: originLatLng,
          destination: destLatLng,
          travelMode: fbMode,
        })
        if (response) {
          actualMode = fbMode
          break
        }
      } catch (e) {
        // continue trying next mode
      }
    }
  }

  if (!response || !isCurrentRequest()) return null

  const route = response.routes[0]
  const leg = route.legs[0]
  if (!leg) return null

  const strokeColor = preferenceColorMap[preference] || '#10b981'

  clearMapRouteLayers()

  // Draw real street-following polyline
  const polyline = new window.google.maps.Polyline({
    path: route.overview_path,
    geodesic: true,
    strokeColor: strokeColor,
    strokeOpacity: 0.95,
    strokeWeight: 6,
    map: map.value,
  })
  currentRoutePolylines.push(polyline)

  const bounds = new window.google.maps.LatLngBounds()
  route.overview_path.forEach((pt) => bounds.extend(pt))
  fitRouteInVisibleMap(bounds)

  return {
    isGoogleRoute: true,
    totalDurationMinutes: Math.max(1, Math.round((leg.duration?.value || 0) / 60)),
    totalDistanceMeters: leg.distance?.value || 0,
    transitSummary: actualMode === window.google.maps.TravelMode.BICYCLING
      ? `單車 / YouBike 騎乘約 ${leg.duration?.text || '時間待確認'}`
      : actualMode === window.google.maps.TravelMode.WALKING
      ? `步行路徑約 ${leg.duration?.text || '時間待確認'}`
      : `大眾運輸約 ${leg.duration?.text || '時間待確認'}`,
    segments: (leg.steps || []).map((step) => ({
      mode: step.travel_mode || (actualMode === window.google.maps.TravelMode.BICYCLING ? 'BICYCLE' : 'TRANSIT'),
      instruction: formatZhTwStepInstruction(step, actualMode),
      duration_minutes: Math.max(1, Math.round((step.duration?.value || 0) / 60)),
      distance_meters: step.distance?.value || 0,
      is_shaded_or_underground: preference === 'more_shading' || step.instructions?.includes('捷運') || step.instructions?.includes('地下'),
    })),
  }
}

async function selectRoutePreference(prefId, place) {
  routePreference.value = prefId
  if (place) {
    await planRouteToPlace(place)
  }
}

async function toggleSwapRoute(place) {
  routeOriginSwapped.value = !routeOriginSwapped.value
  Snackbar.info(routeOriginSwapped.value ? '已切換為返程路線 (從目標地點出發)' : '已切換為去程路線 (從目前位置出發)')
  if (place) {
    await planRouteToPlace(place)
  }
}

async function selectDepartureTime(timeLabel, place) {
  routeDepartureTime.value = timeLabel
  showDepartureDropdown.value = false
  Snackbar.info(`已更新出發時間設定：${timeLabel}`)
  if (place) {
    await planRouteToPlace(place)
  }
}

async function planRouteToPlace(place) {
  if (!place?.position) {
    Snackbar.warning('這筆活動沒有可信座標，無法規劃路線')
    return
  }
  const requestVersion = ++routeRequestVersion
  const isCurrentRouteRequest = () => requestVersion === routeRequestVersion
  routeLoading.value = true
  try {
    if (!hasUserLocation.value) {
      const located = await requestCurrentLocation({ center: false, showFeedback: true })
      if (!isCurrentRouteRequest()) return
      if (!located) {
        Snackbar.warning('未取得目前位置，因此沒有產生可能錯誤的起點路線')
        return
      }
    }

    const originCoords = routeOriginSwapped.value
      ? { lat: place.position.lat, lng: place.position.lng }
      : { lat: userLocation.value.lat, lng: userLocation.value.lng }
    const destCoords = routeOriginSwapped.value
      ? { lat: userLocation.value.lat, lng: userLocation.value.lng }
      : { lat: place.position.lat, lng: place.position.lng }
    const destName = routeOriginSwapped.value ? '出發地 (台北市區)' : place.name

    const route = await routesService.computeRoute({
      originLat: originCoords.lat,
      originLng: originCoords.lng,
      destLat: destCoords.lat,
      destLng: destCoords.lng,
      destName: destName,
      prioritizeShade: routePreference.value === 'more_shading',
      shadeTimePeriod: shadeTimePeriod.value,
      preference: routePreference.value,
      wheelchairAccessible: routePreference.value === 'wheelchair',
      departureTime: routeDepartureTime.value,
    })
    if (!isCurrentRouteRequest()) return

    let googleRoute = null
    if (map.value && window.google?.maps) {
      try {
        googleRoute = await renderGoogleDirections(originCoords, destCoords, routePreference.value, isCurrentRouteRequest)
      } catch (directionsError) {
        console.warn('Google Directions route failed:', directionsError)
      }
    }
    if (!isCurrentRouteRequest()) return

    if (!googleRoute && map.value && window.google?.maps) {
      clearMapRouteLayers()
      const strokeColor = preferenceColorMap[routePreference.value] || '#10b981'

      // If backend gave real decoded polyline use it, otherwise generate realistic street-grid path
      const displayPath = (route.hasRealPath && route.path?.length > 3)
        ? route.path
        : [
            { lat: originCoords.lat, lng: originCoords.lng },
            { lat: originCoords.lat + (destCoords.lat - originCoords.lat) * 0.5, lng: originCoords.lng },
            { lat: originCoords.lat + (destCoords.lat - originCoords.lat) * 0.5, lng: destCoords.lng },
            { lat: destCoords.lat, lng: destCoords.lng },
          ]

      currentPolyline = new window.google.maps.Polyline({
        path: displayPath,
        geodesic: true,
        strokeColor: strokeColor,
        strokeOpacity: 0.9,
        strokeWeight: 6,
        map: map.value,
      })
      currentRoutePolylines.push(currentPolyline)

      const bounds = new window.google.maps.LatLngBounds()
      displayPath.forEach((pt) => bounds.extend(pt))
      fitRouteInVisibleMap(bounds)
    }

    if (!googleRoute && !route.hasRealPath) {
      clearMapRouteLayers()
      activeRoute.value = {
        ...route,
        pathUnavailable: true,
        routeAdvice: `${route.routeAdvice} 路徑細節暫時無法繪製，請開啟導航確認道路與班次。`,
      }
      Snackbar.warning(`${activeShadeScenario.value.label}遮蔭情境已產生，地圖路徑暫未繪製`)
      return
    }

    const shadedGoogleRoute = googleRoute
      ? applyShadeScenarioToGoogleRoute(googleRoute, shadeTimePeriod.value)
      : null
    activeRoute.value = googleRoute
      ? {
          ...route,
          ...shadedGoogleRoute,
          preference: routePreference.value,
          multimodal: route.multimodal,
          accessibilityNote: route.accessibilityNote,
          crowdNote: route.crowdNote,
        }
      : route

    Snackbar.success(`已規劃【${routePreferencesList.find(p => p.id === routePreference.value)?.label || '自訂'}】路線：${activeRoute.value.transitSummary}`)
  } catch (err) {
    if (!isCurrentRouteRequest()) return
    console.error('Route plan error:', err)
    activeRoute.value = null
    clearMapRouteLayers()
    Snackbar.error('路線規劃失敗，未顯示模擬路線')
  } finally {
    if (isCurrentRouteRequest()) routeLoading.value = false
  }
}

function resetRouteState() {
  routeRequestVersion += 1
  routeLoading.value = false
  activeRoute.value = null
  clearMapRouteLayers()
}

function clearRoute() {
  resetRouteState()
  centerMap()
  Snackbar.info('已清除路線')
}

// Heatmap Layer Toggle (PRD 8)
function clearHeatmapOverlays() {
  while (heatmapOverlays.length > 0) {
    heatmapOverlays.pop()?.setMap(null)
  }
}

function heatColor(score) {
  if (score >= 80) return '#d94f3d'
  if (score >= 65) return '#ef7f4d'
  if (score >= 40) return '#e0aa3e'
  return '#4b9278'
}

async function toggleHeatmap() {
  heatmapVisible.value = !heatmapVisible.value
  if (!map.value || !window.google?.maps) return

  if (heatmapVisible.value) {
    try {
      const points = await crowdService.getHeatmapPoints()
      if (!points.length) throw new Error('Crowd API returned no heatmap points')

      clearHeatmapOverlays()
      const { Circle } = await window.google.maps.importLibrary('maps')
      points.forEach((point) => {
        const score = Number(point.crowd_score ?? point.weight * 100)
        heatmapOverlays.push(new Circle({
          map: map.value,
          center: { lat: Number(point.latitude), lng: Number(point.longitude) },
          radius: 240 + Math.max(0.1, Number(point.weight)) * 460,
          fillColor: heatColor(score),
          fillOpacity: 0.22 + Math.max(0.1, Number(point.weight)) * 0.22,
          strokeColor: heatColor(score),
          strokeOpacity: 0.7,
          strokeWeight: 2,
          clickable: false,
          zIndex: Math.round(score),
        }))
      })
      heatmapIsMock.value = points.every((point) => point.data_source !== 'live')
    Snackbar.success(heatmapIsMock.value ? '已顯示示意人流' : '已開啟人流圖層')
    } catch (err) {
      console.error('Heatmap load error:', err)
      heatmapVisible.value = false
      Snackbar.error('人潮圖層載入失敗')
    }
  } else {
    clearHeatmapOverlays()
    Snackbar.info('已關閉人潮熱力圖')
  }
}

function toggleSheet() {
  if (sheetMinimized.value) {
    sheetMinimized.value = false
    sheetExpanded.value = false
  } else if (sheetExpanded.value) {
    sheetExpanded.value = false
  } else {
    sheetExpanded.value = true
  }
  sheetDragHeight.value = null
  nextTick(refocusSelectedPlace)
}

function minimizeSheet() {
  sheetExpanded.value = false
  sheetMinimized.value = true
  sheetDragHeight.value = null
  nextTick(refocusSelectedPlace)
}

function getSheetSnapHeights() {
  const minimized = window.innerWidth <= 620 ? 106 : 72
  const half = Math.min(560, Math.max(340, window.innerHeight * 0.46))
  const expanded = Math.max(half, window.innerHeight * 0.88)
  return { minimized, half, expanded }
}

function startSheetDrag(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  sheetDragging.value = true
  sheetDragStartY = event.clientY
  sheetDragStartHeight = sheetElement.value?.getBoundingClientRect().height ?? window.innerHeight * 0.48
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function moveSheetDrag(event) {
  if (!sheetDragging.value) return
  const { minimized, expanded } = getSheetSnapHeights()
  sheetDragHeight.value = Math.min(expanded, Math.max(minimized, sheetDragStartHeight + sheetDragStartY - event.clientY))
}

function endSheetDrag(event) {
  if (!sheetDragging.value) return
  sheetDragging.value = false
  event.currentTarget.releasePointerCapture?.(event.pointerId)
  const currentHeight = sheetDragHeight.value ?? sheetDragStartHeight
  const { minimized, half, expanded } = getSheetSnapHeights()
  if (currentHeight < (minimized + half) / 2) {
    sheetMinimized.value = true
    sheetExpanded.value = false
  } else if (currentHeight < (half + expanded) / 2) {
    sheetMinimized.value = false
    sheetExpanded.value = false
  } else {
    sheetMinimized.value = false
    sheetExpanded.value = true
  }
  sheetDragHeight.value = null
  nextTick(refocusSelectedPlace)
}

function useQuickPrompt(value) {
  prompt.value = value
  nextTick(() => document.querySelector('.prompt-input textarea, .prompt-input input')?.focus())
}

// PRD Multi-Criteria Reasoning & SSE Exploration
async function explore() {
  if (isExploring.value) return
  if (!prompt.value.trim()) {
    Snackbar.warning('請先輸入想找的活動')
    return
  }

  isExploring.value = true
  aiReply.value = ''
  aiError.value = ''
  aiThoughtSteps.value = []
  aiParsedCriteria.value = null
  aiRecommendations.value = []
  aiEvaluatedCount.value = 0
  syncMarkerSelection()
  aiDispersalSummary.value = ''
  aiOneSentenceSummary.value = ''

  try {
    const result = await agentService.recommend({
      message: prompt.value.trim(),
      user_id: activePersona.value.id,
      user_latitude: userLocation.value.lat,
      user_longitude: userLocation.value.lng,
      session_id: agentSessionId.value,
      events: places.value,
      onStreamEvent: (type, data) => {
        if (type === 'thought') {
          aiThoughtSteps.value.push(data)
        } else if (type === 'understanding') {
          aiParsedCriteria.value = data
        } else if (type === 'markdown_chunk') {
          aiReply.value += data.chunk || data.text || ''
        } else if (type === 'recommendation_cards') {
          aiRecommendations.value = data.cards || []
          aiDispersalSummary.value = data.dispersal_summary || ''
          aiEvaluatedCount.value = data.evaluated_count || 0
          syncMarkerSelection()
        } else if (type === 'done') {
          aiOneSentenceSummary.value = data.one_sentence_summary || ''
          agentSessionId.value = data.session_id || agentSessionId.value
        }
      },
    })

    if (result.reply && !aiReply.value) {
      aiReply.value = result.reply
    }
    if (result.thought_steps?.length && !aiThoughtSteps.value.length) {
      aiThoughtSteps.value = result.thought_steps
    }
    if (result.parsed_criteria && !aiParsedCriteria.value) {
      aiParsedCriteria.value = result.parsed_criteria
    }
    if (result.recommendations?.length && !aiRecommendations.value.length) {
      aiRecommendations.value = result.recommendations
      syncMarkerSelection()
    }
    if (result.dispersal_summary && !aiDispersalSummary.value) {
      aiDispersalSummary.value = result.dispersal_summary
    }
    if (result.evaluated_count) {
      aiEvaluatedCount.value = result.evaluated_count
    }

    activeFilter.value = '為你推薦'

    // If top recommendation has coordinates, highlight on map
    const topRec = aiRecommendations.value[0]?.event
    if (topRec) {
      const matchedPlace = places.value.find((p) => p.id === topRec.id)
      if (matchedPlace) selectPlace(matchedPlace)
    }

    sheetMinimized.value = false
    sheetExpanded.value = true
    await nextTick()
    document.querySelector('.agent-recommendations-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })

    Snackbar.success('推薦已更新')
  } catch (error) {
    aiError.value = '推薦暫時無法更新，仍可直接瀏覽活動清單。'
    console.error(error)
  } finally {
    isExploring.value = false
  }
}

function formatAgentEventDate(event) {
  if (!event?.start_time) return ''
  const start = new Date(event.start_time)
  if (Number.isNaN(start.getTime())) return ''
  return start.toLocaleString('zh-TW', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function cleanUiLabel(label, fallback = '') {
  return String(label || fallback).replace(/^[^\p{L}\p{N}]+/u, '').trim()
}

// PRD Section 6 Stage 10 Feedback
async function handleFeedback(eventId, isHelpful, tag) {
  feedbackMap.value.set(eventId, { isHelpful, tag })
  try {
    await agentService.submitFeedback({
      session_id: 'session_' + activePersona.value.id,
      event_id: eventId,
      is_helpful: isHelpful,
      feedback_tag: tag,
    })
    Snackbar.success(isHelpful ? '感謝你的好評！' : '感謝回饋，將為你調整推薦權重')
  } catch (err) {
    Snackbar.success('感謝你的回饋！')
  }
}

function updateUserLocationMarker() {
  if (!map.value || !window.google?.maps || !hasUserLocation.value) return
  userLocationOverlay?.setMap(null)

  const content = document.createElement('div')
  content.className = 'map-user-location'
  content.setAttribute('title', '你的目前位置')

  const overlay = new window.google.maps.OverlayView()
  overlay.onAdd = () => overlay.getPanes().overlayMouseTarget.appendChild(content)
  overlay.draw = () => {
    const point = overlay.getProjection().fromLatLngToDivPixel(userLocation.value)
    if (!point) return
    content.style.left = `${point.x}px`
    content.style.top = `${point.y}px`
  }
  overlay.onRemove = () => content.remove()
  overlay.setMap(map.value)
  userLocationOverlay = overlay
}

function requestCurrentLocation({ center = true, showFeedback = true } = {}) {
  if (!navigator.geolocation) {
    locationState.value = 'unsupported'
    if (showFeedback) Snackbar.warning('此瀏覽器不支援定位功能')
    return Promise.resolve(false)
  }

  locationState.value = 'requesting'
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        userLocation.value = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        }
        hasUserLocation.value = true
        locationState.value = 'ready'
        updateUserLocationMarker()
        if (center && map.value) {
          map.value.panTo(userLocation.value)
          map.value.setZoom(14)
        }
        await loadWeather()
        if (showFeedback) Snackbar.success('已更新為你的目前位置')
        resolve(true)
      },
      (error) => {
        locationState.value = error.code === error.PERMISSION_DENIED ? 'denied' : 'error'
        if (showFeedback) {
          Snackbar.warning(error.code === error.PERMISSION_DENIED
            ? '定位權限未開啟，目前使用台北車站作為預設位置'
            : '暫時無法取得目前位置')
        }
        resolve(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    )
  })
}

async function centerMap() {
  if (!map.value) return
  if (!hasUserLocation.value) {
    await requestCurrentLocation({ center: true, showFeedback: true })
    return
  }
  map.value.panTo(userLocation.value)
  map.value.setZoom(14)
}

function addMarker(place) {
  if (!place.position) return
  const content = document.createElement('div')
  content.className = 'map-place-marker'
  content.style.setProperty('--pin-color', place.color)
  content.setAttribute('role', 'button')
  content.setAttribute('tabindex', '0')
  content.setAttribute('aria-label', `查看 ${place.name}`)

  const pin = document.createElement('span')
  pin.className = 'map-place-marker__pin'
  const pinLabel = document.createElement('span')
  pinLabel.textContent = place.label
  pin.appendChild(pinLabel)

  const label = document.createElement('span')
  label.className = 'map-place-marker__label'
  label.textContent = place.shortName
  content.append(pin, label)

  const overlay = new window.google.maps.OverlayView()
  overlay.onAdd = () => overlay.getPanes().overlayMouseTarget.appendChild(content)
  overlay.draw = () => {
    const point = overlay.getProjection().fromLatLngToDivPixel(place.position)
    if (!point) return
    content.style.left = `${point.x}px`
    content.style.top = `${point.y}px`
  }
  overlay.onRemove = () => content.remove()
  overlay.setMap(map.value)

  content.addEventListener('click', () => openPlaceDetails(place))
  content.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openPlaceDetails(place)
    }
  })
  markers.set(place.id, { content, overlay })
}

async function initMap() {
  mapState.value = 'loading'
  window.gm_authFailure = () => {
    mapState.value = 'error'
    mapError.value = '地圖暫時無法顯示，活動清單仍可使用。'
  }

  const mapsApiKey = rawEnvMapsKey
  if (!mapsApiKey) {
    mapState.value = 'error'
    mapError.value = '地圖暫時無法顯示，活動清單仍可使用。'
    return
  }

  try {
    const loader = new Loader({
      apiKey: mapsApiKey,
      version: 'weekly',
      language: 'zh-TW',
      region: 'TW',
      libraries: ['geometry'],
    })
    await loader.load()
    map.value = new window.google.maps.Map(mapElement.value, {
      center: TAIPEI_CENTER,
      zoom: 12,
      minZoom: 11,
      maxZoom: 17,
      disableDefaultUI: true,
      clickableIcons: false,
      gestureHandling: 'greedy',
      styles: [
        {
          featureType: 'poi',
          elementType: 'all',
          stylers: [{ visibility: 'off' }],
        },
      ],
    })
    places.value.filter((place) => place.position).forEach(addMarker)
    syncMarkerSelection()
    mapState.value = 'ready'
  } catch (error) {
    mapState.value = 'error'
    mapError.value = '地圖暫時無法顯示，活動清單仍可使用。'
  }
}

onMounted(async () => {
  await Promise.all([
    loadWeather(),
    loadUserAndPersonas(),
    loadQuickPrompts(),
    loadEvents(),
  ])
  await initMap()
  requestCurrentLocation({ center: false, showFeedback: false })
})
</script>

<template>
  <main class="app-shell" :class="{ 'sheet-expanded': sheetExpanded, 'sheet-minimized': sheetMinimized }">
    <!-- Map Canvas Section -->
    <section class="map-stage" aria-label="台北市地圖">
      <div ref="mapElement" class="google-map"></div>
      <div v-if="mapState === 'loading'" class="map-state map-loading">
        <div class="loader-orbit"></div>
          <span>正在載入地圖…</span>
      </div>
      <div v-if="mapState === 'error'" class="map-state map-error">
        <span class="error-mark">!</span>
         <strong>地圖暫時無法顯示</strong>
        <small>{{ mapError }}</small>
      </div>

      <!-- Topbar Header -->
      <header class="topbar">
        <div class="brand-lockup" aria-label="SideQuest 城市探索">
          <img class="brand-mark" src="/brand/sidequest-mark.png" alt="SideQuest 圖形標誌" />
          <div>
            <div class="brand-name">sidequest<span>.</span></div>
            <div class="brand-caption">城市裡的下一站</div>
          </div>
        </div>
        <div class="topbar-actions">
          <button class="city-pill" @click="centerMap" aria-label="切換城市或置中">
            <span class="status-dot"></span> 台北市 <span class="caret">⌄</span>
          </button>
          <button
            class="avatar-button"
            :title="`目前角色：${activePersona.name}`"
            aria-label="切換測試 Persona 角色"
            @click="showPersonaModal = true"
          >
            {{ avatarInitials }}
          </button>
        </div>
      </header>

      <!-- Live Microclimate & Solar Pill -->
       <div class="map-context-pill" @click="loadWeather" title="重新整理天氣與日照資料">
        <span class="context-icon">☀</span>
        <div>
          <strong>{{ weather.temperature }}°C</strong>
          <span>體感 {{ weather.apparentTemperature }}°C</span>
        </div>
        <i></i>
        <div>
          <strong>UV {{ weather.uvIndex }}</strong>
          <span>{{ weather.sunExposureLevel === 'HIGH' ? '高曝曬' : '中等日照' }}</span>
        </div>
        <div class="refresh-label" :class="{ spinning: weatherLoading }">
           {{ weather.isMock ? '示意資料' : '即時資料' }}
        </div>
      </div>

      <!-- Map Floating Controls -->
      <button
        class="map-control locate-control"
        :class="{ active: hasUserLocation }"
        :aria-label="hasUserLocation ? '回到我的目前位置' : '取得我的目前位置'"
        :title="locationState === 'requesting' ? '正在取得位置…' : (hasUserLocation ? '回到我的目前位置' : '取得我的目前位置')"
        @click="centerMap"
      >◎</button>
      <button
        class="map-control heatmap-control"
        :class="{ active: heatmapVisible }"
        aria-label="切換人潮熱力圖圖層"
        @click="toggleHeatmap"
      >
        ◌
      </button>
      <div class="map-control-stack">
        <button class="map-control" aria-label="放大地圖" @click="map?.setZoom((map?.getZoom() ?? 12) + 1)">＋</button>
        <button class="map-control" aria-label="縮小地圖" @click="map?.setZoom((map?.getZoom() ?? 12) - 1)">−</button>
      </div>

      <!-- Active Route Notification Bar -->
      <div v-if="activeRoute" class="map-route-banner">
        <div class="route-banner-icon">⌁</div>
        <div class="route-banner-info">
          <strong>{{ activeRoute.destination }}</strong>
          <span>{{ activeRoute.transitSummary }} · {{ activeShadeScenario.label }}遮蔭情境 {{ activeRoute.shadePercentage }}%</span>
        </div>
        <button type="button" class="route-banner-close" aria-label="清除路線" @click="clearRoute">×</button>
      </div>

      <div class="map-legend">
        <span><b class="legend-dot legend-cool"></b>人流舒適 (&lt;35)</span>
        <span><b class="legend-dot legend-warm"></b>人潮熱門 (&gt;65)</span>
         <span v-if="heatmapVisible && heatmapIsMock">示意資料</span>
      </div>
    </section>

    <!-- Bottom Sliding Sheet -->
    <section
      ref="sheetElement"
      class="bottom-sheet"
      :class="{ expanded: sheetExpanded, minimized: sheetMinimized, dragging: sheetDragging }"
      :style="sheetStyle"
      aria-label="SideQuest 探索面板"
    >
      <div class="sheet-grabber">
        <button
          class="sheet-grabber-control"
          type="button"
          :aria-label="sheetHandleLabel"
          @click="toggleSheet"
          @pointerdown="startSheetDrag"
          @pointermove="moveSheetDrag"
          @pointerup="endSheetDrag"
          @pointercancel="endSheetDrag"
        >
          <span class="sheet-handle"></span>
        </button>
        <button
          v-if="!sheetMinimized"
          class="sheet-minimize-button"
          type="button"
          aria-label="將探索面板收到底"
          @click="minimizeSheet"
        >⌄</button>
      </div>

      <!-- Activity Detail View -->
      <article v-if="detailPlace" class="place-detail-view">
        <header class="detail-header">
          <button type="button" class="detail-back" aria-label="返回活動列表" @click="closePlaceDetails">←</button>
           <span>活動詳情</span>
          <button type="button" class="detail-close" aria-label="關閉詳細資料" @click="closePlaceDetails">×</button>
        </header>

        <div class="detail-hero" :style="{ '--detail-color': detailPlace.color }">
          <div class="detail-hero-pin">{{ detailPlace.label }}</div>
          <div class="detail-hero-copy">
            <span>{{ detailPlace.category }} · {{ detailPlace.district }}</span>
            <h1>{{ detailPlace.name }}</h1>
            <strong>{{ detailPlace.address }}</strong>
            <small>{{ detailPlace.dateRange }}</small>
          </div>
        </div>

        <nav class="detail-quick-actions" aria-label="活動動作">
          <button type="button" class="primary" :disabled="routeLoading || !detailPlace.position" @click="planRouteToPlace(detailPlace)">
            <span aria-hidden="true">⌁</span>
            <strong>{{ routeLoading ? '規劃中…' : '規劃路線' }}</strong>
          </button>
          <button type="button" @click="revealPlaceOnMap(detailPlace)">
            <span aria-hidden="true">⌖</span><strong>查看地圖</strong>
          </button>
          <button
            type="button"
            :class="{ favorited: favoritePlaceIds.has(detailPlace.id) }"
            @click="toggleBookmark(detailPlace)"
          >
            <span aria-hidden="true">{{ favoritePlaceIds.has(detailPlace.id) ? '♥' : '♡' }}</span>
            <strong>{{ favoritePlaceIds.has(detailPlace.id) ? '已收藏' : '收藏' }}</strong>
          </button>
          <a v-if="detailPlace.sourceUrl" :href="detailPlace.sourceUrl" target="_blank" rel="noopener noreferrer">
            <span aria-hidden="true">↗</span><strong>活動來源</strong>
          </a>
        </nav>

        <!-- Route Guidance Card if computed -->
        <div v-if="activeRoute" class="route-planning-container">
          <!-- Top Route Controls Bar -->
          <div class="route-top-bar">
            <button type="button" class="route-back-btn" @click="resetRouteState" title="關閉路線">
              <span aria-hidden="true">✕</span> 清除路線
            </button>
            <div class="route-time-selector-wrapper">
              <button
                type="button"
                class="route-time-btn"
                @click="showDepartureDropdown = !showDepartureDropdown"
              >
                 <span>◷</span>
                <strong>{{ routeDepartureTime }}</strong>
                <span class="chevron">⌄</span>
              </button>
              <div v-if="showDepartureDropdown" class="route-time-dropdown">
                <button
                  v-for="opt in departureTimeOptions"
                  :key="opt"
                  type="button"
                  :class="{ active: routeDepartureTime === opt }"
                  @click="selectDepartureTime(opt, detailPlace)"
                >
                  {{ opt }}
                </button>
              </div>
            </div>
            <button type="button" class="route-refresh-btn" :disabled="routeLoading" @click="planRouteToPlace(detailPlace)" title="重新整理路線">
              <span>⟳</span>
            </button>
          </div>

          <!-- Origin & Destination Transit Card -->
          <div class="route-od-card">
            <div class="route-od-lines">
              <div class="route-od-point">
                <span class="od-dot origin-dot"></span>
                <div class="od-text">
                  <small>起點</small>
                   <strong>{{ routeOriginSwapped ? detailPlace.name : '目前位置（台北市區）' }}</strong>
                </div>
              </div>
              <div class="od-connector"></div>
              <div class="route-od-point">
                <span class="od-dot dest-dot"></span>
                <div class="od-text">
                  <small>目的地</small>
                   <strong>{{ routeOriginSwapped ? '目前位置（台北市區）' : detailPlace.name }}</strong>
                </div>
              </div>
            </div>
            <button
              type="button"
              class="route-swap-btn"
              title="對調出發地與目的地"
              @click="toggleSwapRoute(detailPlace)"
            >
              <span>⇅</span>
            </button>
          </div>

          <!-- Horizontal Route Preferences Tab Pills -->
          <div class="route-pref-scroller" role="tablist" aria-label="路線偏好選擇">
            <button
              v-for="pref in routePreferencesList"
              :key="pref.id"
              type="button"
              class="route-pref-pill"
              :class="{ active: routePreference === pref.id }"
              :disabled="routeLoading"
              @click="selectRoutePreference(pref.id, detailPlace)"
            >
              <span class="pref-icon">{{ pref.icon }}</span>
              <span class="pref-label">{{ pref.label }}</span>
            </button>
          </div>

          <!-- Multimodal Summary Comparison Grid (Top 4 Metrics) -->
          <div class="multimodal-overview-grid">
            <div class="modal-box" :class="{ highlight: routePreference === 'less_walking' }">
              <div class="modal-box-header">
                <span class="modal-icon">🚶</span>
                <span class="modal-title">步行</span>
              </div>
              <div class="modal-metrics">
                <strong>{{ activeRoute.multimodal?.walk_calories || 376 }} <small>卡</small></strong>
                <span>{{ activeRoute.multimodal?.walk_duration_minutes || 91 }} 分鐘</span>
              </div>
            </div>

            <div class="modal-box" :class="{ highlight: routePreference === 'mixed' }">
              <div class="modal-box-header">
                <span class="modal-icon">🚲</span>
                <span class="modal-title">單車</span>
              </div>
              <div class="modal-metrics">
                <strong>{{ activeRoute.multimodal?.bike_calories || 128 }} <small>卡</small></strong>
                <span>{{ activeRoute.multimodal?.bike_duration_minutes || 31 }} 分鐘 · $20</span>
              </div>
            </div>

            <div class="modal-box">
              <div class="modal-box-header">
                <span class="modal-icon">🚕</span>
                <span class="modal-title">計程車</span>
              </div>
              <div class="modal-metrics">
                <strong>~{{ activeRoute.multimodal?.taxi_duration_minutes || 20 }} <small>分鐘</small></strong>
                <span>約 NT$ {{ activeRoute.multimodal?.taxi_cost_twd || 195 }}</span>
              </div>
            </div>

            <div class="modal-box highlight-transit">
              <div class="modal-box-header">
                <span class="modal-icon">🚇</span>
                <span class="modal-title">大眾運輸</span>
              </div>
              <div class="modal-metrics">
                <strong>{{ activeRoute.totalDurationMinutes }} <small>分鐘</small></strong>
                <span class="shade-pill">◒ {{ activeRoute.shadePercentage }}% 步行遮蔭</span>
              </div>
            </div>
          </div>

          <!-- Detailed YouBike 2.0 Card (Option 1) -->
          <div class="youbike-option-card">
            <div class="option-card-header">
              <div class="option-title-group">
                <span class="badge-youbike">🚲 YouBike 2.0</span>
                <span class="option-price">$20.00</span>
              </div>
              <div class="option-duration">
                <strong>{{ activeRoute.multimodal?.bike_duration_minutes || 34 }}</strong>
                <small>分鐘</small>
              </div>
            </div>
            <div class="option-meta-row">
              <span>📍 {{ activeRoute.multimodal?.bike_station || '周邊租賃站點' }} · 可借 5 輛 / 可還 12 位</span>
            </div>
            <p class="option-desc">
              沿著林蔭單車道前行，預估消耗 <strong>{{ activeRoute.multimodal?.bike_calories || 128 }}</strong> 大卡。
            </p>
          </div>

          <!-- Main Transit Plan Card (Option 2 - Custom to Preference) -->
          <div class="transit-plan-card">
            <div class="route-card-header">
              <div>
                <span class="route-tag">
                  {{ activeShadeScenario.label }} ·
                  {{ routePreferencesList.find(p => p.id === routePreference)?.icon }}
                  {{ routePreferencesList.find(p => p.id === routePreference)?.label }}推薦
                  {{ activeRoute.pathUnavailable ? '· 路徑待確認' : '' }}
                </span>
                <h3>{{ activeRoute.transitSummary }}</h3>
              </div>
              <div class="route-shade-badge">
                <strong>{{ activeRoute.shadePercentage }}%</strong>
                <small>步行遮蔭率</small>
              </div>
            </div>

            <!-- Route Badges Row -->
            <div class="route-feature-badges">
              <span v-if="activeRoute.accessibilityNote" class="feat-badge access-badge">
                ♿ {{ activeRoute.accessibilityNote }}
              </span>
              <span v-if="activeRoute.crowdNote" class="feat-badge crowd-badge">
                👥 {{ activeRoute.crowdNote }}
              </span>
              <span v-if="activeRoute.sunExposureMinutes !== undefined" class="feat-badge sun-badge">
                ☀️ 預估直曬 {{ activeRoute.sunExposureMinutes }} 分鐘
              </span>
            </div>

            <p class="route-advice-copy">{{ activeRoute.routeAdvice }}</p>

            <!-- Step by step directions -->
            <div v-if="activeRoute.segments?.length" class="route-steps">
              <div v-for="(step, idx) in activeRoute.segments" :key="idx" class="route-step">
                <span class="step-num">{{ idx + 1 }}</span>
                <div class="step-info">
                  <div class="step-main">
                    <strong>{{ step.instruction }}</strong>
                    <span v-if="step.is_shaded_or_underground && ['WALK', 'WALKING', 'UNDERGROUND_WALK'].includes(String(step.mode || '').toUpperCase())" class="step-tag-shade">{{ routeStepContext(step) }}</span>
                    <span v-if="step.is_accessible" class="step-tag-access">♿ 無障礙</span>
                  </div>
                  <small>{{ step.duration_minutes }} 分鐘 · {{ step.distance_meters }}m · {{ routeStepContext(step) }} {{ step.transit_line ? `· ${step.transit_line}` : '' }}</small>
                </div>
              </div>
            </div>
          </div>

          <!-- Taxi / Rideshare Estimate Card (Option 3) -->
          <div class="taxi-option-card">
            <div class="option-card-header">
              <div class="option-title-group">
                <span class="badge-taxi">計程車／專車直達</span>
                <span class="option-price">約 NT$ {{ activeRoute.multimodal?.taxi_cost_twd || 195 }}</span>
              </div>
              <div class="option-duration">
                <strong>~{{ activeRoute.multimodal?.taxi_duration_minutes || 20 }}</strong>
                <small>分鐘</small>
              </div>
            </div>
            <div class="taxi-actions">
              <a
                :href="`https://www.google.com/maps/dir/?api=1&origin=${userLocation.lat},${userLocation.lng}&destination=${detailPlace.position?.lat || ''},${detailPlace.position?.lng || ''}&travelmode=driving`"
                target="_blank"
                rel="noopener noreferrer"
                class="taxi-nav-btn"
              >
                <span>↗</span> 開啟導航
              </a>
            </div>
          </div>
        </div>

        <div class="detail-status-grid">
          <div>
            <span>♧</span>
            <small>目前人流</small>
            <strong :class="crowdClass(detailPlace.crowd)">
              {{ crowdLabel(detailPlace.crowd) }}<template v-if="Number.isFinite(detailPlace.crowd)"> ({{ detailPlace.crowd }}){{ detailPlace.crowdIsMock ? '（示意）' : '' }}</template>
            </strong>
          </div>
          <div>
            <span>◒</span>
            <small>曝曬/遮蔽評估</small>
            <strong>{{ detailPlace.isIndoor ? '室內空調 (0% 曝曬)' : (detailPlace.sunLabel || `戶外曝曬 ${detailPlace.sun}%`) }}</strong>
          </div>
          <div>
            <span>◷</span>
            <small>預估距離</small>
            <strong>{{ detailPlace.distance }}</strong>
          </div>
        </div>

        <section class="detail-section">
          <div class="detail-section-heading"><span>01</span><h2>活動資訊</h2></div>
          <dl class="detail-facts">
            <div><dt>日期時段</dt><dd>{{ detailPlace.dateRange }} ({{ detailPlace.time }})</dd></div>
            <div><dt>費用標準</dt><dd>{{ detailPlace.fee || '請見活動來源' }}</dd></div>
            <div><dt>入場方式</dt><dd>{{ detailPlace.admission || '開放參觀' }}</dd></div>
            <div><dt>主辦單位</dt><dd>{{ detailPlace.organizer || '活動主辦方' }}</dd></div>
            <div v-if="detailPlace.tags?.length"><dt>標籤分類</dt><dd>{{ detailPlace.tags.join('、') }}</dd></div>
          </dl>
        </section>

        <section class="detail-section">
          <div class="detail-section-heading"><span>02</span><h2>活動亮點</h2></div>
          <p>{{ detailPlace.description }}</p>
          <div v-if="detailPlace.admission" class="detail-tip">
            <span>↳</span>
            <div><strong>入場提醒</strong><p>{{ detailPlace.admission }}</p></div>
          </div>
        </section>
      </article>

      <!-- Discover / Catalog View -->
      <div v-else class="sheet-discover-view">
        <div class="sheet-header">
          <div>
            <p class="eyebrow"><span class="eyebrow-dot"></span> 為你探索 · {{ activePersona.name }}</p>
            <h1>今天，想怎麼感受台北？</h1>
          </div>
          <div class="header-badges">
            <Badge value="活動資料" type="success" class="data-badge" />
          </div>
        </div>

        <!-- Natural Language Prompt Composer -->
        <div class="prompt-composer">
          <div class="prompt-icon">✦</div>
          <Input
            v-model="prompt"
            class="prompt-input"
            textarea
            :rows="1"
            :resize="false"
            placeholder="告訴我你想找什麼活動？"
            @keydown.enter.exact.prevent="explore"
          />
          <Button class="explore-button" type="primary" round :loading="isExploring" @click="explore">
            <span v-if="!isExploring">開始探索</span>
          </Button>
        </div>

        <!-- Quick Prompts Chips -->
        <div class="quick-prompts">
          <button
            v-for="item in quickPrompts"
            :key="item"
            class="quick-prompt"
            type="button"
            @click="useQuickPrompt(item)"
          >
            {{ item }}
          </button>
        </div>

        <!-- Live Agent Streaming Reasoning & Thoughts -->
        <div v-if="isExploring || aiReply || aiError || aiThoughtSteps.length" class="agent-response" :class="{ failed: aiError }">
          <div class="agent-response-heading">
            <span>✦</span> 推薦分析
            <em v-if="isExploring">正在整理活動、天氣與交通…</em>
          </div>

          <!-- Structured Understanding Criteria (PRD 7.3) -->
          <div v-if="aiParsedCriteria" class="parsed-criteria-row">
            <span class="criteria-badge">時段：{{ aiParsedCriteria.date_time_range || '今日' }}</span>
            <span v-if="aiParsedCriteria.requested_date" class="criteria-badge criteria-date-badge">已鎖定 {{ aiParsedCriteria.requested_date }}</span>
            <span v-if="aiParsedCriteria.occasion" class="criteria-badge">{{ aiParsedCriteria.occasion }}</span>
            <span v-if="aiParsedCriteria.target_district" class="criteria-badge">區域：{{ aiParsedCriteria.target_district }}</span>
            <span v-if="aiParsedCriteria.avoid_crowd" class="criteria-badge">避開人潮</span>
            <span v-if="aiParsedCriteria.prefer_indoor" class="criteria-badge">室內</span>
            <span v-if="aiParsedCriteria.is_free_only" class="criteria-badge">免費入場</span>
          </div>

          <!-- Collapsible Agent Thought Trace -->
          <div v-if="aiThoughtSteps.length" class="agent-thought-container">
            <button
              type="button"
              class="thought-toggle-btn"
              @click="showThoughtTrace = !showThoughtTrace"
            >
              <span>查看分析依據（{{ aiThoughtSteps.length }} 項）</span>
              <small>{{ showThoughtTrace ? '收合' : '展開' }}</small>
            </button>
            <div v-if="showThoughtTrace" class="thought-steps-list">
              <div v-for="step in aiThoughtSteps" :key="step.step" class="thought-step-item">
                <div class="step-index">0{{ step.step }}</div>
                <div class="step-body">
                  <strong>{{ step.title }}</strong>
                  <p>{{ step.thought }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent Markdown Stream Output -->
          <p v-if="isExploring && !aiReply" class="agent-loading-copy">正在整理適合你的活動…</p>
          <p v-else-if="aiError" class="agent-error-copy">{{ aiError }}</p>
          <p v-else class="agent-markdown-text">{{ aiReply }}</p>
        </div>

        <!-- 3 PRD Recommendation Cards (PRD 7.4 & 8.3) -->
        <section v-if="aiRecommendations.length" class="agent-recommendations-section" aria-label="推薦方案">
          <div class="agent-rec-header">
            <div>
              <span class="rec-kicker">推薦方案</span>
              <h2>適合你的活動</h2>
            </div>
            <strong>已比較 {{ aiEvaluatedCount || places.length }} 個活動</strong>
          </div>

          <div class="recommendations-grid">
            <article
              v-for="(card, idx) in aiRecommendations"
              :key="`card-${card.event?.id || idx}`"
              class="rec-card"
              :class="`role-${card.card_role?.toLowerCase()}`"
              role="button"
              tabindex="0"
              @click="card.event?.id && openPlaceDetails(places.find(p => p.id === card.event.id) || card.event)"
              @keydown.enter="card.event?.id && openPlaceDetails(places.find(p => p.id === card.event.id) || card.event)"
            >
              <div class="rec-card-top">
                <span class="rec-role-badge">{{ cleanUiLabel(card.card_role_label, '推薦選擇') }}</span>
                <div class="rec-score-pill">
                  <span>綜合得分</span>
                  <strong>{{ Math.round(card.total_score || 90) }}</strong>
                </div>
              </div>

              <h3 class="rec-card-title">{{ card.event?.title }}</h3>
              <div v-if="formatAgentEventDate(card.event)" class="rec-card-date">{{ formatAgentEventDate(card.event) }}</div>
              <p class="rec-card-reason">{{ card.recommendation_reason }}</p>

              <!-- Dispersal Badges -->
              <div v-if="card.badges?.length" class="rec-badges-row">
                <span v-for="badge in card.badges" :key="badge.label" class="rec-badge" :class="`badge-${badge.color}`">
                  {{ badge.label }}
                </span>
              </div>

              <!-- PRD Multi-dimension Score Breakdown -->
              <div class="rec-metrics-grid">
                <div class="rec-metric-item">
                  <small>人流舒適度</small>
                  <strong :class="crowdClass(card.crowd_score)">{{ crowdLabel(card.crowd_score) }} ({{ card.crowd_score }})</strong>
                </div>
                <div class="rec-metric-item">
                  <small>捷運與遮蔭</small>
                  <strong>{{ Math.round(card.accessibility_score || 85) }}%</strong>
                </div>
                <div class="rec-metric-item">
                  <small>微氣候適應</small>
                  <strong>{{ Math.round(card.weather_comfort_score || 88) }}分</strong>
                </div>
              </div>

              <div class="rec-card-footer">
                <span class="rec-transit-guide">⌁ {{ card.transit_summary || '捷運直達' }}</span>
                <div class="rec-feedback-actions" @click.stop>
                  <button
                    type="button"
                    class="feedback-btn"
                    :class="{ active: feedbackMap.get(card.event?.id)?.isHelpful === true }"
                    aria-label="這個推薦有幫助"
                    title="這個推薦有幫助"
                    @click="handleFeedback(card.event?.id, true, 'accurate')"
                  >✓</button>
                  <button
                    type="button"
                    class="feedback-btn"
                    :class="{ active: feedbackMap.get(card.event?.id)?.isHelpful === false }"
                    aria-label="這個推薦不適合"
                    title="人潮偏多或距離較遠"
                    @click="handleFeedback(card.event?.id, false, 'too_crowded')"
                  >×</button>
                </div>
              </div>
            </article>
          </div>

          <div v-if="aiDispersalSummary" class="dispersal-insight-pill">
            <span class="insight-icon">↝</span>
            <div>
              <strong>人流建議</strong>
              <p>{{ aiDispersalSummary }}</p>
            </div>
          </div>
        </section>

        <!-- Activities Catalog Header -->
        <div class="recommendation-header">
          <div>
            <div class="section-kicker">
               {{ selectedTab === 'saved' ? '已收藏' : `活動清單 · ${places.length} 項` }}
              <span class="pulse-dot"></span>
            </div>
             <h2>{{ selectedTab === 'saved' ? '已收藏的活動' : '探索活動' }}</h2>
          </div>
          <button
            v-if="selectedTab !== 'saved'"
            class="view-all"
            type="button"
             @click="activeFilter = '推薦'"
          >
             清除篩選
          </button>
        </div>

        <!-- Filter Chips Row -->
        <div v-if="selectedTab !== 'saved'" class="filter-row" role="tablist" aria-label="推薦篩選">
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

        <!-- Empty state for Bookmarks -->
        <div v-if="selectedTab === 'saved' && bookmarkedPlaces.length === 0" class="events-state">
           還沒有收藏活動。點擊卡片右上角的收藏即可加入。
        </div>

        <!-- Events List -->
        <div v-else-if="eventsLoading" class="events-state">正在載入活動…</div>
        <div v-else-if="eventsError" class="events-state events-state-error">{{ eventsError }}</div>
        <div v-else class="place-list">
          <article
            v-for="(place, index) in visiblePlaces"
            :key="place.id"
            class="place-card"
            :class="{ selected: activePlaceId === place.id }"
            role="button"
            tabindex="0"
            @click="openPlaceDetails(place)"
            @keydown.enter="openPlaceDetails(place)"
          >
             <div class="place-number">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="place-main">
              <div class="place-topline">
                <span class="place-category">{{ place.category }}</span>
                 <span class="place-distance">{{ place.distanceShort }}</span>
              </div>
              <h3>{{ place.name }}</h3>
              <div class="place-meta">{{ place.dateRange || '當期活動' }} <span>·</span> {{ place.fee }}</div>
              <p>{{ place.description }}</p>
              <div class="metric-row">
                <span class="metric crowd-metric" :class="crowdClass(place.crowd)">
                  <i class="metric-icon crowd-icon">♧</i> 人流 {{ crowdLabel(place.crowd) }}
                  <strong v-if="Number.isFinite(place.crowd)">{{ place.crowd }}{{ place.crowdIsMock ? '*' : '' }}</strong>
                </span>
                <span class="metric" :title="place.sunLabel || ''">
                  <i class="metric-icon sun-icon">◒</i> {{ place.isIndoor ? '室內 0% 曝曬' : `曝曬 ${place.sun}% (遮蔭 ${place.shade || (100 - place.sun)}%)` }}
                </span>
                <span class="metric"><i class="metric-icon time-icon">◷</i> {{ place.time }}</span>
              </div>
              <div v-if="Number.isFinite(place.crowd)" class="crowd-progress" :title="place.crowdIsMock ? 'MVP 模擬人流資料' : '人流資料'">
                <Progress :value="place.crowd" :color="place.color" track-color="#edece7" :height="4" />
              </div>
            </div>
            <button
              type="button"
              class="bookmark-card-btn"
              :class="{ active: favoritePlaceIds.has(place.id) }"
               :aria-label="favoritePlaceIds.has(place.id) ? '取消收藏' : '收藏活動'"
              @click.stop="toggleBookmark(place)"
            >
              {{ favoritePlaceIds.has(place.id) ? '♥' : '♡' }}
            </button>
          </article>
        </div>
      </div>

      <section v-if="!sheetMinimized" class="shade-scenario-panel" aria-labelledby="shade-scenario-title">
        <div class="shade-scenario-copy">
          <span class="shade-scenario-icon" aria-hidden="true">◒</span>
          <div>
             <strong id="shade-scenario-title">日照情境</strong>
             <small>以 {{ activeShadeScenario.time }} 計算</small>
          </div>
        </div>
        <div class="shade-scenario-switch" role="group" aria-label="選擇遮蔭估算時段">
          <button
            v-for="scenario in SHADE_TIME_SCENARIOS"
            :key="scenario.id"
            type="button"
            :class="{ active: shadeTimePeriod === scenario.id }"
            :aria-pressed="shadeTimePeriod === scenario.id"
            @click="selectShadeTimePeriod(scenario.id)"
          >
            <strong>{{ scenario.label }}</strong>
            <small>{{ scenario.time }}</small>
          </button>
        </div>
      </section>
    </section>

    <!-- Persona Switcher Modal (PRD 7.1) -->
    <div v-if="showPersonaModal" class="persona-modal-overlay" @click.self="showPersonaModal = false">
      <div class="persona-modal">
        <header class="persona-modal-header">
          <div>
             <span>示範帳號</span>
             <h2>切換使用者</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showPersonaModal = false">×</button>
        </header>
         <p class="persona-intro">選擇一個示範帳號，套用它的偏好與收藏清單。</p>
        <div class="personas-grid">
          <div
            v-for="p in personas"
            :key="p.id"
            class="persona-card"
            :class="{ active: activePersona.id === p.id }"
            role="button"
            tabindex="0"
            @click="switchPersona(p)"
            @keydown.enter="switchPersona(p)"
          >
            <div class="persona-avatar">{{ p.name.slice(0, 2) }}</div>
            <div class="persona-details">
              <strong>{{ p.name }}</strong>
              <div class="persona-tags">
                <span v-for="t in p.interest_tags" :key="t">{{ t }}</span>
              </div>
              <small>{{ p.prefer_indoor ? '偏好室內' : '可接受戶外' }} · {{ p.avoid_crowd ? '避開人潮' : '喜愛熱鬧' }} · 預算上限 NT${{ p.budget_twd_cap }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Navigation Bar -->
    <nav class="mobile-nav" aria-label="主要導覽">
      <button :class="{ active: selectedTab === 'discover' }" @click="selectedTab = 'discover'">
        <span>⌂</span>探索
      </button>
      <button :class="{ active: selectedTab === 'saved' }" @click="selectedTab = 'saved'">
        <span>♥</span>收藏 ({{ favoritePlaceIds.size }})
      </button>
      <button :class="{ active: selectedTab === 'profile' }" @click="showPersonaModal = true">
        <span>◎</span>{{ activePersona.name.slice(0, 3) }}
      </button>
    </nav>
  </main>
</template>
