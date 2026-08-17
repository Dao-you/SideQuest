import test from 'node:test'
import assert from 'node:assert/strict'

import { applyShadeScenarioToGoogleRoute, RoutesService } from '../src/services/routesService.js'

test('derives noon shade from the same Google walking steps shown in the UI', () => {
  const result = applyShadeScenarioToGoogleRoute({
    segments: [
      { mode: 'WALK', instruction: '往西南前進', duration_minutes: 1, distance_meters: 21 },
      { mode: 'WALK', instruction: '右轉進入巷口', duration_minutes: 1, distance_meters: 62 },
      { mode: 'TRANSIT', instruction: '公車開往保一總隊', duration_minutes: 42, distance_meters: 10797 },
      { mode: 'WALK', instruction: '往南步行', duration_minutes: 5, distance_meters: 345 },
      { mode: 'WALK', instruction: '右轉繼續步行', duration_minutes: 7, distance_meters: 509 },
    ],
  }, 'noon')

  assert.equal(result.shadePercentage, 20)
  assert.equal(result.shadedDistanceMeters, 187)
  assert.equal(result.sunExposureMinutes, 11.2)
  assert.equal(result.walkingDistanceMeters, 937)
  assert.equal(result.segments[2].segment_kind, 'transit')
  assert.equal(result.segments[2].shade_percentage, null)
  assert.ok(result.segments.filter((segment) => segment.segment_kind === 'walk').every((segment) => segment.shade_percentage === 20))
})

test('sends the selected shade period and maps it back to the UI model', async () => {
  const originalFetch = globalThis.fetch
  let requestBody = null
  globalThis.fetch = async (_url, options) => {
    requestBody = JSON.parse(options.body)
    return new Response(JSON.stringify({
      origin: '目前位置',
      destination: '測試場地',
      total_duration_minutes: 20,
      total_distance_meters: 3000,
      transit_summary: '捷運 20 分鐘',
      underground_or_shaded_percentage: 90,
      comfort_score: 92,
      route_advice: '正午驗收情境',
      sun_exposure_minutes: 0.7,
      shaded_distance_meters: 405,
      shade_time_period: 'noon',
      segments: [],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }

  try {
    const result = await new RoutesService().computeRoute({
      originLat: 25.04,
      originLng: 121.52,
      destLat: 25.05,
      destLng: 121.56,
      shadeTimePeriod: 'noon',
    })

    assert.equal(requestBody.shade_time_period, 'noon')
    assert.equal(result.shadeTimePeriod, 'noon')
    assert.equal(result.shadePercentage, 90)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('uses period-specific fallback numbers when the backend is unavailable', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response('{}', { status: 503 })

  try {
    const result = await new RoutesService().computeRoute({
      destLat: 25.05,
      destLng: 121.56,
      shadeTimePeriod: 'evening',
    })

    assert.equal(result.shadeTimePeriod, 'evening')
    assert.equal(result.shadePercentage, 75)
    assert.equal(result.sunExposureMinutes, 1.8)
  } finally {
    globalThis.fetch = originalFetch
  }
})
