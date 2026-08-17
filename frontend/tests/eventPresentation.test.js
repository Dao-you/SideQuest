import test from 'node:test'
import assert from 'node:assert/strict'

import { toEventPlace } from '../src/data/eventPresentation.js'

function event(overrides = {}) {
  return {
    id: 'event-1',
    title: '測試活動',
    category: '城市活動',
    fee: '免費',
    ...overrides,
  }
}

test('does not invent a map position when source coordinates are missing', () => {
  const place = toEventPlace(event({ latitude: null, longitude: null }), 0)

  assert.equal(place.position, null)
  assert.equal(place.distanceShort, '位置待確認')
})

test('uses source coordinates and only explicit crowd measurements', () => {
  const place = toEventPlace(event({
    latitude: 25.0478,
    longitude: 121.517,
    crowdScore: 42,
    crowdIsMock: true,
  }), 0)

  assert.deepEqual(place.position, { lat: 25.0478, lng: 121.517 })
  assert.equal(place.crowd, 42)
  assert.equal(place.crowdIsMock, true)
  assert.equal(place.sun, 35)
  assert.equal(place.shade, 65)
})
