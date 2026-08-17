import test from 'node:test'
import assert from 'node:assert/strict'

import { RoutesService } from '../src/services/routesService.js'

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
    assert.equal(result.shadePercentage, 98)
    assert.equal(result.sunExposureMinutes, 0.1)
  } finally {
    globalThis.fetch = originalFetch
  }
})
