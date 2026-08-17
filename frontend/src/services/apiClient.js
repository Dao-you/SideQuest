/**
 * Core API Client for SideQuest Frontend.
 * Supports standard JSON REST calls and Server-Sent Events (SSE) streaming.
 */

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '/api/v1'

export function parseSSEMessage(message) {
  if (!message.trim()) return null

  let eventName = 'message'
  const dataLines = []

  for (const line of message.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }

  if (dataLines.length === 0) return null

  const dataStr = dataLines.join('\n')
  try {
    return { eventName, data: JSON.parse(dataStr) }
  } catch {
    return { eventName, data: dataStr }
  }
}

export function splitSSEMessages(buffer) {
  const messages = buffer.split(/\r?\n\r?\n/)
  return { messages: messages.slice(0, -1), remainder: messages.at(-1) || '' }
}

export class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  /**
   * Standard JSON fetch with error handling.
   */
  async request(path, options = {}) {
    const url = path.startsWith('http') ? path : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      let errorMessage = `API request failed with status ${response.status}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        // ignore json parse error
      }
      throw new Error(errorMessage)
    }

    return response.json()
  }

  /**
   * SSE Stream Consumer using standard Fetch and ReadableStream.
   * Emits typed events via onEvent callback.
   *
   * @param {string} path - API endpoint path
   * @param {Object} body - POST request payload
   * @param {Object} callbacks - { onEvent(event, data), onError(error), onDone() }
   * @returns {AbortController} - Controller to cancel stream
   */
  stream(path, body, { onEvent, onError, onDone }) {
    const controller = new AbortController()
    const url = path.startsWith('http') ? path : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`

    ;(async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify(body),
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`SSE stream failed: ${response.status}`)
        }

        if (!response.body) {
          throw new Error('SSE stream response has no readable body')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        const dispatchMessage = (message) => {
          const parsed = parseSSEMessage(message)
          if (parsed) onEvent?.(parsed.eventName, parsed.data)
        }

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const split = splitSSEMessages(buffer)
          const messages = split.messages
          buffer = split.remainder
          messages.forEach(dispatchMessage)
        }

        buffer += decoder.decode()
        if (buffer.trim()) dispatchMessage(buffer)

        onDone?.()
      } catch (err) {
        if (err.name !== 'AbortError') {
          onError?.(err)
        }
      }
    })()

    return controller
  }
}

export const apiClient = new ApiClient()
