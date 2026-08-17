<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Loader } from '@googlemaps/js-api-loader'
import { Badge, Button, Chip, Input, Progress, Snackbar } from '@varlet/ui'
import { createEventDataSource } from './data/eventDataSource'
import { toEventPlace } from './data/eventPresentation'
import { createAgentService } from './services/agentService'
import { weatherService } from './services/weatherService'
import { crowdService } from './services/crowdService'
import { routesService } from './services/routesService'
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
const activeFilter = ref('為你推薦')
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

// Routes & Thermal Comfort State (PRD 10)
const activeRoute = ref(null)
const routeLoading = ref(false)
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
const eventDataSource = createEventDataSource()
const eventSourceLabel = eventDataSource.label
const agentService = createAgentService()
const markers = new Map()
let sheetDragStartY = 0
let sheetDragStartHeight = 0
let mapFocusTimer = null

const filters = computed(() => {
  const base = ['為你推薦', '室內避暑', '低人流', '免費入場']
  if (quickTags.value.length > 0) {
    quickTags.value.forEach((tag) => {
      if (!base.includes(tag.label)) base.push(tag.label)
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
  if (activeFilter.value === '室內避暑') {
    return places.value.filter((place) => place.isIndoor)
  }
  if (activeFilter.value === '免費入場') {
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

async function loadEvents() {
  eventsLoading.value = true
  eventsError.value = ''
  try {
    const [records, venueStatuses] = await Promise.all([
      eventDataSource.list(),
      crowdService.getVenuesStatus(),
    ])
    const crowdByVenue = new Map(venueStatuses.map((venue) => [venue.venue_id, venue]))
    places.value = records.map((record, index) => {
      const venueStatus = crowdByVenue.get(record.venueId)
      return toEventPlace({
        ...record,
        crowdScore: venueStatus?.crowd_score,
        // The current backend venue feed comes from MockDataSeeder.
        crowdIsMock: Boolean(venueStatus),
      }, index)
    })
    activePlaceId.value = places.value[0]?.id ?? ''
    if (map.value) {
      markers.forEach((m) => m.overlay?.setMap(null))
      markers.clear()
      places.value.filter((place) => place.position).forEach(addMarker)
      syncMarkerSelection()
    }
  } catch (error) {
    eventsError.value = '活動目錄暫時無法載入，請確認後端服務或網路連線。'
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
  sheetExpanded.value = false
  sheetMinimized.value = false
  selectPlace(place)
  await nextTick()
  sheetElement.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

async function closePlaceDetails() {
  resetRouteState()
  detailPlaceId.value = ''
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

function routeStepInstruction(step) {
  if (step.instructions?.trim()) return step.instructions

  const transit = step.transitDetails
  if (transit) {
    const line = transit.transitLine?.shortName
      || transit.transitLine?.name
      || transit.transitLine?.vehicle?.name
      || '大眾運輸'
    const departure = transit.departureStop?.name
    const arrival = transit.arrivalStop?.name
    const direction = transit.headsign ? `（往 ${transit.headsign}）` : ''
    const stops = transit.stopCount ? `，共 ${transit.stopCount} 站` : ''
    if (departure && arrival) return `從 ${departure} 搭乘 ${line}${direction} 至 ${arrival}${stops}`
    return `搭乘 ${line}${direction}${stops}`
  }

  return String(step.travelMode).includes('WALK')
    ? '依 Google Maps 步行路徑前進'
    : '依 Google Maps 路線前進'
}

async function renderGoogleDirections(origin, destination, isCurrentRequest = () => true) {
  const { Route } = await window.google.maps.importLibrary('routes')
  const { LatLngBounds } = await window.google.maps.importLibrary('core')
  if (!isCurrentRequest()) return null
  const { routes } = await Route.computeRoutes({
    origin,
    destination,
    travelMode: 'TRANSIT',
    departureTime: new Date(),
    computeAlternativeRoutes: false,
    language: 'zh-TW',
    region: 'TW',
    fields: ['path', 'legs', 'localizedValues'],
  })
  if (!isCurrentRequest()) return null

  const route = routes?.[0]
  const leg = route?.legs?.[0]
  if (!route || !leg) throw new Error('Google Routes did not return a route leg')

  clearMapRouteLayers()
  route.createPolylines().forEach((polyline) => {
    polyline.setOptions?.({
      strokeColor: '#3c6254',
      strokeOpacity: 0.92,
      strokeWeight: 6,
    })
    polyline.setMap(map.value)
    currentRoutePolylines.push(polyline)
  })

  const bounds = new LatLngBounds()
  route.path.forEach((point) => bounds.extend(point))
  fitRouteInVisibleMap(bounds)

  return {
    isGoogleRoute: true,
    totalDurationMinutes: Math.max(1, Math.round((leg.durationMillis || 0) / 60000)),
    totalDistanceMeters: leg.distanceMeters || 0,
    transitSummary: `Google Maps 大眾運輸約 ${leg.localizedValues?.duration || '時間待確認'}`,
    segments: (leg.steps || []).map((step) => ({
      mode: step.travelMode || 'TRANSIT',
      instruction: routeStepInstruction(step),
      duration_minutes: Math.max(1, Math.round((step.staticDurationMillis || 0) / 60000)),
      distance_meters: step.distanceMeters || 0,
      is_shaded_or_underground: false,
    })),
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

    const route = await routesService.computeRoute({
      originLat: userLocation.value.lat,
      originLng: userLocation.value.lng,
      destLat: place.position.lat,
      destLng: place.position.lng,
      destName: place.name,
      prioritizeShade: true,
    })
    if (!isCurrentRouteRequest()) return

    let googleRoute = null
    if (map.value && window.google?.maps?.importLibrary) {
      try {
        googleRoute = await renderGoogleDirections(userLocation.value, place.position, isCurrentRouteRequest)
      } catch (directionsError) {
        console.warn('Google Directions route failed:', directionsError)
      }
    }
    if (!isCurrentRouteRequest()) return

    if (!googleRoute && route.hasRealPath && map.value && window.google?.maps) {
      clearMapRouteLayers()
      currentPolyline = new window.google.maps.Polyline({
        path: route.path,
        geodesic: true,
        strokeColor: '#3c6254',
        strokeOpacity: 0.9,
        strokeWeight: 6,
        map: map.value,
      })

      const bounds = new window.google.maps.LatLngBounds()
      route.path.forEach((pt) => bounds.extend(pt))
      fitRouteInVisibleMap(bounds)
    }

    if (!googleRoute && !route.hasRealPath) {
      activeRoute.value = null
      clearMapRouteLayers()
      Snackbar.warning('目前無法取得 Google Maps 實際路線，未顯示模擬路徑或固定步驟')
      return
    }

    activeRoute.value = googleRoute
      ? {
          ...route,
          ...googleRoute,
          routeAdvice: `${googleRoute.transitSummary}。遮蔭與地下街比例為 SideQuest 估算值，實際行走請以 Google Maps 導航為準。`,
        }
      : route

    Snackbar.success(`已取得實際路線：${activeRoute.value.transitSummary}`)
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
      Snackbar.success(heatmapIsMock.value ? '已開啟 MVP 模擬人潮圖層' : '已開啟人潮圖層')
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
    Snackbar.warning('先告訴我你現在想怎麼感受台北')
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

    Snackbar.success(`Agent 已完成分析與多準則推薦`)
  } catch (error) {
    aiError.value = 'Agent 暫時沒有回應，推薦卡仍可直接瀏覽。'
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

async function fetchMapsApiKey() {
  if (rawEnvMapsKey) return rawEnvMapsKey
  try {
    const res = await fetch('/api/v1/config/maps-key')
    if (res.ok) {
      const data = await res.json()
      if (data.maps_api_key) return data.maps_api_key
    }
  } catch (err) {
    console.warn('Could not fetch dynamic maps key from backend config:', err)
  }
  return ''
}

async function initMap() {
  mapState.value = 'loading'
  window.gm_authFailure = () => {
    mapState.value = 'error'
    mapError.value = 'Google Maps 認證授權中，正在套用專案網域白名單…'
  }

  const mapsApiKey = await fetchMapsApiKey()
  if (!mapsApiKey) {
    mapState.value = 'error'
    mapError.value = '尚未設定 Google Maps API key (請設定 GCP 專案環境變數)'
    return
  }

  try {
    const loader = new Loader({
      apiKey: mapsApiKey,
      version: 'weekly',
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
    mapError.value = error?.message?.includes('RefererNotAllowedMapError')
      ? '此網址尚未加入 API key 的允許來源'
      : 'Google Maps 載入失敗，請檢查 API key 與 Maps JavaScript API 是否啟用'
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
        <span>正在連線 Google Maps 與台北微氣候…</span>
      </div>
      <div v-if="mapState === 'error'" class="map-state map-error">
        <span class="error-mark">!</span>
        <strong>Google Maps 暫時無法載入</strong>
        <small>{{ mapError }}</small>
      </div>

      <!-- Topbar Header -->
      <header class="topbar">
        <div class="brand-lockup">
          <div class="brand-mark">SQ</div>
          <div>
            <div class="brand-name">sidequest<span>.</span></div>
            <div class="brand-caption">城市裡的下一站 · AI Agent</div>
          </div>
        </div>
        <div class="topbar-actions">
          <button class="city-pill" @click="centerMap" aria-label="切換城市或置中">
            <span class="status-dot"></span> Taipei City <span class="caret">⌄</span>
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
      <div class="map-context-pill" @click="loadWeather" title="點擊重新取得微氣候資料">
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
          {{ weather.isMock ? '模擬環境' : '即時更新' }}
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
        🔥
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
          <span>{{ activeRoute.transitSummary }} · SideQuest 遮蔭估算 {{ activeRoute.shadePercentage }}%</span>
        </div>
        <button type="button" class="route-banner-close" aria-label="清除路線" @click="clearRoute">×</button>
      </div>

      <div class="map-legend">
        <span><b class="legend-dot legend-cool"></b>人流舒適 (&lt;35)</span>
        <span><b class="legend-dot legend-warm"></b>人潮熱門 (&gt;65)</span>
        <span v-if="heatmapVisible && heatmapIsMock">MVP 模擬人流</span>
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
          <small>{{ sheetHandleLabel }}</small>
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
          <span>ACTIVITY DETAIL · {{ detailPlace.label }}</span>
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
        <div v-if="activeRoute" class="route-guidance-card">
          <div class="route-card-header">
            <div>
              <span class="route-tag">{{ activeRoute.isGoogleRoute ? 'GOOGLE MAPS 智慧遮蔭' : '🛡️ 智慧抗熱遮蔭路徑' }}</span>
              <h3>{{ activeRoute.transitSummary }}</h3>
            </div>
            <div class="route-shade-badge">
              <strong>{{ activeRoute.shadePercentage }}%</strong>
              <small>遮蔭/地下率</small>
            </div>
          </div>
          <div v-if="activeRoute.sunExposureMinutes !== undefined" class="route-sun-metric-bar" style="font-size: 0.78rem; color: #436456; background: #eef5f1; border-radius: 8px; padding: 6px 10px; margin: 8px 0 12px; display: flex; align-items: center; justify-content: space-between;">
            <span>☀️ 直曬僅 <strong>{{ activeRoute.sunExposureMinutes }}</strong> 分鐘</span>
            <span>🌲 總遮蔭步道 <strong>{{ activeRoute.shadedDistanceMeters || 0 }}m</strong></span>
          </div>
          <p class="route-advice-copy">{{ activeRoute.routeAdvice }}</p>
          <div v-if="activeRoute.segments?.length" class="route-steps">
            <div v-for="(step, idx) in activeRoute.segments" :key="idx" class="route-step">
              <span class="step-num">{{ idx + 1 }}</span>
              <div class="step-info">
                <strong>{{ step.instruction }}</strong>
                <small>{{ step.duration_minutes }} 分鐘 · {{ step.distance_meters }}m {{ step.is_shaded_or_underground ? '🛡️ 遮蔭/地下通道' : '☀️ 戶外路段' }}</small>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-status-grid">
          <div>
            <span>♧</span>
            <small>目前人流</small>
            <strong :class="crowdClass(detailPlace.crowd)">
              {{ crowdLabel(detailPlace.crowd) }}<template v-if="Number.isFinite(detailPlace.crowd)"> ({{ detailPlace.crowd }}){{ detailPlace.crowdIsMock ? ' · 模擬' : '' }}</template>
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
          <div class="detail-section-heading"><span>02</span><h2>亮點與為什麼值得去</h2></div>
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
            <p class="eyebrow"><span class="eyebrow-dot"></span> 你的城市 Agent · {{ activePersona.name }}</p>
            <h1>今天，想怎麼感受台北？</h1>
          </div>
          <div class="header-badges">
            <Badge :value="eventSourceLabel" type="success" class="data-badge" />
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
            placeholder="告訴我你現在的感受，例如：想找室內展覽，不要太熱、人不要太多…"
            @keydown.enter.exact.prevent="explore"
          />
          <Button class="explore-button" type="primary" round :loading="isExploring" @click="explore">
            <span v-if="!isExploring">探索 <span class="button-arrow">↗</span></span>
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
            {{ item }} <span>↗</span>
          </button>
        </div>

        <!-- Live Agent Streaming Reasoning & Thoughts -->
        <div v-if="isExploring || aiReply || aiError || aiThoughtSteps.length" class="agent-response" :class="{ failed: aiError }">
          <div class="agent-response-heading">
            <span>✦</span> 推薦分析
            <em v-if="isExploring">正在即時推理台北活動、微氣候與捷運連通…</em>
          </div>

          <!-- Structured Understanding Criteria (PRD 7.3) -->
          <div v-if="aiParsedCriteria" class="parsed-criteria-row">
            <span class="criteria-badge">時段：{{ aiParsedCriteria.date_time_range || '今日' }}</span>
            <span v-if="aiParsedCriteria.requested_date" class="criteria-badge criteria-date-badge">📅 已鎖定 {{ aiParsedCriteria.requested_date }}</span>
            <span v-if="aiParsedCriteria.occasion" class="criteria-badge">💛 {{ aiParsedCriteria.occasion }}</span>
            <span v-if="aiParsedCriteria.target_district" class="criteria-badge">區域：{{ aiParsedCriteria.target_district }}</span>
            <span v-if="aiParsedCriteria.avoid_crowd" class="criteria-badge">🍃 避開人潮優先</span>
            <span v-if="aiParsedCriteria.prefer_indoor" class="criteria-badge">❄ 室內避暑</span>
            <span v-if="aiParsedCriteria.is_free_only" class="criteria-badge">🎟 免費入場</span>
          </div>

          <!-- Collapsible Agent Thought Trace -->
          <div v-if="aiThoughtSteps.length" class="agent-thought-container">
            <button
              type="button"
              class="thought-toggle-btn"
              @click="showThoughtTrace = !showThoughtTrace"
            >
              <span>🧠 Agent 決策推論軌跡 ({{ aiThoughtSteps.length }} 步)</span>
              <small>{{ showThoughtTrace ? '收合 ▲' : '展開 ▼' }}</small>
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
          <p v-if="isExploring && !aiReply" class="agent-loading-copy">正在透過 SideQuest 多準則引擎評估活動與交通條件…</p>
          <p v-else-if="aiError" class="agent-error-copy">{{ aiError }}</p>
          <p v-else class="agent-markdown-text">{{ aiReply }}</p>
        </div>

        <!-- 3 PRD Recommendation Cards (PRD 7.4 & 8.3) -->
        <section v-if="aiRecommendations.length" class="agent-recommendations-section" aria-label="3 大推薦卡片">
          <div class="agent-rec-header">
            <div>
              <span class="rec-kicker">PRD 3-TIER RECOMMENDATIONS</span>
              <h2>城市決策提案</h2>
            </div>
            <strong>共評估 {{ aiEvaluatedCount || places.length }} 個符合日期的活動</strong>
          </div>

          <div class="recommendations-grid">
            <article
              v-for="(card, idx) in aiRecommendations"
              :key="`card-${card.event?.id || idx}`"
              class="rec-card"
              :class="`role-${card.card_role?.toLowerCase()}`"
              @click="card.event?.id && openPlaceDetails(places.find(p => p.id === card.event.id) || card.event)"
            >
              <div class="rec-card-top">
                <span class="rec-role-badge">{{ card.card_role_label || '🎯 推薦選擇' }}</span>
                <div class="rec-score-pill">
                  <span>綜合得分</span>
                  <strong>{{ Math.round(card.total_score || 90) }}</strong>
                </div>
              </div>

              <h3 class="rec-card-title">{{ card.event?.title }}</h3>
              <div v-if="formatAgentEventDate(card.event)" class="rec-card-date">📅 {{ formatAgentEventDate(card.event) }}</div>
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
                    title="推薦精準，很喜歡"
                    @click="handleFeedback(card.event?.id, true, 'accurate')"
                  >👍</button>
                  <button
                    type="button"
                    class="feedback-btn"
                    :class="{ active: feedbackMap.get(card.event?.id)?.isHelpful === false }"
                    title="人潮偏多或距離較遠"
                    @click="handleFeedback(card.event?.id, false, 'too_crowded')"
                  >👎</button>
                </div>
              </div>
            </article>
          </div>

          <div v-if="aiDispersalSummary" class="dispersal-insight-pill">
            <span class="insight-icon">↝</span>
            <div>
              <strong>人流疏導洞察</strong>
              <p>{{ aiDispersalSummary }}</p>
            </div>
          </div>
        </section>

        <!-- Activities Catalog Header -->
        <div class="recommendation-header">
          <div>
            <div class="section-kicker">
              {{ selectedTab === 'saved' ? 'MY BOOKMARKS' : `${eventSourceLabel} · ${places.length} ACTIVITIES` }}
              <span class="pulse-dot"></span>
            </div>
            <h2>{{ selectedTab === 'saved' ? '我的收藏活動' : '全部城市探索清單' }}</h2>
          </div>
          <button
            v-if="selectedTab !== 'saved'"
            class="view-all"
            type="button"
            @click="activeFilter = '為你推薦'"
          >
            重置篩選 <span>↺</span>
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
          你尚未收藏任何活動，點擊活動卡片中的「♡」即可加入個人清單！
        </div>

        <!-- Events List -->
        <div v-else-if="eventsLoading" class="events-state">正在同步台北活動與即時人流…</div>
        <div v-else-if="eventsError" class="events-state events-state-error">{{ eventsError }}</div>
        <div v-else class="place-list">
          <article
            v-for="(place, index) in visiblePlaces"
            :key="place.id"
            class="place-card"
            :class="{ selected: activePlaceId === place.id }"
            @click="openPlaceDetails(place)"
          >
            <div class="place-number">0{{ index + 1 }}</div>
            <div class="place-main">
              <div class="place-topline">
                <span class="place-category">{{ place.category }}</span>
                <span class="place-distance">{{ place.distanceShort }} <span>↗</span></span>
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
              title="收藏活動"
              @click.stop="toggleBookmark(place)"
            >
              {{ favoritePlaceIds.has(place.id) ? '♥' : '♡' }}
            </button>
          </article>
        </div>
      </div>
    </section>

    <!-- Persona Switcher Modal (PRD 7.1) -->
    <div v-if="showPersonaModal" class="persona-modal-overlay" @click.self="showPersonaModal = false">
      <div class="persona-modal">
        <header class="persona-modal-header">
          <div>
            <span>DEMO LOGIN · PRD 7.1</span>
            <h2>選擇測試 Persona 角色</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showPersonaModal = false">×</button>
        </header>
        <p class="persona-intro">免密碼切換預設測試角色，立即體驗個人化推薦、收藏清單與自訂人流偏好：</p>
        <div class="personas-grid">
          <div
            v-for="p in personas"
            :key="p.id"
            class="persona-card"
            :class="{ active: activePersona.id === p.id }"
            @click="switchPersona(p)"
          >
            <div class="persona-avatar">{{ p.name.slice(0, 2) }}</div>
            <div class="persona-details">
              <strong>{{ p.name }}</strong>
              <div class="persona-tags">
                <span v-for="t in p.interest_tags" :key="t">{{ t }}</span>
              </div>
              <small>{{ p.prefer_indoor ? '❄ 偏好室內' : '☀ 接受戶外' }} · {{ p.avoid_crowd ? '🍃 避開人潮' : '👥 喜愛熱鬧' }} · 預算上限 NT${{ p.budget_twd_cap }}</small>
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
        <span>👤</span>{{ activePersona.name.slice(0, 3) }}
      </button>
    </nav>
  </main>
</template>
