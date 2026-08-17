const mockLocations = [
  { position: { lat: 25.0566, lng: 121.5085 }, color: '#5b8f89', distance: '捷運 24 分鐘', distanceShort: '24 min' },
  { position: { lat: 25.0527, lng: 121.5203 }, color: '#e9855f', distance: '捷運 14 分鐘', distanceShort: '14 min' },
  { position: { lat: 25.0365, lng: 121.5658 }, color: '#7b7bb1', distance: '捷運 26 分鐘', distanceShort: '26 min' },
  { position: { lat: 25.0577, lng: 121.6169 }, color: '#d9a441', distance: '捷運 32 分鐘', distanceShort: '32 min' },
  { position: { lat: 25.0438, lng: 121.5608 }, color: '#77a58d', distance: '捷運 31 分鐘', distanceShort: '31 min' },
  { position: { lat: 25.0395, lng: 121.5432 }, color: '#c37b9e', distance: '捷運 21 分鐘', distanceShort: '21 min' },
  { position: { lat: 25.0531, lng: 121.5186 }, color: '#6992b6', distance: '捷運 16 分鐘', distanceShort: '16 min' },
  { position: { lat: 24.9497, lng: 121.3507 }, color: '#8b9b65', distance: '捷運 46 分鐘', distanceShort: '46 min' },
  { position: { lat: 25.0418, lng: 121.5592 }, color: '#d58a62', distance: '捷運 29 分鐘', distanceShort: '29 min' },
  { position: { lat: 25.0604, lng: 121.4616 }, color: '#9a82ad', distance: '捷運 37 分鐘', distanceShort: '37 min' },
]

// Prototype-only environmental signals. Real crowd/weather services can replace this adapter.
const mockMetrics = [
  { crowd: 58, sun: 68 }, { crowd: 44, sun: 12 }, { crowd: 72, sun: 18 }, { crowd: 66, sun: 10 }, { crowd: 49, sun: 22 },
  { crowd: 34, sun: 14 }, { crowd: 27, sun: 8 }, { crowd: 31, sun: 76 }, { crowd: 78, sun: 34 }, { crowd: 81, sun: 6 },
]

/**
 * Converts the canonical EventRecord into the current map/card view model.
 * This is intentionally separate from EventDataSource so backend data can arrive
 * without forcing a rewrite of the UI.
 */
export function toEventPlace(event, index) {
  const location = mockLocations[index] ?? mockLocations[0]
  const metrics = mockMetrics[index] ?? { crowd: 50, sun: 30 }
  const dateRange = [event.startDate, event.endDate].filter(Boolean).join(' – ')
  const sourceUrl = event.sourceUrl || event.secondarySourceUrl || ''
  return {
    id: event.id,
    name: event.title,
    shortName: event.title.slice(0, 13),
    category: event.category,
    address: event.address,
    description: event.description || event.admission || '活動詳情請見來源網站。',
    crowd: metrics.crowd,
    sun: metrics.sun,
    distance: location.distance,
    distanceShort: location.distanceShort,
    rating: '—',
    time: event.highlight || '活動期間請見來源',
    dateRange: dateRange || '活動日期請見來源',
    fee: event.fee,
    admission: event.admission,
    organizer: event.organizer,
    source: event.sourceUrl || event.secondarySourceUrl || event.confidence,
    sourceUrl,
    color: location.color,
    position: event.latitude && event.longitude
      ? { lat: event.latitude, lng: event.longitude }
      : location.position,
    label: String.fromCharCode(65 + index),
    isIndoor: /室內|快閃|展覽|POP|店|文創|品牌商展|文化|動漫|藝術/.test(`${event.category}${event.title}`),
  }
}
