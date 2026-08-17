import test from 'node:test'
import assert from 'node:assert/strict'

import { SHADE_TIME_SCENARIOS, toEventPlace } from '../src/data/eventPresentation.js'

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
  assert.equal(place.sun, 30)
  assert.equal(place.shade, 70)
  assert.equal(place.shadeTimePeriod, 'morning')
})

test('returns visibly different deterministic shade values for all three periods', () => {
  const values = Object.fromEntries(
    SHADE_TIME_SCENARIOS.map((scenario) => [
      scenario.id,
      toEventPlace(event({ isIndoor: false }), 0, scenario.id),
    ]),
  )

  assert.deepEqual(
    [values.morning.shade, values.noon.shade, values.evening.shade],
    [70, 55, 80],
  )
  assert.match(values.noon.sunLabel, /正午/)
  assert.match(values.evening.sunLabel, /傍晚/)
})
