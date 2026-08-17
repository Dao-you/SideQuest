/**
 * @typedef {Object} AgentResult
 * @property {string} reply
 * @property {string} provider
 * @property {number} used_event_count
 * @property {string[]} recommended_ids
 */

/**
 * AgentService interface.
 *
 * The UI depends only on recommend(); the current mock can be replaced by an
 * HTTP/Cloud Run adapter later without changing the page components.
 * @typedef {Object} AgentService
 * @property {string} label
 * @property {(payload: {message: string, events: Object[]}) => Promise<AgentResult>} recommend
 */

const topicKeywords = [
  ['展覽', ['展', '藝術', '文化', '文博', '動漫', '史努比', '福音戰士']],
  ['音樂', ['音樂', '演唱', 'festival', '煙火']],
  ['戶外', ['戶外', '劇場', '市集', '煙火']],
  ['親子', ['親子', '小孩', '家庭']],
]

function scoreEvent(event, message) {
  const query = message.toLowerCase()
  const haystack = [event.name, event.category, event.description, event.fee].join(' ').toLowerCase()
  let score = 0
  for (const [, keywords] of topicKeywords) {
    if (keywords.some((keyword) => query.includes(keyword.toLowerCase()))) {
      score += keywords.some((keyword) => haystack.includes(keyword.toLowerCase())) ? 4 : 0
    }
  }
  if (query.includes('免費') && event.fee.includes('免費')) score += 5
  if ((query.includes('室內') || query.includes('冷氣') || query.includes('不要太熱')) && event.isIndoor) score += 4
  if ((query.includes('人少') || query.includes('避開人潮') || query.includes('不要太擠')) && event.crowd < 50) score += 5
  if (query.includes('戶外') && !event.isIndoor) score += 4
  score += Math.max(0, 3 - event.crowd / 35)
  return score
}

export class MockAgentService {
  label = 'MOCK AGENT'

  async recommend({ message, events }) {
    await new Promise((resolve) => window.setTimeout(resolve, 650))
    const ranked = [...events].sort((left, right) => scoreEvent(right, message) - scoreEvent(left, message))
    const topEvents = ranked.slice(0, 3)
    const first = topEvents[0]
    const crowdHint = first?.crowd < 50 ? '人流相對舒適' : '目前人流較熱鬧，建議避開尖峰'
    const reply = first
      ? `我先從 ${events.length} 個活動裡挑出「${first.name}」作為第一站：${crowdHint}，${first.sun < 40 ? '曝曬程度也較低' : '如果怕熱，建議把戶外行程放在傍晚'}。另外也可以比較 ${topEvents.slice(1).map((event) => event.name).join('、')}。`
      : '目前沒有可供比較的活動，請稍後再試。'
    return {
      reply,
      provider: this.label,
      used_event_count: events.length,
      recommended_ids: topEvents.map((event) => event.id),
    }
  }
}

export class HttpAgentService {
  label = 'BACKEND AGENT'

  constructor(baseUrl = import.meta.env.VITE_AGENT_API_URL || '') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  async recommend(payload) {
    const response = await fetch(`${this.baseUrl}/api/v1/agent/ai-recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error(`Agent request failed: ${response.status}`)
    return response.json()
  }
}

/** @returns {AgentService} */
export function createAgentService() {
  return import.meta.env.VITE_AGENT_SOURCE === 'http'
    ? new HttpAgentService()
    : new MockAgentService()
}
