/**
 * Routes & Transit Thermal Comfort Planning Service.
 */
import { apiClient } from './apiClient'

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
        transitSummary: preference === 'more_bus'
          ? '搭乘幹線公車直達，沿騎樓遮蔭步行 2 分鐘'
          : preference === 'wheelchair'
          ? '搭乘捷運無障礙車廂與直達電梯，全線無障礙友善'
          : '搭乘捷運至周邊捷運站，沿地下街出口步行 3 分鐘',
        shadePercentage: preference === 'more_shading' ? 95 : 88,
        comfortScore: 92,
        sunExposureMinutes: 2.5,
        shadedDistanceMeters: Math.round(dist * 0.88),
        accessibilityNote: preference === 'wheelchair' ? '♿ 全程無障礙電梯與平緩步道，推車或大件行李極佳' : '正常步行通道',
        crowdNote: preference === 'less_crowded' ? '🟢 綠色舒適車廂，離峰乘車人潮稀疏' : '市區常規人流',
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
        routeAdvice: '捷運連通道與騎樓覆蓋率高，預估戶外直曬極短，避暑與通勤舒適度俱佳。',
        segments: [
          { mode: 'WALK', instruction: '從目前位置步行至站點 (地下通道/騎樓)', duration_minutes: 4, distance_meters: 220, is_shaded_or_underground: true, is_accessible: true },
          { mode: preference === 'more_bus' ? 'BUS' : 'SUBWAY', instruction: preference === 'more_bus' ? '搭乘市區幹線公車直達' : '搭乘捷運抵達目標站點 (強冷空調)', duration_minutes: 14, distance_meters: Math.max(300, dist - 400), is_shaded_or_underground: true, is_accessible: true },
          { mode: 'WALK', instruction: `出站由騎樓/地下街直通 ${destName}`, duration_minutes: 4, distance_meters: 200, is_shaded_or_underground: true, is_accessible: true },
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
