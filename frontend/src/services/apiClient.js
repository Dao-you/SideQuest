/**
 * Core API Client for SideQuest Frontend.
 * Supports standard JSON REST calls and Server-Sent Events (SSE) streaming.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

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

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n\n')
          buffer = lines.pop() || ''

          for (const message of lines) {
            if (!message.trim()) continue
            let eventName = 'message'
            let dataStr = ''

            const msgLines = message.split('\n')
            for (const line of msgLines) {
              if (line.startsWith('event:')) {
                eventName = line.slice(6).trim()
              } else if (line.startsWith('data:')) {
                dataStr += line.slice(5).trim()
              }
            }

            if (dataStr) {
              try {
                const parsedData = JSON.parse(dataStr)
                onEvent?.(eventName, parsedData)
              } catch {
                onEvent?.(eventName, dataStr)
              }
            }
          }
        }

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
