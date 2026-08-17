/**
 * Event Data Source with unified API client and CSV fallback.
 */

const CATEGORY_NAMES = {
  art: '當代藝術',
  music: '音樂現場',
  food: '美食探索',
  outdoor: '戶外漫遊',
  tech: '科技社群',
  family: '親子活動',
  cafe: '特色咖啡',
  craft: '文創手作',
  exhibition: '主題特展',
  market: '風格市集',
  workshop: '深度工作坊',
}

function parseCsv(text) {
  const rows = []
  let row = []
  let cell = ''
  let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index]
    const next = text[index + 1]
    if (quoted) {
      if (character === '"' && next === '"') {
        cell += '"'
        index += 1
      } else if (character === '"') {
        quoted = false
      } else {
        cell += character
      }
    } else if (character === '"') {
      quoted = true
    } else if (character === ',') {
      row.push(cell)
      cell = ''
    } else if (character === '\r' || character === '\n') {
      if (character === '\r' && next === '\n') index += 1
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
    } else {
      cell += character
    }
  }
  if (cell.length || row.length) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

function recordFromCsvRow(row, headers, index) {
  const values = Object.fromEntries(headers.map((header, columnIndex) => [header, row[columnIndex] ?? '']))
  return {
    id: `csv-event-${index + 1}`,
    title: values['活動名稱'] || `台北活動 ${index + 1}`,
    category: values['活動類型'] || '城市活動',
    startDate: values['開始日期'] || '',
    endDate: values['結束日期'] || '',
    highlight: values['本週重點時間'] || '',
    venue: values['地點'] || '',
    address: values['地址'] || '台北市',
    fee: values['費用'] || '請見活動來源',
    admission: values['入場／報名方式'] || '',
    organizer: values['主辦／營運'] || '',
    description: values['活動內容'] || '',
    sourceUrl: values['官網／主要來源'] || '',
    secondarySourceUrl: values['其他來源'] || '',
    confidence: values['資料可信度'] || '',
    notes: values['備註'] || '',
  }
}

function recordFromApiEvent(event, index) {
  const rawCat = typeof event.category === 'string' ? event.category : event.category?.value || 'art'
  const categoryLabel = CATEGORY_NAMES[rawCat.toLowerCase()] || rawCat || '城市活動'
  const price = event.price_type === 'free' ? '免費入場' : event.price_amount ? `NT$ ${event.price_amount}` : '請見活動來源'
  const admission = event.registration_status === 'free_entry'
    ? '免報名自由入場'
    : event.registration_status === 'open'
    ? '開放線上報名 / 購票'
    : event.registration_status || ''

  return {
    id: String(event.id || `api-event-${index + 1}`),
    venueId: String(event.venue_id || ''),
    title: event.title || `台北活動 ${index + 1}`,
    category: categoryLabel,
    rawCategory: rawCat,
    startDate: event.start_time?.slice(0, 10) || '',
    endDate: event.end_time?.slice(0, 10) || '',
    highlight: event.tags?.slice(0, 3).join(' · ') || '',
    venue: event.venue_name || '',
    address: event.location?.address || '台北市',
    district: event.location?.district || '台北市',
    fee: price,
    admission,
    organizer: event.source_platform || '主辦單位',
    description: event.description || '',
    sourceUrl: event.source_url || '',
    secondarySourceUrl: '',
    confidence: 'backend-verified',
    notes: '',
    latitude: event.location?.latitude,
    longitude: event.location?.longitude,
    mrtStation: event.location?.mrt_station,
    mrtDistanceMeters: event.location?.mrt_distance_meters,
    isIndoor: event.is_indoor ?? true,
    acAvailable: event.ac_available ?? true,
    rating: event.rating ?? 4.5,
    tags: event.tags || [],
    imageUrl: event.image_url || '',
  }
}

export class CsvEventDataSource {
  label = 'CSV DATA'

  constructor(url = '/data/taipeidope_events.csv') {
    this.url = url
  }

  async list() {
    const response = await fetch(this.url)
    if (!response.ok) throw new Error(`CSV request failed: ${response.status}`)
    const rows = parseCsv(await response.text())
    const headers = rows.shift() ?? []
    return rows
      .filter((row) => row.some((value) => value.trim()))
      .map((row, index) => recordFromCsvRow(row, headers, index))
  }
}

export class ApiEventDataSource {
  label = 'BACKEND API'

  constructor(baseUrl = import.meta.env.VITE_EVENTS_API_URL || '/api/v1') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.fallbackCsv = new CsvEventDataSource()
  }

  async list(filters = {}) {
    try {
      const queryParams = new URLSearchParams()
      queryParams.set('limit', '100')
      if (filters.category) queryParams.set('category', filters.category)
      if (filters.district) queryParams.set('district', filters.district)
      if (typeof filters.is_indoor === 'boolean') queryParams.set('is_indoor', String(filters.is_indoor))
      if (filters.keyword) queryParams.set('keyword', filters.keyword)

      const response = await fetch(`${this.baseUrl}/events?${queryParams.toString()}`)
      if (!response.ok) throw new Error(`Events API request failed: ${response.status}`)
      const payload = await response.json()
      const events = Array.isArray(payload) ? payload : payload.events || []
      if (events.length === 0) {
        return this.fallbackCsv.list()
      }
      return events.map(recordFromApiEvent)
    } catch (err) {
      console.warn('Backend events API unreachable, falling back to local CSV:', err)
      return this.fallbackCsv.list()
    }
  }
}

/**
 * Creates the event data source instance.
 * Defaults to ApiEventDataSource (with automatic CSV fallback).
 */
export function createEventDataSource() {
  return import.meta.env.VITE_EVENT_SOURCE === 'csv'
    ? new CsvEventDataSource()
    : new ApiEventDataSource()
}
