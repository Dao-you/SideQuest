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

const mockLocations = [
  { position: { lat: 25.0566, lng: 121.5085 }, color: '#5b8f89', distance: '捷運大橋頭站 步行 6 分鐘', distanceShort: '24 min' },
  { position: { lat: 25.0527, lng: 121.5203 }, color: '#e9855f', distance: '捷運中山站 步行 3 分鐘', distanceShort: '14 min' },
  { position: { lat: 25.0365, lng: 121.5658 }, color: '#7b7bb1', distance: '捷運台北 101/世貿站 步行 4 分鐘', distanceShort: '26 min' },
  { position: { lat: 25.0577, lng: 121.6169 }, color: '#d9a441', distance: '捷運南港站 步行 5 分鐘', distanceShort: '32 min' },
  { position: { lat: 25.0438, lng: 121.5608 }, color: '#77a58d', distance: '捷運國父紀念館站 步行 7 分鐘', distanceShort: '31 min' },
  { position: { lat: 25.0395, lng: 121.5432 }, color: '#c37b9e', distance: '捷運大安站 步行 5 分鐘', distanceShort: '21 min' },
  { position: { lat: 25.0531, lng: 121.5186 }, color: '#6992b6', distance: '捷運雙連站 步行 4 分鐘', distanceShort: '16 min' },
  { position: { lat: 24.9497, lng: 121.3507 }, color: '#8b9b65', distance: '捷運鶯歌站 步行 8 分鐘', distanceShort: '46 min' },
  { position: { lat: 25.0418, lng: 121.5592 }, color: '#d58a62', distance: '捷運忠孝敦化站 步行 6 分鐘', distanceShort: '29 min' },
  { position: { lat: 25.0604, lng: 121.4616 }, color: '#9a82ad', distance: '捷運府中站 步行 9 分鐘', distanceShort: '37 min' },
]

const mockMetrics = [
  { crowd: 58, sun: 68 }, { crowd: 44, sun: 12 }, { crowd: 72, sun: 18 }, { crowd: 66, sun: 10 }, { crowd: 49, sun: 22 },
  { crowd: 34, sun: 14 }, { crowd: 27, sun: 8 }, { crowd: 31, sun: 76 }, { crowd: 78, sun: 34 }, { crowd: 81, sun: 6 },
]

/**
 * Converts canonical EventRecord into the map & card presentation model.
 */
export function toEventPlace(event, index) {
  const fallbackLoc = mockLocations[index % mockLocations.length]
  const metrics = mockMetrics[index % mockMetrics.length] ?? { crowd: 45, sun: 25 }
  const dateRange = [event.startDate, event.endDate].filter(Boolean).join(' – ')
  const sourceUrl = event.sourceUrl || event.secondarySourceUrl || ''

  // Compute transit distance string
  let distance = fallbackLoc.distance
  let distanceShort = fallbackLoc.distanceShort
  if (event.mrtStation) {
    const walkMins = Math.max(2, Math.round((event.mrtDistanceMeters || 300) / 75))
    distance = `捷運${event.mrtStation} 步行 ${walkMins} 分鐘`
    distanceShort = `${walkMins} min`
  }

  const categoryColor = categoryColors[event.category] || fallbackLoc.color

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
    crowd: metrics.crowd,
    sun: event.isIndoor ? 15 : metrics.sun,
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
    position: (event.latitude && event.longitude)
      ? { lat: Number(event.latitude), lng: Number(event.longitude) }
      : fallbackLoc.position,
    label: String.fromCharCode(65 + (index % 26)),
    isIndoor: typeof event.isIndoor === 'boolean'
      ? event.isIndoor
      : /室內|快閃|展覽|POP|店|文創|品牌商展|文化|動漫|藝術|咖啡|科技/.test(`${event.category}${event.title}`),
    tags: event.tags || [],
    imageUrl: event.imageUrl || '',
  }
}
