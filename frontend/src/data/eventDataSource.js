/**
 * @typedef {Object} EventRecord
 * @property {string} id
 * @property {string} title
 * @property {string} category
 * @property {string} startDate
 * @property {string} endDate
 * @property {string} highlight
 * @property {string} venue
 * @property {string} address
 * @property {string} fee
 * @property {string} admission
 * @property {string} organizer
 * @property {string} description
 * @property {string} sourceUrl
 * @property {string} secondarySourceUrl
 * @property {string} confidence
 * @property {string} notes
 */

/**
 * EventDataSource interface.
 *
 * Any future backend adapter only needs to expose the same list() contract.
 * @typedef {Object} EventDataSource
 * @property {string} label
 * @property {() => Promise<EventRecord[]>} list
 */

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
  const category = typeof event.category === 'string' ? event.category : event.category?.value || '城市活動'
  const price = event.price_type === 'free' ? '免費' : event.price_amount ? `NT$ ${event.price_amount}` : '請見活動來源'
  return {
    id: String(event.id || `api-event-${index + 1}`),
    title: event.title || `台北活動 ${index + 1}`,
    category,
    startDate: event.start_time?.slice(0, 10) || '',
    endDate: event.end_time?.slice(0, 10) || '',
    highlight: '',
    venue: event.venue_name || '',
    address: event.location?.address || '台北市',
    fee: price,
    admission: event.registration_status || '',
    organizer: event.source_platform || '',
    description: event.description || '',
    sourceUrl: event.source_url || '',
    secondarySourceUrl: '',
    confidence: 'backend',
    notes: '',
    latitude: event.location?.latitude,
    longitude: event.location?.longitude,
  }
}

export class CsvEventDataSource {
  label = 'CSV MOCK'

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
  }

  async list() {
    const response = await fetch(`${this.baseUrl}/events?limit=100`)
    if (!response.ok) throw new Error(`Events API request failed: ${response.status}`)
    const payload = await response.json()
    const events = Array.isArray(payload) ? payload : payload.events || []
    return events.map(recordFromApiEvent)
  }
}

/**
 * Runtime selection keeps the view layer independent from the storage/API choice.
 * @returns {EventDataSource}
 */
export function createEventDataSource() {
  return import.meta.env.VITE_EVENT_SOURCE === 'api'
    ? new ApiEventDataSource()
    : new CsvEventDataSource()
}
