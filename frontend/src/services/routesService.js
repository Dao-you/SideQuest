/**
 * Routes & Transit Thermal Comfort Planning Service.
 */
import { apiClient } from './apiClient.js'

const fallbackShadeScenarios = Object.freeze({
  morning: { label: '早上 09:00', shade: 65, exposure: 2.5, distance: 325 },
  noon: { label: '正午 12:30', shade: 45, exposure: 3.9, distance: 225 },
  evening: { label: '傍晚 17:30', shade: 75, exposure: 1.8, distance: 375 },
})

const googleWalkShadeScenarios = Object.freeze({
  morning: { label: '早上 09:00', outdoor: 0.35, partial: 0.65, covered: 0.90 },
  noon: { label: '正午 12:30', outdoor: 0.20, partial: 0.50, covered: 0.85 },
  evening: { label: '傍晚 17:30', outdoor: 0.45, partial: 0.70, covered: 0.92 },
})

function isWalkingMode(mode) {
  return ['WALK', 'WALKING'].includes(String(mode || '').toUpperCase())
}

function shadeRatioForInstruction(instruction, scenario) {
  if (/地下|連通道|室內|站內|月台|underpass|underground/i.test(instruction)) return scenario.covered
  if (/騎樓|林蔭|公園|arcade|tree/i.test(instruction)) return scenario.partial
  return scenario.outdoor
}

/**
 * Apply a deterministic demo scenario to the same Google Maps walking steps
 * shown in the UI. Transit distance is intentionally excluded.
 */
export function applyShadeScenarioToGoogleRoute(route, shadeTimePeriod = 'morning') {
  const scenario = googleWalkShadeScenarios[shadeTimePeriod] || googleWalkShadeScenarios.morning
  let walkingDistanceMeters = 0
  let walkingDurationMinutes = 0
  let shadedDistanceMeters = 0
  let sunExposureMinutes = 0

  const segments = (route.segments || []).map((segment) => {
    if (!isWalkingMode(segment.mode)) {
      return { ...segment, segment_kind: 'transit', shade_percentage: null }
    }

    const distance = Math.max(0, Number(segment.distance_meters) || 0)
    const duration = Math.max(0, Number(segment.duration_minutes) || 0)
    const ratio = shadeRatioForInstruction(segment.instruction || '', scenario)
    walkingDistanceMeters += distance
    walkingDurationMinutes += duration
    shadedDistanceMeters += distance * ratio
    sunExposureMinutes += duration * (1 - ratio)

    return {
      ...segment,
      segment_kind: 'walk',
      shade_percentage: Math.round(ratio * 100),
      is_shaded_or_underground: ratio >= 0.60,
    }
  })

  const shadePercentage = walkingDistanceMeters > 0
    ? Math.round((shadedDistanceMeters / walkingDistanceMeters) * 100)
    : 100
  const roundedSunExposure = Math.round(sunExposureMinutes * 10) / 10
  const roundedShadedDistance = Math.round(shadedDistanceMeters)

  return {
    ...route,
    segments,
    shadePercentage,
    sunExposureMinutes: roundedSunExposure,
    shadedDistanceMeters: roundedShadedDistance,
    walkingDistanceMeters: Math.round(walkingDistanceMeters),
    walkingDurationMinutes: Math.round(walkingDurationMinutes * 10) / 10,
    comfortScore: Math.max(30, Math.min(100, Math.round(shadePercentage * 0.6 + 40 - roundedSunExposure * 1.5))),
    shadeTimePeriod,
    shadeMethod: 'google-walking-steps-demo',
    routeAdvice: `${scenario.label}固定情境：依畫面中的 Google Maps 步行分段估算，步行遮蔭約 ${shadePercentage}%，直曬約 ${roundedSunExposure} 分鐘；公車與捷運車程未納入步行遮蔭率。`,
  }
}

/**
 * Standard Google Polyline decoder.
 * @param {string} encoded
 * @returns {Array<{lat: number, lng: number}>}
 */
export function decodePolyline(encoded) {
  if (!encoded) return []
  const points = []
  let index = 0
  const len = encoded.length
  let lat = 0
  let lng = 0

  while (index < len) {
    let b
    let shift = 0
    let result = 0
    do {
      b = encoded.charCodeAt(index++) - 63
      result |= (b & 0x1f) << shift
      shift += 5
    } while (b >= 0x20)
    const dlat = (result & 1) !== 0 ? ~(result >> 1) : (result >> 1)
    lat += dlat

    shift = 0
    result = 0
    do {
      b = encoded.charCodeAt(index++) - 63
      result |= (b & 0x1f) << shift
      shift += 5
    } while (b >= 0x20)
    const dlng = (result & 1) !== 0 ? ~(result >> 1) : (result >> 1)
    lng += dlng

    points.push({ lat: lat / 1e5, lng: lng / 1e5 })
  }
  return points
}

export class RoutesService {
  /**
   * Compute transit route with thermal comfort, multimodal comparison, and preference optimization.
   * @param {Object} params
   * @param {number} params.originLat
   * @param {number} params.originLng
   * @param {number} params.destLat
   * @param {number} params.destLng
   * @param {string} [params.destName]
   * @param {boolean} [params.prioritizeShade=true]
   * @param {'morning'|'noon'|'evening'} [params.shadeTimePeriod='morning']
   * @param {string} [params.preference='fastest']
   * @param {boolean} [params.wheelchairAccessible=false]
   * @param {string} [params.departureTime='now']
   */
  async computeRoute({
    originLat = 25.0478,
    originLng = 121.5319,
    destLat,
    destLng,
    destName = '目標活動場地',
    prioritizeShade = true,
    shadeTimePeriod = 'morning',
    preference = 'fastest',
    wheelchairAccessible = false,
    departureTime = 'now',
  }) {
    const payload = {
      origin_lat: originLat,
      origin_lng: originLng,
      destination_lat: destLat,
      destination_lng: destLng,
      destination_name: destName,
      prioritize_shade: prioritizeShade,
      shade_time_period: shadeTimePeriod,
      preference: preference,
      wheelchair_accessible: wheelchairAccessible || preference === 'wheelchair',
      departure_time: departureTime,
      travel_mode: 'TRANSIT',
    }

    try {
      const result = await apiClient.request('/routes/compute', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      const decodedPath = result.encoded_polyline
        ? decodePolyline(result.encoded_polyline)
        : [
            { lat: originLat, lng: originLng },
            { lat: (originLat + destLat) / 2, lng: (originLng + destLng) / 2 },
            { lat: destLat, lng: destLng },
          ]

      return {
        origin: result.origin,
        destination: result.destination,
        preference: result.preference || preference,
        totalDurationMinutes: result.total_duration_minutes,
        totalDistanceMeters: result.total_distance_meters,
        transitSummary: result.transit_summary,
        shadePercentage: result.underground_or_shaded_percentage,
        comfortScore: result.comfort_score,
        routeAdvice: result.route_advice,
        sunExposureMinutes: result.sun_exposure_minutes ?? 0,
        shadedDistanceMeters: result.shaded_distance_meters ?? Math.round(result.total_distance_meters * (result.underground_or_shaded_percentage / 100)),
        shadeTimePeriod: result.shade_time_period ?? shadeTimePeriod,
        accessibilityNote: result.accessibility_note,
        crowdNote: result.crowd_note,
        multimodal: result.multimodal || {
          walk_calories: Math.round(result.total_distance_meters * 0.06),
          walk_duration_minutes: Math.round(result.total_distance_meters / 70),
          walk_distance_meters: result.total_distance_meters,
          bike_calories: Math.round(result.total_distance_meters * 0.04),
          bike_duration_minutes: Math.round(result.total_distance_meters / 250),
          bike_cost_twd: 20,
          bike_station: `YouBike 2.0 站點 (近 ${destName})`,
          taxi_duration_minutes: Math.max(5, Math.round(result.total_distance_meters / 420) + 3),
          taxi_cost_twd: Math.max(85, Math.round(85 + (result.total_distance_meters / 200) * 5)),
          transit_duration_minutes: result.total_duration_minutes,
        },
        segments: result.segments || [],
        path: decodedPath,
        hasRealPath: Boolean(result.encoded_polyline),
      }
    } catch (err) {
      console.warn('Routes compute API failed, generating smart fallback route:', err)
      const scenario = fallbackShadeScenarios[shadeTimePeriod] || fallbackShadeScenarios.morning
      const dist = Math.round(Math.hypot((originLat - destLat) * 111000, (originLng - destLng) * 100000)) || 2800
      const walkMin = Math.max(5, Math.round(dist / 70))
      const bikeMin = Math.max(3, Math.round(dist / 250))
      const taxiMin = Math.max(5, Math.round(dist / 420) + 3)
      const taxiFare = Math.max(85, Math.round(85 + (dist / 200) * 5))
      return {
        origin: '目前位置 (台北市市區)',
        destination: destName,
        preference: preference,
        totalDurationMinutes: 22,
        totalDistanceMeters: dist,
        transitSummary: '大眾運輸與步行示意（實際路徑待確認）',
        shadePercentage: scenario.shade,
        comfortScore: Math.round(scenario.shade * 0.6 + 40 - scenario.exposure * 1.5),
        sunExposureMinutes: scenario.exposure,
        shadedDistanceMeters: scenario.distance,
        shadeTimePeriod,
        accessibilityNote: preference === 'wheelchair' ? '無障礙需求已記錄，實際電梯與坡道仍待 Google Maps 路徑確認' : '實際步行條件待確認',
        crowdNote: preference === 'less_crowded' ? '避開人潮偏好已記錄，實際車廂人流待確認' : '即時人流待確認',
        multimodal: {
          walk_calories: Math.round(walkMin * 4.2),
          walk_duration_minutes: walkMin,
          walk_distance_meters: dist,
          bike_calories: Math.round(bikeMin * 4.1),
          bike_duration_minutes: bikeMin,
          bike_cost_twd: 20,
          bike_station: `YouBike 2.0 站點 (近 ${destName})`,
          taxi_duration_minutes: taxiMin,
          taxi_cost_twd: taxiFare,
          transit_duration_minutes: 22,
        },
        routeAdvice: `${scenario.label}保守 fallback：以共 500 公尺步行示意估算遮蔭約 ${scenario.shade}%，預估戶外直曬 ${scenario.exposure} 分鐘；實際路徑待 Google Maps 確認。`,
        segments: [
          { mode: 'WALK', instruction: '從目前位置步行至鄰近大眾運輸站點', duration_minutes: 4, distance_meters: 250, is_shaded_or_underground: false, shade_percentage: scenario.shade, segment_kind: 'walk' },
          { mode: preference === 'more_bus' ? 'BUS' : 'SUBWAY', instruction: preference === 'more_bus' ? '搭乘市區幹線公車前往目標區域' : '搭乘捷運抵達目標站點', duration_minutes: 14, distance_meters: Math.max(300, dist - 500), is_shaded_or_underground: true },
          { mode: 'WALK', instruction: `由大眾運輸站點步行抵達 ${destName}`, duration_minutes: 4, distance_meters: 250, is_shaded_or_underground: false, shade_percentage: scenario.shade, segment_kind: 'walk' },
        ],
        path: [
          { lat: originLat, lng: originLng },
          { lat: (originLat * 0.5 + destLat * 0.5), lng: (originLng * 0.5 + destLng * 0.5) },
          { lat: destLat, lng: destLng },
        ],
        hasRealPath: false,
      }
    }
  }
}

export const routesService = new RoutesService()
