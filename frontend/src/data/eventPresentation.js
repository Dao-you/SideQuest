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

/**
 * Converts canonical EventRecord into the map & card presentation model.
 */
export function toEventPlace(event, index) {
  const dateRange = [event.startDate, event.endDate].filter(Boolean).join(' – ')
  const sourceUrl = event.sourceUrl || event.secondarySourceUrl || ''

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
    sun: null,
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
    isIndoor: typeof event.isIndoor === 'boolean'
      ? event.isIndoor
      : /室內|快閃|展覽|POP|店|文創|品牌商展|文化|動漫|藝術|咖啡|科技/.test(`${event.category}${event.title}`),
    tags: event.tags || [],
    imageUrl: event.imageUrl || '',
  }
}
