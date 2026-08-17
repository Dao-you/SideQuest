/**
 * Agent Interaction Service (Gemini 3.7 Flash Agent with SSE Reasoning Trace & Multi-Criteria Ranking).
 */
import { apiClient } from './apiClient'

/**
 * @typedef {Object} AgentResult
 * @property {string} reply - Full natural language markdown reply
 * @property {string} provider - Model / provider identifier
 * @property {number} used_event_count - Count of events evaluated
 * @property {string[]} recommended_ids - Ranked IDs
 * @property {Array<{tool: string, event_id: string, reason: string}>} tool_calls
 * @property {Array<Object>} recommendations - Full PRD recommendation cards
 * @property {Array<Object>} thought_steps - Agent reasoning steps
 * @property {Object} [parsed_criteria] - Structured query criteria
 * @property {string} [one_sentence_summary] - Concise summary of changes
 * @property {string} [dispersal_summary] - Smart dispersal insight
 */

const fallbackQuickPrompts = [
  '今天下午想看展，不想太熱',
  '想找人少的地方散步喝咖啡',
  '今晚信義區有什麼推薦活動？',
]

export class MockAgentService {
  label = 'MOCK AGENT'

  async getQuickPrompts() {
    return {
      example_prompts: fallbackQuickPrompts.map((prompt) => ({
        title: prompt,
        prompt,
        category: 'general',
        icon: '✦',
      })),
      quick_tags: [
        { id: 'indoor', label: '室內避暑', icon: '❄', filter_key: 'is_indoor', filter_value: true },
        { id: 'low_crowd', label: '避開人潮', icon: '🍃', filter_key: 'avoid_crowd', filter_value: true },
        { id: 'free', label: '免費入場', icon: '🎟', filter_key: 'is_free_only', filter_value: true },
      ],
    }
  }

  async recommend({ message, events = [] }) {
    await new Promise((resolve) => window.setTimeout(resolve, 500))
    const query = (message || '').toLowerCase()

    const ranked = [...events].sort((a, b) => {
      let scoreA = 0
      let scoreB = 0
      const textA = [a.name, a.category, a.description, a.fee].join(' ').toLowerCase()
      const textB = [b.name, b.category, b.description, b.fee].join(' ').toLowerCase()

      if (query.includes('室內') || query.includes('冷氣')) {
        if (a.isIndoor) scoreA += 5
        if (b.isIndoor) scoreB += 5
      }
      if (query.includes('人少') || query.includes('避開')) {
        if (a.crowd < 45) scoreA += 5
        if (b.crowd < 45) scoreB += 5
      }
      if (query.includes('免費')) {
        if (a.fee?.includes('免費')) scoreA += 5
        if (b.fee?.includes('免費')) scoreB += 5
      }
      scoreA += (100 - (a.crowd || 50)) / 20
      scoreB += (100 - (b.crowd || 50)) / 20
      return scoreB - scoreA
    })

    const topEvents = ranked.slice(0, 3)
    const first = topEvents[0]
    const crowdHint = first?.crowd < 50 ? '人流相對舒適' : '目前人流適中，建議多利用捷運地下街'

    const reply = first
      ? `我從 ${events.length} 個活動中為你挑選了「${first.name}」：${crowdHint}，${first.sun < 40 ? '曝曬程度低且交通便利' : '建議傍晚時段前往或走地下連通道'}。備選推薦包括 ${topEvents.slice(1).map((e) => e.name).join('、')}。`
      : '已為你檢索台北市最新活動目錄。'

    return {
      reply,
      provider: this.label,
      used_event_count: events.length,
      recommended_ids: topEvents.map((e) => e.id),
      tool_calls: topEvents.map((e, index) => ({
        tool: 'present_event_card',
        event_id: e.id,
        reason: index === 0 ? '🎯 整體條件最符合需求' : index === 1 ? '🍃 舒適人少替代方案' : '✨ 特色探索推薦',
      })),
      thought_steps: [
        { step: 1, title: '解析自然語言意圖', thought: `提取關鍵詞：「${message}」，判斷為週末休閒行程需求。` },
        { step: 2, title: '查詢台北活動資料庫', thought: `比對 ${events.length} 個即時活動與展覽。` },
        { step: 3, title: '多準則評分與人流疏導', thought: '依 35% 相關度、25% 時間、20% 遮蔭、10% 預算、10% 舒適度計算綜合得分。' },
      ],
      recommendations: topEvents.map((place, idx) => ({
        event: {
          id: place.id,
          title: place.name,
          category: place.category,
          venue_name: place.address,
          description: place.description,
          location: { address: place.address, latitude: place.position?.lat, longitude: place.position?.lng },
          is_indoor: place.isIndoor,
          start_time: place.dateRange,
          end_time: place.dateRange,
          price_type: place.fee?.includes('免費') ? 'free' : 'paid',
          source_url: place.sourceUrl,
        },
        card_role: idx === 0 ? 'TOP_MATCH' : idx === 1 ? 'DISPERSAL_ALTERNATIVE' : 'EXPLORATION_GEM',
        card_role_label: idx === 0 ? '🎯 最符合需求' : idx === 1 ? '🍃 舒適替代選擇' : '✨ 特色探索選擇',
        total_score: idx === 0 ? 94.5 : idx === 1 ? 88.0 : 83.5,
        match_score: idx === 0 ? 95 : 85,
        accessibility_score: 90,
        weather_comfort_score: 88,
        crowd_score: place.crowd,
        crowd_level: place.crowd < 40 ? 'LOW' : place.crowd < 70 ? 'MODERATE' : 'HIGH',
        transit_summary: place.distance,
        recommendation_reason: idx === 0 ? '室內涼爽、交通極為便利' : '人潮相對少，適合放鬆步調',
        badges: [
          { type: 'COOL_HAVEN', label: '涼爽避暑', color: 'blue' },
          { type: 'HIDDEN_GEM', label: '舒適少人', color: 'green' },
        ],
      })),
      one_sentence_summary: '已依照偏好推薦 3 大城市提案。',
      dispersal_summary: '目前松菸周邊人流較高，推薦的替代場館舒適度提升 30% 以上。',
    }
  }

  async submitFeedback() {
    return { status: 'success', message: '感謝回饋！' }
  }
}

export class HttpAgentService {
  label = 'GEMINI 3.7 FLASH'
  fallbackMock = new MockAgentService()

  /**
   * Fetch dynamic quick prompts and tags from backend.
   */
  async getQuickPrompts() {
    try {
      return await apiClient.request('/agent/quick-prompts')
    } catch (err) {
      console.warn('Quick prompts API failed, using fallback:', err)
      return this.fallbackMock.getQuickPrompts()
    }
  }

  /**
   * Send chat query to Agent with optional SSE real-time streaming.
   *
   * @param {Object} params
   * @param {string} params.message
   * @param {number} [params.user_latitude=25.0330]
   * @param {number} [params.user_longitude=121.5654]
   * @param {string} [params.session_id]
   * @param {string} [params.user_id='demo_weekend_explorer']
   * @param {boolean} [params.avoid_crowd_strict=true]
   * @param {boolean} [params.prefer_indoor]
   * @param {number} [params.max_budget_twd]
   * @param {Array<Object>} [params.events=[]]
   * @param {Function} [params.onStreamEvent] - Callback for real-time SSE stream events: (type, data)
   */
  async recommend(params) {
    const {
      message,
      user_latitude = 25.0330,
      user_longitude = 121.5654,
      session_id,
      user_id = 'demo_weekend_explorer',
      avoid_crowd_strict = true,
      prefer_indoor,
      max_budget_twd,
      events = [],
      onStreamEvent,
    } = params

    const payload = {
      message,
      user_latitude,
      user_longitude,
      session_id,
      user_id,
      avoid_crowd_strict,
      prefer_indoor,
      max_budget_twd,
    }

    // 1. If real-time streaming callback is provided, stream via SSE
    if (typeof onStreamEvent === 'function') {
      return new Promise((resolve, reject) => {
        let accumulatedReply = ''
        const thoughtSteps = []
        let parsedCriteria = null
        let recommendationCards = []
        let dispersalSummary = ''
        let oneSentenceSummary = ''

        const controller = apiClient.stream('/agent/chat/stream', payload, {
          onEvent: (type, data) => {
            onStreamEvent(type, data)

            if (type === 'thought') {
              thoughtSteps.push(data)
            } else if (type === 'understanding') {
              parsedCriteria = data
            } else if (type === 'markdown_chunk') {
              accumulatedReply += data.text || ''
            } else if (type === 'recommendation_cards') {
              recommendationCards = data.cards || []
              dispersalSummary = data.dispersal_summary || ''
            } else if (type === 'done') {
              oneSentenceSummary = data.one_sentence_summary || ''
            }
          },
          onError: async (err) => {
            console.warn('Agent SSE streaming failed, trying fallback synchronous chat:', err)
            try {
              const fallbackRes = await this.fallbackSyncChat(payload, events)
              resolve(fallbackRes)
            } catch (fallbackErr) {
              const mockRes = await this.fallbackMock.recommend({ message, events })
              resolve(mockRes)
            }
          },
          onDone: () => {
            const recommendedIds = recommendationCards.map((c) => c.event?.id).filter(Boolean)
            const toolCalls = recommendationCards.map((c) => ({
              tool: 'present_event_card',
              event_id: c.event?.id,
              reason: c.recommendation_reason || c.card_role_label,
            }))

            resolve({
              reply: accumulatedReply,
              provider: this.label,
              used_event_count: events.length || recommendationCards.length,
              recommended_ids: recommendedIds,
              tool_calls: toolCalls,
              recommendations: recommendationCards,
              thought_steps: thoughtSteps,
              parsed_criteria: parsedCriteria,
              one_sentence_summary: oneSentenceSummary,
              dispersal_summary: dispersalSummary,
            })
          },
        })
      })
    }

    // 2. Non-streaming synchronous request
    return this.fallbackSyncChat(payload, events)
  }

  async fallbackSyncChat(payload, events) {
    try {
      const res = await apiClient.request('/agent/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      const recommendedIds = (res.recommendations || []).map((c) => c.event?.id).filter(Boolean)
      const toolCalls = (res.recommendations || []).map((c) => ({
        tool: 'present_event_card',
        event_id: c.event?.id,
        reason: c.recommendation_reason || c.card_role_label,
      }))

      return {
        reply: res.reply || '',
        provider: this.label,
        used_event_count: events.length || res.recommendations?.length || 0,
        recommended_ids: recommendedIds,
        tool_calls: toolCalls,
        recommendations: res.recommendations || [],
        thought_steps: res.thought_steps || [],
        parsed_criteria: res.parsed_criteria,
        one_sentence_summary: res.one_sentence_summary || '',
        dispersal_summary: res.dispersal_summary || '',
      }
    } catch (err) {
      console.warn('Agent sync chat failed, falling back to mock agent:', err)
      return this.fallbackMock.recommend({ message: payload.message, events })
    }
  }

  /**
   * Submit satisfaction feedback for recommendations (PRD Section 6 Stage 10).
   */
  async submitFeedback(feedback) {
    try {
      return await apiClient.request('/agent/feedback', {
        method: 'POST',
        body: JSON.stringify(feedback),
      })
    } catch (err) {
      console.warn('Feedback API failed:', err)
      return this.fallbackMock.submitFeedback()
    }
  }
}

/**
 * Creates the agent service instance.
 * Defaults to HttpAgentService with automatic mock fallback on error.
 * @returns {HttpAgentService | MockAgentService}
 */
export function createAgentService() {
  return import.meta.env.VITE_AGENT_SOURCE === 'mock'
    ? new MockAgentService()
    : new HttpAgentService()
}
