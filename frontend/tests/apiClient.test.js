import test from 'node:test'
import assert from 'node:assert/strict'

import { ApiClient, parseSSEMessage, splitSSEMessages } from '../src/services/apiClient.js'

test('splits CRLF-delimited SSE messages without dropping events', () => {
  const stream = [
    'event: recommendation_cards\r\n',
    'data: {"recommendations":[{"event_id":"evt-1"}]}\r\n\r\n',
    'event: done\r\n',
    'data: {"one_sentence_summary":"完成"}\r\n\r\n',
  ].join('')

  const { messages, remainder } = splitSSEMessages(stream)

  assert.equal(remainder, '')
  assert.equal(messages.length, 2)
  assert.deepEqual(parseSSEMessage(messages[0]), {
    eventName: 'recommendation_cards',
    data: { recommendations: [{ event_id: 'evt-1' }] },
  })
})

test('keeps an incomplete SSE message for the next network chunk', () => {
  const { messages, remainder } = splitSSEMessages('event: markdown\ndata: {"chunk":"半')

  assert.deepEqual(messages, [])
  assert.equal(remainder, 'event: markdown\ndata: {"chunk":"半')
})

test('streams CRLF SSE events across arbitrary response chunks', async () => {
  const originalFetch = globalThis.fetch
  const encoder = new TextEncoder()
  const chunks = [
    'event: recommendation_cards\r\ndata: {"cards":[',
    '{"event":{"id":"evt-1"}}]}\r\n\r\nevent: done\r\n',
    'data: {"status":"completed"}\r\n\r\n',
  ]
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } })

  try {
    const events = []
    await new Promise((resolve, reject) => {
      new ApiClient('https://example.test').stream('/stream', {}, {
        onEvent: (eventName, data) => events.push({ eventName, data }),
        onError: reject,
        onDone: resolve,
      })
    })

    assert.deepEqual(events.map((event) => event.eventName), ['recommendation_cards', 'done'])
    assert.equal(events[0].data.cards[0].event.id, 'evt-1')
  } finally {
    globalThis.fetch = originalFetch
  }
})
