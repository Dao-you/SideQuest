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

const rawEnvMapsKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || 'AIzaSyBvHetpB7ilLcNSJXeecfVgaLQ7b3TGobY'
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

// User & Persona State (PRD 7.1 & Google Auth)
const personas = ref([])
const activePersona = ref({
  id: 'demo_weekend_explorer',
  name: '林宥廷 (週末文藝探索者)',
  account_type: 'WEEKEND_EXPLORER',
  interest_tags: ['當代藝術', '獨立手作', '手沖咖啡', '動漫展覽'],
})
const showPersonaModal = ref(false)
const favoritePlaceIds = ref(new Set())

// Google Authentication & Identity Services State
const googleClientId = ref('')
const isGoogleAuthLoading = ref(false)
const googleAuthReady = ref(false)
const googleAuthError = ref('')
const isGoogleLoggedIn = computed(() => {
  return activePersona.value?.auth_provider === 'google'
})

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
const routeDepartureTime = ref('出發時間 現在')
const showDepartureDropdown = ref(false)
const routeOriginSwapped = ref(false)
const selectedModalTab = ref('transit') // 'overview' | 'youbike' | 'transit' | 'taxi'

const routePreferencesList = [
  { id: 'fastest', label: '經典', icon: '🟢', desc: '最快速抵達' },
  { id: 'wheelchair', label: '無障礙', icon: '♿', desc: '電梯/推車/大件行李友善' },
  { id: 'more_bus', label: '公車+', icon: '🚌', desc: '公車直達優先' },
  { id: 'more_subway', label: '捷運+', icon: '🚇', desc: '捷運軌道優先' },
  { id: 'less_walking', label: '少走點', icon: '🚶', desc: '少走路/少換乘' },
  { id: 'more_shading', label: '避曬', icon: '🛡️', desc: '地下街與林蔭遮蔽' },
  { id: 'less_crowded', label: '避人潮', icon: '👥', desc: '舒適離峰車廂' },
  { id: 'mixed', label: '混合', icon: '🚲', desc: 'YouBike+捷運組合' },
]

const departureTimeOptions = [
  '出發時間 現在',
  '出發時間 10 分鐘後',
  '出發時間 30 分鐘後',
  '出發時間 1 小時後',
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

// Date & Time Picker Options (Step 1 & 4)
const quickDateOptions = [
  { label: '📅 今天 (8/18)', value: '今天', promptSuffix: '今天想找適合放鬆的活動，不要太熱、人不要太多' },
  { label: '📅 明天 (8/19)', value: '明天', promptSuffix: '明天下午想找室內展覽與咖啡廳' },
  { label: '📅 本週末 (8/22-8/23)', value: '本週末', promptSuffix: '8月22日下午想和另一半約會，看展再喝咖啡' },
  { label: '📅 8月22日 (週五)', value: '8月22日', promptSuffix: '8月22日週五想去當代藝術或特色展覽' },
  { label: '📅 8月23日 (週六)', value: '8月23日', promptSuffix: '8月23日週六想找人少安靜的地方散步' },
]
const selectedDateTag = ref('本週末')

// Active Planned Itinerary & Google Calendar State (Step 9, 11, 12, 14)
const activePlannedPlace = ref(null)

// Profile & Preferences State (Step 3 & 17)
const userPreferences = ref({
  prefer_indoor: true,
  avoid_crowd: true,
  max_budget: 500,
  route_preference: 'shade_first',
  favorite_tags: ['文創', '市集', '咖啡', '冷氣'],
  google_account_connected: true,
  google_email: 'kevin.sidequest@gmail.com',
})

const availableTags = [
  '文創市集',
  'AI講座',
  '當代藝術',
  '手沖咖啡',
  '親子展覽',
  '動漫展覽',
  '老屋甜點',
  '手作工作坊',
  '夜間散步',
  '地下街直通',
  '黑客松',
  '免排隊',
]

// Google Calendar Conflict Modal State (Step 11 & Schedule Conflict Resolution)
const showCalendarConflictModal = ref(false)
const calendarConflictData = ref(null)
const googleCalendarEvents = ref([])
const autoConflictDetection = ref(true)

// PK & Comparison Matrix State (Step 8)
const pkPlaceIds = ref(new Set())
const showPkModal = ref(false)

// Share Card & Link State (Step 10)
const showShareModal = ref(false)
const shareTargetPlace = ref(null)

// Dynamic Condition Alert & Alternative Plan State (Step 13 & 14)
const showAlternativeModal = ref(false)
const alternativePlanData = ref(null)

// Post-event Feedback Modal State (Step 16)
const showFeedbackModal = ref(false)
const feedbackTargetPlace = ref(null)
const feedbackRating = ref(true)
const selectedFeedbackTags = ref(new Set())
const feedbackTagsList = [
  '避開人潮很準確',
  '地下街遮蔭涼爽',
  '交通指引清楚',
  '展覽內容精彩',
  '人潮比預期多',
  '步行距離偏遠',
]

const places = ref([])
const eventDataSource = createEventDataSource()
const eventSourceLabel = eventDataSource.label
const agentService = createAgentService()
const markers = new Map()
let sheetDragStartY = 0
let sheetDragStartHeight = 0
let mapFocusTimer = null

const pkPlaces = computed(() =>
  places.value.filter((p) => pkPlaceIds.value.has(p.id))
)

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

function syncPreferencesFromPersona(profile) {
  if (!profile) return
  userPreferences.value = {
    prefer_indoor: profile.prefer_indoor ?? true,
    avoid_crowd: profile.avoid_crowd ?? true,
    max_budget: profile.max_budget ?? profile.budget_twd_cap ?? 500,
    route_preference: profile.route_preference ?? 'shade_first',
    favorite_tags: profile.favorite_tags ?? profile.interest_tags ?? ['文創', '市集', '咖啡', '冷氣'],
    google_account_connected: profile.google_account_connected ?? true,
    google_email: profile.google_email ?? `${profile.id}@gmail.com`,
  }
}

function togglePreferenceTag(tag) {
  const tags = [...userPreferences.value.favorite_tags]
  const idx = tags.indexOf(tag)
  if (idx >= 0) {
    tags.splice(idx, 1)
  } else {
    tags.push(tag)
  }
  userPreferences.value.favorite_tags = tags
}

async function refreshGoogleCalendarEvents() {
  try {
    const events = await userService.getCalendarEvents(activePersona.value.id)
    if (events && Array.isArray(events)) {
      googleCalendarEvents.value = events
    }
  } catch (err) {
    console.warn('Refresh calendar events error:', err)
  }
}

async function saveUserPreferences() {
  try {
    const updated = await userService.updatePreferences(activePersona.value.id, {
      prefer_indoor: userPreferences.value.prefer_indoor,
      avoid_crowd: userPreferences.value.avoid_crowd,
      max_budget: userPreferences.value.max_budget,
      route_preference: userPreferences.value.route_preference,
      favorite_tags: userPreferences.value.favorite_tags,
      google_account_connected: userPreferences.value.google_account_connected,
      google_email: userPreferences.value.google_email,
    })
    if (updated) {
      activePersona.value = updated
      syncPreferencesFromPersona(updated)
    }
    Snackbar.success('✨ 個人偏好設定已儲存！Agent 探索已套用新條件。')
  } catch (err) {
    console.error('Save preferences error:', err)
    Snackbar.info('個人偏好已更新')
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
      favoritePlaceIds.value = new Set(profile.favorited_event_ids || profile.favorite_event_ids || [])
      syncPreferencesFromPersona(profile)
      if (profile.calendar_events?.length) {
        googleCalendarEvents.value = profile.calendar_events
      } else {
        await refreshGoogleCalendarEvents()
      }
    }
  } catch (err) {
    console.error('User persona load error:', err)
  }
}

async function switchPersona(persona) {
  try {
    const profile = await userService.mockLogin(persona.id)
    activePersona.value = profile
    favoritePlaceIds.value = new Set(profile.favorited_event_ids || profile.favorite_event_ids || [])
    syncPreferencesFromPersona(profile)
    if (profile.calendar_events?.length) {
      googleCalendarEvents.value = profile.calendar_events
    } else {
      await refreshGoogleCalendarEvents()
    }
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

function waitForGoogleIdentityServices(timeoutMs = 10000) {
  if (window.google?.accounts?.id) return Promise.resolve()

  return new Promise((resolve, reject) => {
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      if (window.google?.accounts?.id) {
        window.clearInterval(timer)
        resolve()
      } else if (Date.now() - startedAt >= timeoutMs) {
        window.clearInterval(timer)
        reject(new Error('Google Identity Services SDK 載入逾時'))
      }
    }, 100)
  })
}

function renderGoogleSignInButtons() {
  if (!googleAuthReady.value || !window.google?.accounts?.id) return

  const buttonConfigs = [
    ['google_signin_topbar', { size: 'medium', text: 'signin', width: 150 }],
    ['google_signin_profile', { size: 'large', text: 'signin_with', width: 240 }],
    ['google_signin_modal', { size: 'large', text: 'signin_with', width: 260 }],
  ]
  buttonConfigs.forEach(([id, config]) => {
    const container = document.getElementById(id)
    if (!container || container.childElementCount > 0) return
    window.google.accounts.id.renderButton(container, {
      theme: 'outline',
      type: 'standard',
      shape: 'pill',
      logo_alignment: 'left',
      locale: 'zh_TW',
      ...config,
    })
  })
}

async function initGoogleIdentityServices() {
  try {
    const config = await userService.getGoogleAuthConfig()
    if (!config?.enabled || !config?.client_id) {
      throw new Error('後端尚未設定 Google OAuth Web Client ID')
    }
    googleClientId.value = config.client_id
    await waitForGoogleIdentityServices()
    window.google.accounts.id.initialize({
      client_id: googleClientId.value,
      callback: handleGoogleIdTokenResponse,
      auto_select: false,
      cancel_on_tap_outside: true,
    })
    googleAuthReady.value = true
    await nextTick()
    renderGoogleSignInButtons()
  } catch (err) {
    googleAuthError.value = err?.message || 'Google 登入目前無法使用'
    console.error('Google Identity Services initialization failed:', err)
  }
}

async function handleGoogleIdTokenResponse(response) {
  if (isGoogleAuthLoading.value) return
  if (!response?.credential) {
    googleAuthError.value = 'Google 未回傳登入憑證，請再試一次'
    return
  }

  isGoogleAuthLoading.value = true
  googleAuthError.value = ''
  try {
    const res = await userService.loginWithGoogle(response.credential)
    if (res?.user) {
      const googleProfile = { ...res.user, id: res.user.user_id }
      activePersona.value = googleProfile
      syncPreferencesFromPersona(googleProfile)
      googleCalendarEvents.value = res.user.calendar_events || []
      showPersonaModal.value = false
      Snackbar.success(res.message || `已成功以 Google 帳號 (${res.user.email}) 登入！`)
    }
  } catch (err) {
    console.error('Execute Google login error:', err)
    googleAuthError.value = 'Google 登入驗證失敗，請重新選擇帳號'
    Snackbar.error(googleAuthError.value)
  } finally {
    isGoogleAuthLoading.value = false
  }
}

function logoutGoogleAccount() {
  window.google?.accounts?.id?.disableAutoSelect()
  const defaultPersona = personas.value[0] || {
    id: 'demo_weekend_explorer',
    name: '林宥廷 (週末文藝探索者)',
  }
  switchPersona(defaultPersona)
  Snackbar.info('已登出 Google 帳號，回到 Demo 探索角色')
}

watch([showPersonaModal, selectedTab, googleAuthReady], async () => {
  await nextTick()
  renderGoogleSignInButtons()
})

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
    return '依 Google Maps 路線前進'
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
      prioritizeShade: routePreference.value === 'more_shading' || true,
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

    activeRoute.value = googleRoute
      ? {
          ...route,
          ...googleRoute,
          preference: routePreference.value,
          multimodal: route.multimodal,
          accessibilityNote: route.accessibilityNote,
          crowdNote: route.crowdNote,
          routeAdvice: `${googleRoute.transitSummary}。遮蔭與地下街比例為 SideQuest 估算值，實際行走請以 Google Maps 導航為準。`,
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

// Google Calendar Integration (Step 11 & 14)
function generateGoogleCalendarUrl(place) {
  if (!place) return '#'
  const title = `[SideQuest] ${place.name}`
  const now = new Date()
  const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 14, 0, 0)
  const endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 17, 0, 0)
  const formatGCalDate = (d) => d.toISOString().replace(/-|:|\.\d+/g, '')
  const dates = `${formatGCalDate(startDate)}/${formatGCalDate(endDate)}`
  const details = [
    `🎪 活動名稱：${place.name}`,
    `📍 活動地址：${place.address || '台北市'}`,
    `🕒 時間時段：${place.dateRange || '當期活動'} (${place.time || '14:00 - 17:00'})`,
    `🚇 交通建議：${place.transit_summary || '捷運直達 / 大眾運輸'}`,
    `👥 人流狀況：${crowdLabel(place.crowd)} (${place.crowd || 30})`,
    `☀️ 曝曬指數：${place.isIndoor ? '室內空調 (0% 曝曬)' : `戶外曝曬 ${place.sun || 30}%`}`,
    `🎫 門票標準：${place.fee || '免費入場 / 依現場公告'}`,
    `🔗 官方連結：${place.sourceUrl || window.location.href}`,
    '',
    '✨ 由 SideQuest 智慧城市 Agent 自動規劃生成',
  ].join('\n')
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title,
    dates: dates,
    details: details,
    location: place.address || place.name || '台北市',
  })
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

async function addToGoogleCalendar(place) {
  if (!place) return

  // Check if conflict detection is enabled and Google account is connected
  if (autoConflictDetection.value && userPreferences.value.google_account_connected) {
    try {
      const startTime = '2026-08-22T14:30:00+08:00'
      const endTime = '2026-08-22T17:00:00+08:00'
      const checkRes = await userService.checkCalendarConflict(activePersona.value.id, {
        event_id: place.id,
        event_title: place.name,
        start_time: startTime,
        end_time: endTime,
        location: place.address || place.name || '台北市',
      })

      if (checkRes?.has_conflict && checkRes.conflicting_events?.length) {
        calendarConflictData.value = {
          targetPlace: place,
          conflictingEvents: checkRes.conflicting_events,
          startTime,
          endTime,
        }
        showCalendarConflictModal.value = true
        return
      }
    } catch (err) {
      console.warn('Calendar conflict check failed, fallback to direct add:', err)
    }
  }

  // Direct sync if no conflict
  await executeCalendarSync(place, 'overwrite')
}

async function resolveCalendarConflict(choice) {
  if (!calendarConflictData.value) return
  const place = calendarConflictData.value.targetPlace
  const confEvent = calendarConflictData.value.conflictingEvents?.[0]

  showCalendarConflictModal.value = false

  if (choice === 'cancel') {
    Snackbar.info('已保留原 Google 日曆行程，未加入新活動')
    return
  }

  await executeCalendarSync(place, choice, confEvent)
}

async function executeCalendarSync(place, choice = 'overwrite', confEvent = null) {
  activePlannedPlace.value = place
  const url = generateGoogleCalendarUrl(place)

  try {
    const res = await userService.syncCalendarEvent(activePersona.value.id, {
      event_id: place.id,
      event_title: place.name,
      start_time: '2026-08-22T14:30:00+08:00',
      end_time: '2026-08-22T17:00:00+08:00',
      location: place.address || place.name,
      description: `[SideQuest 智慧城市探險]\n人流狀況：${crowdLabel(place.crowd)}\n遮蔭狀況：${place.isIndoor ? '室內冷氣' : '戶外遮蔭'}\n票價：${place.fee || '免費'}`,
      resolution_choice: choice,
    })
    if (res?.all_calendar_events?.length) {
      googleCalendarEvents.value = res.all_calendar_events
    }
  } catch (err) {
    console.warn('Calendar sync error:', err)
  }

  window.open(url, '_blank', 'noopener,noreferrer')
  if (choice === 'overwrite' && confEvent) {
    Snackbar.success(`✅ 已更新 Google 日曆！原【${confEvent.title}】已由【${place.name}】取代！`)
  } else if (choice === 'both') {
    Snackbar.success(`✅ 已將【${place.name}】與原行程同時保留於 Google 日曆中！`)
  } else {
    Snackbar.success(`🎉 已將「${place.name}」排入 Google 日曆，並鎖定為進行中行程！`)
  }
}

function cancelActivePlan() {
  activePlannedPlace.value = null
  Snackbar.info('已清除進行中行程鎖定')
}

// Smart Departure & Arrival Advice (Step 6 & 12)
function getSmartDepartureAdvice(place) {
  if (!place) return { summary: '建議出發時間計算中…', text: '建議現在出發', crowdBuffer: '離峰舒適', depStr: '14:15', arrStr: '14:45' }
  const crowd = Number.isFinite(place.crowd) ? place.crowd : 45
  const durationMin = activeRoute.value?.durationMinutes || 25
  const now = new Date()
  const depTime = new Date(now.getTime() + 10 * 60000)
  const arrTime = new Date(depTime.getTime() + durationMin * 60000)
  const formatTime = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  const depStr = formatTime(depTime)
  const arrStr = formatTime(arrTime)

  let crowdNote = '離峰舒適時段'
  let reason = '避開下一波尖峰人流'
  if (crowd > 65) {
    crowdNote = '人潮較多'
    reason = '建議提早出發以利排隊進場'
  } else if (crowd < 35) {
    crowdNote = '最佳觀展時機'
    reason = '目前場館人流寬鬆，體驗最佳'
  }

  return {
    depStr,
    arrStr,
    crowdNote,
    summary: `建議 ${depStr} 出發 · 預計 ${arrStr} 抵達`,
    text: `建議於 ${depStr} 出發（${reason}），車程約 ${durationMin} 分鐘，預計於 ${arrStr} 順利抵達。`,
    crowdBuffer: crowdNote,
  }
}

// External Google Maps Navigation (Step 15)
function openGoogleMapsNavigation(place) {
  if (!place) return
  const origin = `${userLocation.value.lat},${userLocation.value.lng}`
  const destination = place.position ? `${place.position.lat},${place.position.lng}` : encodeURIComponent(place.address || place.name)
  const url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=transit`
  window.open(url, '_blank', 'noopener,noreferrer')
}

// Quick Date Tag Selection (Step 1 & 4)
function selectDateTag(dateOpt) {
  selectedDateTag.value = dateOpt.label
  prompt.value = dateOpt.promptSuffix
  explore()
}

// PK Comparison Matrix Methods (Step 8)
function togglePkPlace(place) {
  if (!place) return
  if (pkPlaceIds.value.has(place.id)) {
    pkPlaceIds.value.delete(place.id)
    Snackbar.info(`已將「${place.name}」移出 PK 比較`)
  } else {
    if (pkPlaceIds.value.size >= 3) {
      Snackbar.warning('最多同時比較 3 個活動，請先移除其他活動')
      return
    }
    pkPlaceIds.value.add(place.id)
    Snackbar.success(`已加入 PK 比較 (${pkPlaceIds.value.size}/3)`)
  }
}

function clearPk() {
  pkPlaceIds.value.clear()
  Snackbar.info('已清空 PK 比較清單')
}

function selectPkWinner(place) {
  showPkModal.value = false
  openPlaceDetails(place)
  addToGoogleCalendar(place)
}

// Share Modal Methods (Step 10)
function openShareModal(place) {
  shareTargetPlace.value = place || detailPlace.value || activePlannedPlace.value || places.value[0]
  showShareModal.value = true
}

function formatShareText(place) {
  if (!place) return ''
  return [
    `🎪【SideQuest 台北活動推薦】`,
    `✨ ${place.name}`,
    `🗓️ 時間：${place.dateRange || '當期活動'} (${place.time || '14:00 - 17:00'})`,
    `📍 地點：${place.address || '台北市'}`,
    `🚇 交通：${place.transit_summary || '捷運/大眾運輸直達'}`,
    `👥 人流：${crowdLabel(place.crowd)} (${place.crowd || 30})`,
    `☀️ 曝曬：${place.isIndoor ? '室內空調 (0% 曝曬)' : `戶外曝曬 ${place.sun || 30}%`}`,
    `🎫 門票：${place.fee || '免費入場'}`,
    `🔗 活動連結：${place.sourceUrl || window.location.href}`,
    ``,
    `👉 使用 SideQuest 智慧城市 Agent 規劃：${window.location.origin}`,
  ].join('\n')
}

async function copyShareText(place) {
  const text = formatShareText(place)
  try {
    await navigator.clipboard.writeText(text)
    Snackbar.success('已複製活動分享資訊至剪貼簿！')
  } catch (err) {
    Snackbar.success('已準備分享文字！')
  }
}

function shareToLine(place) {
  const text = formatShareText(place)
  const lineUrl = `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(text)}`
  window.open(lineUrl, '_blank', 'noopener,noreferrer')
}

// Dynamic Condition Alert & Alternative Plan Overwrite (Step 13 & 14)
function triggerSimulateConditionChange(originalPlace) {
  const current = originalPlace || detailPlace.value || activePlannedPlace.value || places.value[0]
  if (!current) return
  const indoorCandidates = places.value.filter((p) => p.id !== current.id && p.isIndoor)
  const alt = indoorCandidates.length > 0 ? indoorCandidates[0] : (places.value.find((p) => p.id !== current.id) || current)

  alternativePlanData.value = {
    original: current,
    alternative: alt,
    alertTitle: '⚠️ 行前突發警報：天候驟變與人流暴增',
    alertMessage: `原定活動【${current.name}】目的地目前降雨機率攀升至 85%，且現場人流擁擠度已達 88 (嚴重壅塞)！`,
    agentAdvice: `Agent 依據智慧城市微氣候與即時人流演算法，為您推薦相同性質的室內備案：【${alt.name}】。`,
    benefits: [
      '❄️ 室內空調場館，0% 紫外線曝曬，完全不受雷雨影響',
      `👥 即時人流指數僅 ${alt.crowd || 25} (舒適寬敞，無需排隊)`,
      '🚇 捷運連通地下街，出站步行直達',
    ],
  }
  showAlternativeModal.value = true
}

function applyAlternativePlan() {
  if (!alternativePlanData.value?.alternative) return
  const newPlace = alternativePlanData.value.alternative
  showAlternativeModal.value = false
  activePlannedPlace.value = newPlace
  openPlaceDetails(newPlace)
  planRouteToPlace(newPlace)
  const url = generateGoogleCalendarUrl(newPlace)
  window.open(url, '_blank', 'noopener,noreferrer')
  Snackbar.success(`已成功改用【${newPlace.name}】並更新 Google Calendar 行程！`)
}

function dismissAlternativePlan() {
  showAlternativeModal.value = false
  Snackbar.info('已維持原定計畫。出門請攜帶雨具並留意現場人潮！')
}

// Post-event Feedback Dialog (Step 16)
function openFeedbackModal(place, isHelpful = true) {
  feedbackTargetPlace.value = place || detailPlace.value || places.value[0]
  feedbackRating.value = isHelpful
  selectedFeedbackTags.value.clear()
  showFeedbackModal.value = true
}

function toggleFeedbackTag(tag) {
  if (selectedFeedbackTags.value.has(tag)) {
    selectedFeedbackTags.value.delete(tag)
  } else {
    selectedFeedbackTags.value.add(tag)
  }
}

async function submitDetailedFeedback() {
  const place = feedbackTargetPlace.value
  if (place) {
    feedbackMap.value.set(place.id, {
      isHelpful: feedbackRating.value,
      tags: Array.from(selectedFeedbackTags.value),
    })
    try {
      await agentService.submitFeedback?.({
        event_id: place.id,
        user_id: activePersona.value.id,
        is_helpful: feedbackRating.value,
        feedback_tags: Array.from(selectedFeedbackTags.value),
      })
    } catch (e) {
      console.warn('Feedback submit fallback:', e)
    }
  }
  showFeedbackModal.value = false
  Snackbar.success('感謝您的回饋！Agent 已吸收並更新您的偏好模型。')
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
    mapError.value = 'Google Maps 認證授權中，正在套用專案網域白名單…'
  }

  const mapsApiKey = rawEnvMapsKey
  if (!mapsApiKey) {
    mapState.value = 'error'
    mapError.value = '尚未設定 Google Maps API key (請設定 GCP 專案環境變數)'
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
    initGoogleIdentityServices(),
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
          <div v-if="!isGoogleLoggedIn && googleAuthReady" id="google_signin_topbar" class="google-signin-slot"></div>
          <button
            v-else-if="!isGoogleLoggedIn"
            type="button"
            class="topbar-google-btn"
            disabled
            :title="googleAuthError || 'Google 登入初始化中'"
          >
            Google 登入初始化中
          </button>
          <button
            class="avatar-button"
            :class="{ 'avatar-google-auth': isGoogleLoggedIn }"
            :title="`目前帳號：${activePersona.name} (${isGoogleLoggedIn ? 'Google 認證帳號' : 'Demo 角色'})`"
            aria-label="切換帳號或偏好"
            @click="showPersonaModal = true"
          >
            <img v-if="activePersona.avatar_url && isGoogleLoggedIn" :src="activePersona.avatar_url" class="topbar-avatar-img" alt="Google Avatar" />
            <span v-else>{{ avatarInitials }}</span>
            <span v-if="isGoogleLoggedIn" class="topbar-google-badge">G</span>
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
            <!-- Smart Departure & Arrival Advice (Step 6 & 12) -->
            <div class="smart-timing-strip">
              <span class="timing-badge">🕒 智慧出發建議</span>
              <span>{{ getSmartDepartureAdvice(detailPlace).text }}</span>
            </div>
          </div>
        </div>

        <nav class="detail-quick-actions" aria-label="活動動作">
          <button type="button" class="primary" :disabled="routeLoading || !detailPlace.position" @click="planRouteToPlace(detailPlace)">
            <span aria-hidden="true">⌁</span>
            <strong>{{ routeLoading ? '規劃中…' : '規劃路線' }}</strong>
          </button>
          <button type="button" class="btn-gcal" @click="addToGoogleCalendar(detailPlace)">
            <span aria-hidden="true">📅</span><strong>加行事曆</strong>
          </button>
          <button type="button" :class="{ active: pkPlaceIds.has(detailPlace.id) }" @click="togglePkPlace(detailPlace)">
            <span aria-hidden="true">⚖️</span><strong>{{ pkPlaceIds.has(detailPlace.id) ? '已加PK' : 'PK比較' }}</strong>
          </button>
          <button type="button" @click="openShareModal(detailPlace)">
            <span aria-hidden="true">🔗</span><strong>分享卡片</strong>
          </button>
          <button
            type="button"
            :class="{ favorited: favoritePlaceIds.has(detailPlace.id) }"
            @click="toggleBookmark(detailPlace)"
          >
            <span aria-hidden="true">{{ favoritePlaceIds.has(detailPlace.id) ? '♥' : '♡' }}</span>
            <strong>{{ favoritePlaceIds.has(detailPlace.id) ? '已收藏' : '收藏' }}</strong>
          </button>
          <button type="button" class="btn-sim-alert" @click="triggerSimulateConditionChange(detailPlace)" title="模擬天候驟變與人潮暴增之備案">
            <span aria-hidden="true">🚨</span><strong>模擬備案</strong>
          </button>
          <button type="button" @click="openGoogleMapsNavigation(detailPlace)">
            <span aria-hidden="true">🗺️</span><strong>Google導航</strong>
          </button>
          <a v-if="detailPlace.sourceUrl" :href="detailPlace.sourceUrl" target="_blank" rel="noopener noreferrer">
            <span aria-hidden="true">↗</span><strong>活動官網</strong>
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
                <span>🕒</span>
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
                  <strong>{{ routeOriginSwapped ? detailPlace.name : '當前位置 (台北市區 / 吳興街)' }}</strong>
                </div>
              </div>
              <div class="od-connector"></div>
              <div class="route-od-point">
                <span class="od-dot dest-dot"></span>
                <div class="od-text">
                  <small>目的地</small>
                  <strong>{{ routeOriginSwapped ? '當前位置 (台北市區)' : detailPlace.name }}</strong>
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
                <span class="shade-pill">🛡️ {{ activeRoute.shadePercentage }}% 遮蔭</span>
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
              🌱 沿著林蔭單車專用道前行，預估燃燒 <strong>{{ activeRoute.multimodal?.bike_calories || 128 }}</strong> 大卡，享受微風與低碳生活。
            </p>
          </div>

          <!-- Main Transit Plan Card (Option 2 - Custom to Preference) -->
          <div class="transit-plan-card">
            <div class="route-card-header">
              <div>
                <span class="route-tag">
                  {{ routePreferencesList.find(p => p.id === routePreference)?.icon }}
                  {{ routePreferencesList.find(p => p.id === routePreference)?.label }}推薦
                </span>
                <h3>{{ activeRoute.transitSummary }}</h3>
              </div>
              <div class="route-shade-badge">
                <strong>{{ activeRoute.shadePercentage }}%</strong>
                <small>遮蔭/地下率</small>
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
                ☀️ 戶外直曬僅 {{ activeRoute.sunExposureMinutes }} 分鐘
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
                    <span v-if="step.is_shaded_or_underground" class="step-tag-shade">🛡️ 地下/遮蔭</span>
                    <span v-if="step.is_accessible" class="step-tag-access">♿ 無障礙</span>
                  </div>
                  <small>{{ step.duration_minutes }} 分鐘 · {{ step.distance_meters }}m {{ step.transit_line ? `· ${step.transit_line}` : '' }}</small>
                </div>
              </div>
            </div>
          </div>

          <!-- Taxi / Rideshare Estimate Card (Option 3) -->
          <div class="taxi-option-card">
            <div class="option-card-header">
              <div class="option-title-group">
                <span class="badge-taxi">🚕 計程車 / 專車直達</span>
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
                <span>🗺️</span> 在 Google Maps 開啟即時導航
              </a>
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

      <!-- Dedicated Profile & Google Calendar & Preferences View (Step 3, 11, 17) -->
      <div v-else-if="selectedTab === 'profile'" class="sheet-profile-view">
        <!-- Profile Header Card -->
        <div class="profile-header-card" :class="{ 'google-authenticated-card': isGoogleLoggedIn }">
          <div class="profile-avatar-row">
            <div class="profile-avatar" :class="{ 'google-avatar-glow': isGoogleLoggedIn }">
              <img v-if="activePersona.avatar_url && isGoogleLoggedIn" :src="activePersona.avatar_url" class="profile-avatar-img" alt="Google Avatar" />
              <span v-else class="avatar-letter">{{ activePersona.name ? activePersona.name.charAt(0) : '👤' }}</span>
              <span class="avatar-status-dot" :class="{ 'dot-google': isGoogleLoggedIn }"></span>
            </div>
            <div class="profile-info">
              <div class="profile-name-row">
                <h2>{{ activePersona.name }}</h2>
                <span class="profile-role-badge" :class="{ 'badge-google': isGoogleLoggedIn }">
                  {{ isGoogleLoggedIn ? '🟢 Google 認證帳號' : (activePersona.description || 'Demo 探索者') }}
                </span>
              </div>
              <p class="profile-email">
                <span class="email-icon">✉</span>
                {{ userPreferences.google_email || activePersona.email || `${activePersona.id}@gmail.com` }}
              </p>
            </div>
          </div>

          <!-- Google Sign-In Prompt or Status Banner -->
          <div v-if="!isGoogleLoggedIn" class="profile-google-login-box">
            <div class="google-login-text">
              <strong>連動真實 Google 帳號</strong>
              <span>由 Google 官方登入按鈕選擇帳號，SideQuest 只會接收並驗證基本身分資料。</span>
            </div>
            <div class="google-login-action-group">
              <div v-if="googleAuthReady" id="google_signin_profile" class="google-signin-slot"></div>
              <small v-else class="google-auth-error">{{ googleAuthError || 'Google 登入初始化中…' }}</small>
            </div>
          </div>
          <div v-else class="profile-google-active-box">
            <div class="active-status-left">
              <span class="active-dot">🟢</span>
              <div>
                <strong>Google 身分認證已完成</strong>
                <small>{{ activePersona.email }} · 日曆授權將在加入行程時另行要求</small>
              </div>
            </div>
            <button type="button" class="btn-google-signout" @click="logoutGoogleAccount">
              登出 Google
            </button>
          </div>

          <div class="profile-persona-switch-bar">
            <span class="switch-label">切換 Demo 角色：</span>
            <div class="persona-chips-scroll">
              <button
                v-for="p in personas"
                :key="p.id"
                type="button"
                class="persona-chip-btn"
                :class="{ active: activePersona.id === p.id }"
                @click="switchPersona(p)"
              >
                {{ p.name }}
              </button>
            </div>
          </div>
        </div>

        <!-- Google Calendar Integration Card -->
        <section class="profile-section-card gcal-sync-card">
          <div class="card-section-title">
            <div class="title-left">
              <span class="gcal-icon">📅</span>
              <div>
                <h3>Google 日曆連動與時段衝突調解</h3>
                <small>自動即時比對 Google Calendar 時程，避免重複排程或撞期</small>
              </div>
            </div>
            <span class="gcal-connected-tag">🟢 API 已連線</span>
          </div>

          <div class="gcal-settings-row">
            <label class="gcal-toggle-label">
              <input type="checkbox" v-model="autoConflictDetection" />
              <span>⚡ 啟用智慧衝突偵測 (遇時段重疊時主動提供雙邊比較與覆蓋/並存選項)</span>
            </label>
          </div>

          <div class="gcal-events-preview">
            <div class="preview-header">
              <h4>目前 Google 日曆已排定行程 ({{ googleCalendarEvents.length }})</h4>
              <button type="button" class="btn-refresh-gcal" @click="refreshGoogleCalendarEvents">
                <span>🔄</span> 重新整理
              </button>
            </div>

            <div v-if="googleCalendarEvents.length === 0" class="gcal-empty">
              目前日曆時段充裕，尚未排入任何重疊行程。
            </div>
            <div v-else class="gcal-event-list">
              <div v-for="evt in googleCalendarEvents" :key="evt.event_id" class="gcal-event-item">
                <div class="gcal-event-left">
                  <span class="gcal-time-badge">{{ evt.start_time ? evt.start_time.substring(11, 16) : '14:00' }} - {{ evt.end_time ? evt.end_time.substring(11, 16) : '16:30' }}</span>
                  <strong class="gcal-event-title">{{ evt.title }}</strong>
                  <span class="gcal-event-loc">📍 {{ evt.location || '台北市' }}</span>
                </div>
                <span class="gcal-type-tag" :class="evt.event_id.startsWith('sidequest_') ? 'type-sidequest' : 'type-original'">
                  {{ evt.event_id.startsWith('sidequest_') ? 'SideQuest' : 'Google日曆' }}
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- Preferences Settings Card -->
        <section class="profile-section-card preferences-card">
          <div class="card-section-title">
            <div class="title-left">
              <span class="pref-icon">⚙️</span>
              <div>
                <h3>個人探索偏好設定 (Preferences)</h3>
                <small>自訂室內冷氣、人潮容忍度、預算及遮蔭偏好，Agent 將以此量身推薦</small>
              </div>
            </div>
          </div>

          <!-- Environment Preference -->
          <div class="pref-group">
            <label class="pref-label">❄ 環境空間偏好</label>
            <div class="pref-pill-group">
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: userPreferences.prefer_indoor }"
                @click="userPreferences.prefer_indoor = true"
              >
                ❄ 偏好室內冷氣直達
              </button>
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: !userPreferences.prefer_indoor }"
                @click="userPreferences.prefer_indoor = false"
              >
                ☀️ 接受戶外活動
              </button>
            </div>
          </div>

          <!-- Crowd Preference -->
          <div class="pref-group">
            <label class="pref-label">👥 人潮擁擠容忍度</label>
            <div class="pref-pill-group">
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: userPreferences.avoid_crowd }"
                @click="userPreferences.avoid_crowd = true"
              >
                🍃 避開擁擠排隊 (低密度優先)
              </button>
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: !userPreferences.avoid_crowd }"
                @click="userPreferences.avoid_crowd = false"
              >
                👥 喜愛熱鬧氛圍
              </button>
            </div>
          </div>

          <!-- Budget Cap -->
          <div class="pref-group">
            <label class="pref-label">💰 單人預算上限 (TWD)</label>
            <div class="pref-chips-group">
              <button
                v-for="budget in [300, 500, 800, 1200, 2000]"
                :key="budget"
                type="button"
                class="pref-chip"
                :class="{ active: userPreferences.max_budget === budget }"
                @click="userPreferences.max_budget = budget"
              >
                {{ budget >= 2000 ? '無上限 (NT$ 2000+)' : `NT$ ${budget}` }}
              </button>
            </div>
          </div>

          <!-- Route Preference -->
          <div class="pref-group">
            <label class="pref-label">🚶 路線與交通規劃偏好</label>
            <div class="pref-pill-group">
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: userPreferences.route_preference === 'shade_first' }"
                @click="userPreferences.route_preference = 'shade_first'"
              >
                🍃 優先高遮蔭 / 地下街直通
              </button>
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: userPreferences.route_preference === 'fastest' }"
                @click="userPreferences.route_preference = 'fastest'"
              >
                ⚡ 最短乘車時間
              </button>
              <button
                type="button"
                class="pref-pill-btn"
                :class="{ active: userPreferences.route_preference === 'accessible' }"
                @click="userPreferences.route_preference = 'accessible'"
              >
                ♿ 無障礙 / 大件行李友善
              </button>
            </div>
          </div>

          <!-- Favorite Interest Tags -->
          <div class="pref-group">
            <label class="pref-label">🏷️ 感興趣的活動主題 (可複選)</label>
            <div class="pref-tags-grid">
              <button
                v-for="tag in availableTags"
                :key="tag"
                type="button"
                class="pref-tag-chip"
                :class="{ active: userPreferences.favorite_tags.includes(tag) }"
                @click="togglePreferenceTag(tag)"
              >
                <span class="tag-check">{{ userPreferences.favorite_tags.includes(tag) ? '✓' : '+' }}</span>
                {{ tag }}
              </button>
            </div>
          </div>

          <div class="pref-save-action">
            <button type="button" class="btn-save-preferences" @click="saveUserPreferences">
              💾 儲存偏好設定並更新推薦
            </button>
          </div>
        </section>

        <!-- Active Planned Trip in Profile -->
        <section v-if="activePlannedPlace" class="profile-section-card active-plan-profile-card">
          <div class="card-section-title">
            <div class="title-left">
              <span class="plan-icon">🎯</span>
              <div>
                <h3>進行中探險行程 (Active Itinerary)</h3>
                <small>已排入 Google 日曆並鎖定行程提醒</small>
              </div>
            </div>
            <button type="button" class="btn-cancel-plan-mini" @click="cancelActivePlan">✕ 清除</button>
          </div>
          <div class="plan-card-body">
            <h4>{{ activePlannedPlace.name }}</h4>
            <p>📍 {{ activePlannedPlace.address || activePlannedPlace.location || '台北市' }}</p>
            <div class="plan-action-buttons">
              <button type="button" class="btn-plan-action" @click="openGoogleMapsNavigation(activePlannedPlace)">
                🗺️ Google 導航
              </button>
              <button type="button" class="btn-plan-action" @click="openShareModal(activePlannedPlace)">
                🔗 分享卡片
              </button>
              <button type="button" class="btn-plan-action" @click="triggerSimulateConditionChange(activePlannedPlace)">
                🚨 模擬突發狀況
              </button>
            </div>
          </div>
        </section>
      </div>

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

        <!-- Active Planned Trip Banner (Step 9, 11, 13) -->
        <div v-if="activePlannedPlace" class="active-plan-banner">
          <div class="active-plan-main" @click="openPlaceDetails(activePlannedPlace)">
            <div class="active-plan-header">
              <span class="active-plan-badge"><span class="pulse-dot"></span> 進行中行程 · 已同步 Google Calendar</span>
              <small class="active-plan-timing">{{ getSmartDepartureAdvice(activePlannedPlace).summary }}</small>
            </div>
            <strong class="active-plan-title">{{ activePlannedPlace.name }}</strong>
            <p class="active-plan-meta">{{ activePlannedPlace.address }} · {{ activePlannedPlace.dateRange }} · 人流 {{ crowdLabel(activePlannedPlace.crowd) }}</p>
          </div>
          <div class="active-plan-btns">
            <button type="button" class="plan-btn plan-btn-alert" @click="triggerSimulateConditionChange(activePlannedPlace)" title="模擬午後雷雨或人潮暴增警報">
              🚨 模擬突發變更
            </button>
            <button type="button" class="plan-btn" @click="openShareModal(activePlannedPlace)">
              🔗 分享
            </button>
            <button type="button" class="plan-btn plan-btn-close" @click="cancelActivePlan" title="取消鎖定行程">
              ✕
            </button>
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

        <!-- Quick Date & Time Picker Chips (Step 1 & 4) -->
        <div class="quick-dates-row">
          <span class="date-selector-label">活動日期：</span>
          <button
            v-for="dateOpt in quickDateOptions"
            :key="dateOpt.label"
            type="button"
            class="quick-date-chip"
            :class="{ active: selectedDateTag === dateOpt.label }"
            @click="selectDateTag(dateOpt)"
          >
            {{ dateOpt.label }}
          </button>
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
              <div v-for="(step, idx) in aiThoughtSteps" :key="idx" class="thought-step-item">
                <span class="step-badge">{{ step.step || `STEP 0${idx + 1}` }}</span>
                <div class="step-body">
                  <strong>{{ step.title || step.action }}</strong>
                  <p>{{ step.detail || step.thought || step.output }}</p>
                </div>
              </div>
            </div>
          </div>

          <p v-if="aiReply" class="agent-markdown-text">{{ aiReply }}</p>
          <p v-if="aiError" class="agent-error-text">{{ aiError }}</p>
        </div>

        <!-- PRD Section 6 Multi-criteria Recommendation Cards -->
        <section v-if="aiRecommendations.length" class="agent-recommendations-section">
          <div class="agent-rec-header">
            <div>
              <span class="rec-kicker">AGENT PICKS · 智慧城市多準則決策</span>
              <h2>為你量身打造的推薦方案</h2>
            </div>
            <strong v-if="aiEvaluatedCount">已即時評估 {{ aiEvaluatedCount }} 場活動與路徑</strong>
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
                <div class="rec-card-actions" @click.stop>
                  <button
                    type="button"
                    class="rec-action-btn"
                    title="加入 Google Calendar"
                    @click="addToGoogleCalendar(places.find(p => p.id === card.event?.id) || card.event)"
                  >📅</button>
                  <button
                    type="button"
                    class="rec-action-btn"
                    :class="{ active: pkPlaceIds.has(card.event?.id) }"
                    title="加入 PK 比較"
                    @click="togglePkPlace(places.find(p => p.id === card.event?.id) || card.event)"
                  >⚖️</button>
                  <button
                    type="button"
                    class="rec-action-btn"
                    title="生成分享卡片"
                    @click="openShareModal(places.find(p => p.id === card.event?.id) || card.event)"
                  >🔗</button>
                  <button
                    type="button"
                    class="feedback-btn"
                    :class="{ active: feedbackMap.get(card.event?.id)?.isHelpful === true }"
                    title="推薦精準，很喜歡"
                    @click="openFeedbackModal(places.find(p => p.id === card.event?.id) || card.event, true)"
                  >👍</button>
                  <button
                    type="button"
                    class="feedback-btn"
                    :class="{ active: feedbackMap.get(card.event?.id)?.isHelpful === false }"
                    title="人潮偏多或提供建議"
                    @click="openFeedbackModal(places.find(p => p.id === card.event?.id) || card.event, false)"
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
            v-if="activeFilter !== '為你推薦'"
            type="button"
            class="view-all"
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

              <!-- Quick Place Card Actions -->
              <div class="place-card-bottom-bar" @click.stop>
                <button type="button" class="card-mini-btn" title="加入 Google Calendar" @click="addToGoogleCalendar(place)">
                  <span>📅</span> 加行事曆
                </button>
                <button
                  type="button"
                  class="card-mini-btn"
                  :class="{ active: pkPlaceIds.has(place.id) }"
                  title="加入 PK 比較"
                  @click="togglePkPlace(place)"
                >
                  <span>⚖️</span> {{ pkPlaceIds.has(place.id) ? '已加 PK' : 'PK 比較' }}
                </button>
                <button type="button" class="card-mini-btn" title="分享活動卡片" @click="openShareModal(place)">
                  <span>🔗</span> 分享
                </button>
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

    <!-- Floating PK Bottom Bar (Step 8) -->
    <div v-if="pkPlaces.length > 0" class="floating-pk-bar">
      <div class="pk-bar-info" @click="showPkModal = true">
        <span class="pk-bar-icon">⚖️</span>
        <div>
          <strong>活動 PK 比較 ({{ pkPlaces.length }}/3)</strong>
          <small>點擊展開多準則對比矩陣 (人潮、遮蔭、車程、票價)</small>
        </div>
      </div>
      <div class="pk-bar-actions">
        <button type="button" class="pk-matrix-open-btn" @click="showPkModal = true">
          查看 PK 矩陣 ↗
        </button>
        <button type="button" class="pk-bar-clear-btn" @click="clearPk" title="清空清單">
          ✕
        </button>
      </div>
    </div>

    <!-- 1. Alternative Plan Modal (Step 13 & 14) -->
    <div v-if="showAlternativeModal && alternativePlanData" class="sidequest-modal-overlay" @click.self="dismissAlternativePlan">
      <div class="sidequest-modal alt-modal">
        <header class="sidequest-modal-header alt-modal-header">
          <div>
            <span class="alt-tag">🚨 天候與人流突發警報 · STEP 13-14</span>
            <h2>{{ alternativePlanData.alertTitle }}</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="dismissAlternativePlan">×</button>
        </header>

        <div class="alt-alert-box">
          <p>{{ alternativePlanData.alertMessage }}</p>
          <small>{{ alternativePlanData.agentAdvice }}</small>
        </div>

        <div class="alt-comparison-cards">
          <div class="alt-card original">
            <span class="alt-card-kicker">原定計畫</span>
            <h3>{{ alternativePlanData.original?.name }}</h3>
            <div class="alt-card-metrics">
              <span class="metric-alert">🌧 降雨機率 85%</span>
              <span class="metric-alert">👥 人流指數 88 (嚴重擁擠)</span>
              <span>🚇 戶外換乘步行 12 分鐘</span>
            </div>
          </div>
          <div class="alt-vs-badge">VS</div>
          <div class="alt-card recommended">
            <span class="alt-card-kicker recommended-kicker">✨ AGENT 推薦室內備案</span>
            <h3>{{ alternativePlanData.alternative?.name }}</h3>
            <div class="alt-card-metrics">
              <span class="metric-good">❄️ 室內 0% 曝曬/完全防雨</span>
              <span class="metric-good">👥 人流指數 {{ alternativePlanData.alternative?.crowd || 25 }} (寬敞舒適)</span>
              <span class="metric-good">🚇 地下街直通免淋雨</span>
            </div>
          </div>
        </div>

        <div class="alt-benefits-list">
          <strong>備案優勢：</strong>
          <ul>
            <li v-for="(b, i) in alternativePlanData.benefits" :key="i">{{ b }}</li>
          </ul>
        </div>

        <footer class="alt-modal-footer">
          <button type="button" class="alt-btn-secondary" @click="dismissAlternativePlan">
            維持原計畫 (忽略警報)
          </button>
          <button type="button" class="alt-btn-primary" @click="applyAlternativePlan">
            ✨ 改用這個方案並更新行事曆
          </button>
        </footer>
      </div>
    </div>

    <!-- 2. PK Comparison Matrix Modal (Step 8) -->
    <div v-if="showPkModal" class="sidequest-modal-overlay" @click.self="showPkModal = false">
      <div class="sidequest-modal pk-modal">
        <header class="sidequest-modal-header">
          <div>
            <span>MULTI-EVENT PK MATRIX · STEP 8</span>
            <h2>活動多準則 PK 對比矩陣</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showPkModal = false">×</button>
        </header>
        <p class="persona-intro">已選取 {{ pkPlaces.length }} 個活動，直接比較即時人流、微氣候遮蔭、大眾運輸與費用：</p>

        <div v-if="pkPlaces.length === 0" class="events-state">
          尚未選取任何 PK 活動，請在卡片點擊「⚖️ PK 比較」加入活動。
        </div>
        <div v-else class="pk-matrix-scroll-wrapper">
          <table class="pk-matrix-table">
            <thead>
              <tr>
                <th class="matrix-metric-col">評估維度</th>
                <th v-for="p in pkPlaces" :key="p.id" class="matrix-place-col">
                  <strong>{{ p.name }}</strong>
                  <small>{{ p.category }} · {{ p.district }}</small>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>👥 人流擁擠程度</td>
                <td v-for="p in pkPlaces" :key="`crowd-${p.id}`">
                  <span class="metric crowd-metric" :class="crowdClass(p.crowd)">
                    {{ crowdLabel(p.crowd) }} ({{ p.crowd }})
                  </span>
                </td>
              </tr>
              <tr>
                <td>☀️ 遮蔭率 / 曝曬度</td>
                <td v-for="p in pkPlaces" :key="`sun-${p.id}`">
                  <strong>{{ p.isIndoor ? '❄️ 室內 0% 曝曬' : `☀️ 曝曬 ${p.sun}% (遮蔭 ${p.shade || 60}%)` }}</strong>
                </td>
              </tr>
              <tr>
                <td>🚇 交通時間與費用</td>
                <td v-for="p in pkPlaces" :key="`transit-${p.id}`">
                  <strong>車程約 25 分 · NT$20~25</strong>
                  <small>{{ p.transit_summary || '捷運板南線/淡水信義線直達' }}</small>
                </td>
              </tr>
              <tr>
                <td>🎟 門票標準</td>
                <td v-for="p in pkPlaces" :key="`fee-${p.id}`">
                  <strong>{{ p.fee || '免費參觀' }}</strong>
                </td>
              </tr>
              <tr>
                <td>🕒 智慧出發建議</td>
                <td v-for="p in pkPlaces" :key="`timing-${p.id}`">
                  <small>{{ getSmartDepartureAdvice(p).summary }}</small>
                </td>
              </tr>
              <tr>
                <td>🎯 決策動作</td>
                <td v-for="p in pkPlaces" :key="`act-${p.id}`">
                  <div class="pk-action-btns">
                    <button type="button" class="pk-win-btn" @click="selectPkWinner(p)">
                      🎯 選定此行程
                    </button>
                    <button type="button" class="pk-cal-btn" @click="addToGoogleCalendar(p)">
                      📅 加行事曆
                    </button>
                    <button type="button" class="pk-remove-link" @click="togglePkPlace(p)">
                      移除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 3. Share Card Modal (Step 10) -->
    <div v-if="showShareModal && shareTargetPlace" class="sidequest-modal-overlay" @click.self="showShareModal = false">
      <div class="sidequest-modal share-modal">
        <header class="sidequest-modal-header">
          <div>
            <span>SOCIAL SHARE CARD · STEP 10</span>
            <h2>生成活動分享卡片</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showShareModal = false">×</button>
        </header>

        <!-- Social Preview Card -->
        <div class="share-card-preview" :style="{ '--share-accent': shareTargetPlace.color }">
          <div class="share-card-topbar">
            <span class="share-brand">SIDEQUEST 智慧活動</span>
            <span class="share-badge">{{ shareTargetPlace.category }}</span>
          </div>
          <h3 class="share-title">{{ shareTargetPlace.name }}</h3>
          <p class="share-meta">📍 {{ shareTargetPlace.address }}</p>
          <p class="share-meta">🗓️ {{ shareTargetPlace.dateRange }} ({{ shareTargetPlace.time }})</p>
          <div class="share-metrics-strip">
            <span>👥 人流：{{ crowdLabel(shareTargetPlace.crowd) }}</span>
            <span>☀️ {{ shareTargetPlace.isIndoor ? '室內空調' : `曝曬 ${shareTargetPlace.sun}%` }}</span>
            <span>🎫 {{ shareTargetPlace.fee || '免費入場' }}</span>
          </div>
          <div class="share-transit-tag">
            🚇 建議交通：{{ shareTargetPlace.transit_summary || '捷運大眾運輸直達' }}
          </div>
          <div class="share-card-footer">
            <small>✨ 由 SideQuest 智慧城市 Agent 規劃生成</small>
          </div>
        </div>

        <footer class="share-modal-actions">
          <button type="button" class="share-action-primary" @click="copyShareText(shareTargetPlace)">
            📋 複製分享文字與連結
          </button>
          <button type="button" class="share-action-line" @click="shareToLine(shareTargetPlace)">
            💬 透過 LINE 一鍵分享
          </button>
          <button type="button" class="share-action-gcal" @click="addToGoogleCalendar(shareTargetPlace)">
            📅 加入 Google Calendar
          </button>
        </footer>
      </div>
    </div>

    <!-- 4. Post-event Feedback Modal (Step 16) -->
    <div v-if="showFeedbackModal && feedbackTargetPlace" class="sidequest-modal-overlay" @click.self="showFeedbackModal = false">
      <div class="sidequest-modal feedback-modal">
        <header class="sidequest-modal-header">
          <div>
            <span>AGENT FEEDBACK · STEP 16</span>
            <h2>活動與推薦意見回饋</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showFeedbackModal = false">×</button>
        </header>
        <p class="persona-intro">針對【{{ feedbackTargetPlace.name }}】，此推薦是否符合您的期待？</p>

        <div class="feedback-rating-row">
          <button
            type="button"
            class="feedback-choice-btn"
            :class="{ active: feedbackRating === true }"
            @click="feedbackRating = true"
          >
            👍 符合期待 / 體驗良好
          </button>
          <button
            type="button"
            class="feedback-choice-btn"
            :class="{ active: feedbackRating === false }"
            @click="feedbackRating = false"
          >
            👎 不太符合 / 需改進
          </button>
        </div>

        <div class="feedback-tags-section">
          <label>可複選回饋標籤：</label>
          <div class="feedback-tags-grid">
            <button
              v-for="tag in feedbackTagsList"
              :key="tag"
              type="button"
              class="feedback-tag-chip"
              :class="{ active: selectedFeedbackTags.has(tag) }"
              @click="toggleFeedbackTag(tag)"
            >
              {{ tag }}
            </button>
          </div>
        </div>

        <footer class="feedback-modal-footer">
          <button type="button" class="alt-btn-primary" @click="submitDetailedFeedback">
            送出回饋並更新偏好模型
          </button>
        </footer>
      </div>
    </div>

    <!-- Persona Switcher & Google Sign-In Modal (PRD 7.1 & Google Auth) -->
    <div v-if="showPersonaModal" class="persona-modal-overlay" @click.self="showPersonaModal = false">
      <div class="persona-modal">
        <header class="persona-modal-header">
          <div>
            <span>IDENTITY & LOGIN · PRD 7.1</span>
            <h2>登入 Google 帳號 / 切換 Persona</h2>
          </div>
          <button type="button" class="modal-close-btn" @click="showPersonaModal = false">×</button>
        </header>

        <!-- Real Google Account Sign-In Section -->
        <div class="persona-google-section">
          <div class="google-section-header">
            <svg class="google-g-logo" viewBox="0 0 24 24" width="22" height="22">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <div>
              <strong>真實 Google 帳號授權登入</strong>
              <small>Google 官方帳號選擇器，後端會驗證簽章與 Client ID</small>
            </div>
          </div>

          <div class="google-signin-action-row">
            <span v-if="isGoogleAuthLoading" class="google-auth-loading"><span class="btn-spinner"></span> 正在驗證 Google 帳號…</span>
            <div v-else-if="googleAuthReady" id="google_signin_modal" class="google-signin-slot"></div>
            <small v-else class="google-auth-error">{{ googleAuthError || 'Google 登入初始化中…' }}</small>
          </div>
        </div>

        <div class="persona-divider">
          <span>或選擇 4 大預設 Demo 測試角色</span>
        </div>

        <p class="persona-intro">免密碼切換預設測試角色，立即體驗個人化推薦、收藏清單與自訂人流偏好：</p>
        <div class="personas-grid">
          <div
            v-for="p in personas"
            :key="p.id"
            class="persona-card"
            :class="{ active: activePersona.id === p.id && !isGoogleLoggedIn }"
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

    <!-- Google Calendar Conflict Resolution Modal (Step 11 & Schedule Conflict Resolution) -->
    <div
      v-if="showCalendarConflictModal && calendarConflictData"
      class="sidequest-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="conflict-title"
      @click.self="showCalendarConflictModal = false"
    >
      <div class="sidequest-modal conflict-modal">
        <header class="sidequest-modal-header conflict-modal-header">
          <div class="conflict-header-title">
            <span class="conflict-alert-icon">⚠️</span>
            <div>
              <span class="conflict-kicker">GOOGLE CALENDAR CONFLICT · STEP 11</span>
              <h2 id="conflict-title">Google 日曆時段衝突調解</h2>
            </div>
          </div>
          <button type="button" class="modal-close-btn" @click="showCalendarConflictModal = false">×</button>
        </header>

        <p class="conflict-prompt-text">
          在您預計排入的活動時段內，Google 日曆已有既定行程。SideQuest 已為您比對雙方細節，請選擇處理方式：
        </p>

        <!-- Side-by-side Conflict Comparison Matrix -->
        <div class="conflict-comparison-grid">
          <!-- Existing Event -->
          <div class="conflict-card existing-card">
            <div class="conflict-card-badge">📌 原定 Google 日曆行程</div>
            <h3 class="conflict-event-name">{{ calendarConflictData.conflictingEvents?.[0]?.title || '既定行程' }}</h3>
            <div class="conflict-meta-item">
              <span class="meta-icon">🕒</span>
              <span><strong>時間：</strong>{{ calendarConflictData.conflictingEvents?.[0]?.start_time ? calendarConflictData.conflictingEvents[0].start_time.substring(11, 16) : '14:00' }} - {{ calendarConflictData.conflictingEvents?.[0]?.end_time ? calendarConflictData.conflictingEvents[0].end_time.substring(11, 16) : '16:30' }}</span>
            </div>
            <div class="conflict-meta-item">
              <span class="meta-icon">📍</span>
              <span><strong>地點：</strong>{{ calendarConflictData.conflictingEvents?.[0]?.location || '信義區會議室' }}</span>
            </div>
            <div class="conflict-meta-item">
              <span class="meta-icon">🏷️</span>
              <span><strong>性質：</strong>工作 / 團隊會議</span>
            </div>
            <p class="conflict-event-note">
              {{ calendarConflictData.conflictingEvents?.[0]?.description || '固定週期日程備忘' }}
            </p>
          </div>

          <div class="conflict-vs-divider">VS</div>

          <!-- New Proposed SideQuest Place -->
          <div class="conflict-card new-event-card">
            <div class="conflict-card-badge new-badge">✨ 新增 SideQuest 探險</div>
            <h3 class="conflict-event-name">{{ calendarConflictData.targetPlace?.name }}</h3>
            <div class="conflict-meta-item">
              <span class="meta-icon">🕒</span>
              <span><strong>時間：</strong>14:30 - 17:00 (週六)</span>
            </div>
            <div class="conflict-meta-item">
              <span class="meta-icon">📍</span>
              <span><strong>地點：</strong>{{ calendarConflictData.targetPlace?.address || calendarConflictData.targetPlace?.name }}</span>
            </div>
            <div class="conflict-meta-item">
              <span class="meta-icon">👥</span>
              <span><strong>人流：</strong>{{ crowdLabel(calendarConflictData.targetPlace?.crowd) }} ({{ calendarConflictData.targetPlace?.crowd || 30 }})</span>
            </div>
            <div class="conflict-meta-item">
              <span class="meta-icon">🛡️</span>
              <span><strong>遮蔭：</strong>{{ calendarConflictData.targetPlace?.isIndoor ? '室內冷氣直達 (95% 遮蔭)' : '戶外遮蔭路線' }}</span>
            </div>
            <p class="conflict-event-note">
              {{ calendarConflictData.targetPlace?.description }}
            </p>
          </div>
        </div>

        <!-- Decision Action Buttons -->
        <div class="conflict-actions-list">
          <button
            type="button"
            class="conflict-choice-btn btn-overwrite"
            @click="resolveCalendarConflict('overwrite')"
          >
            <div class="choice-icon">🥇</div>
            <div class="choice-text">
              <strong>改用新活動 (覆蓋原行程)</strong>
              <span>將原【{{ calendarConflictData.conflictingEvents?.[0]?.title }}】從 Google 日曆移除，改排入【{{ calendarConflictData.targetPlace?.name }}】</span>
            </div>
          </button>

          <button
            type="button"
            class="conflict-choice-btn btn-both"
            @click="resolveCalendarConflict('both')"
          >
            <div class="choice-icon">🔀</div>
            <div class="choice-text">
              <strong>兩者皆保留 (並存於日曆)</strong>
              <span>在 Google 日曆中同時排入兩項活動，並自動加註時段重疊備忘</span>
            </div>
          </button>

          <button
            type="button"
            class="conflict-choice-btn btn-keep-original"
            @click="resolveCalendarConflict('cancel')"
          >
            <div class="choice-icon">🥈</div>
            <div class="choice-text">
              <strong>保留原行程 (放棄新活動)</strong>
              <span>維持原定日曆安排，不將【{{ calendarConflictData.targetPlace?.name }}】排入 Google 日曆</span>
            </div>
          </button>
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
      <button :class="{ active: selectedTab === 'profile' }" @click="selectedTab = 'profile'">
        <span>👤</span>偏好與日曆
      </button>
    </nav>
  </main>
</template>
