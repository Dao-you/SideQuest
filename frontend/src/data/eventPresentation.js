const categoryColors = {
  '當代藝術': '#5b8f89',
  '科技社群': '#4f759b',
  '音樂現場': '#7b7bb1',
  '戶外漫遊': '#8b9b65',
  '親子活動': '#d9a441',
  '特色咖啡': '#a07d60',
  '文創手作': '#77a58d',
  '主題特展': '#c37b9e',
  '風格市集': '#e9855f',
  '深度工作坊': '#6992b6',
  '城市活動': '#5b8f89',
}

export const SHADE_TIME_SCENARIOS = Object.freeze([
  { id: 'morning', label: '早上', time: '09:00', description: '斜射日照，建物與騎樓遮蔽較多' },
  { id: 'noon', label: '正午', time: '12:30', description: '太陽高度最高，戶外曝曬最明顯' },
  { id: 'evening', label: '傍晚', time: '17:30', description: '西斜日照，街廓陰影逐漸增加' },
])

const venueShadeByPeriod = Object.freeze({
  morning: { openPlaza: 38, treeCanopy: 78, covered: 86, urban: 70 },
  noon: { openPlaza: 18, treeCanopy: 65, covered: 78, urban: 55 },
  evening: { openPlaza: 52, treeCanopy: 86, covered: 91, urban: 80 },
})

/**
 * Calculate deterministic demo shade based on venue morphology and time scenario.
 */
export function calculateVenueSolarExposure(event, isIndoor, shadeTimePeriod = 'morning') {
  const period = venueShadeByPeriod[shadeTimePeriod] ? shadeTimePeriod : 'morning'
  const values = venueShadeByPeriod[period]
  const periodLabel = SHADE_TIME_SCENARIOS.find((scenario) => scenario.id === period)?.label || '早上'

  if (isIndoor) {
    return { sun: 0, shade: 100, label: `${periodLabel} · 室內空調 (0% 曝曬)` }
  }

  const text = `${event.title} ${event.venue || ''} ${event.address || ''} ${event.category || ''}`

  // Taipei open plazas & riverfronts
  if (/自由廣場|河濱|大佳|戶外大草原|圓山廣場|野餐|碧潭/.test(text)) {
    return { sun: 100 - values.openPlaza, shade: values.openPlaza, label: `${periodLabel} · 開闊廣場 (${values.openPlaza}% 遮蔭)` }
  }

  // Boulevard & dense tree canopy
  if (/仁愛|敦化|民生|大安森林|植物園|陽明山|青田/.test(text)) {
    return { sun: 100 - values.treeCanopy, shade: values.treeCanopy, label: `${periodLabel} · 林蔭大道 (${values.treeCanopy}% 遮蔭)` }
  }

  // Covered arcade (騎樓) and underground transit corridors
  if (/地下街|中山|赤峰|迪化|大稻埕|信義|南港|微風|新光|誠品|西門|大橋頭|忠孝/.test(text)) {
    return { sun: 100 - values.covered, shade: values.covered, label: `${periodLabel} · 騎樓/連通 (${values.covered}% 遮蔭)` }
  }

  // Standard Taipei urban street canyon
  return { sun: 100 - values.urban, shade: values.urban, label: `${periodLabel} · 都會街廓 (${values.urban}% 遮蔭)` }
}

/**
 * Converts canonical EventRecord into the map & card presentation model.
 */
export function toEventPlace(event, index, shadeTimePeriod = 'morning') {
  const dateRange = [event.startDate, event.endDate].filter(Boolean).join(' – ')
  const sourceUrl = event.sourceUrl || event.secondarySourceUrl || ''

  // Determine true indoor status
  const isIndoor = typeof event.isIndoor === 'boolean'
    ? event.isIndoor
    : /室內|快閃|展覽|POP|店|文創|品牌商展|文化|動漫|藝術|咖啡|科技|館|廳|中心/.test(`${event.category}${event.title}`)

  // Realistic micro-morphology solar & shade calculation
  const solarData = calculateVenueSolarExposure(event, isIndoor, shadeTimePeriod)

  // Compute transit distance string
  let distance = '交通資訊請見活動來源'
  let distanceShort = '位置待確認'
  if (event.mrtStation) {
    const walkMins = Math.max(2, Math.round((event.mrtDistanceMeters || 300) / 75))
    distance = `捷運${event.mrtStation} 步行 ${walkMins} 分鐘`
    distanceShort = `${walkMins} min`
  }

  const categoryColor = categoryColors[event.category] || '#5b8f89'
  const hasCoordinates = event.latitude != null
    && event.longitude != null
    && Number.isFinite(Number(event.latitude))
    && Number.isFinite(Number(event.longitude))

  return {
    id: event.id,
    name: event.title,
    shortName: event.title.length > 14 ? `${event.title.slice(0, 13)}…` : event.title,
    category: event.category,
    rawCategory: event.rawCategory,
    address: event.address || event.venue || '台北市',
    venue: event.venue || event.address || '台北市',
    district: event.district || '台北市',
    description: event.description || event.admission || '活動詳情請見主辦方或來源網站。',
    crowd: Number.isFinite(Number(event.crowdScore)) ? Number(event.crowdScore) : null,
    crowdIsMock: Boolean(event.crowdIsMock),
    sun: solarData.sun,
    shade: solarData.shade,
    sunLabel: solarData.label,
    shadeTimePeriod,
    distance,
    distanceShort,
    rating: event.rating ? String(event.rating) : '4.8',
    time: event.highlight || '全日或依場館開放時段',
    dateRange: dateRange || '當期活動',
    fee: event.fee,
    admission: event.admission,
    organizer: event.organizer,
    source: event.sourceUrl || event.secondarySourceUrl || event.confidence,
    sourceUrl,
    color: categoryColor,
    position: hasCoordinates
      ? { lat: Number(event.latitude), lng: Number(event.longitude) }
      : null,
    label: String.fromCharCode(65 + (index % 26)),
    isIndoor,
    tags: event.tags || [],
    imageUrl: event.imageUrl || '',
  }
}
