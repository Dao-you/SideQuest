/**
 * Weather, Microclimate, and Solar Comfort Service.
 */
import { apiClient } from './apiClient'

export class WeatherService {
  /**
   * Fetch live microclimate data for coordinates.
   * @param {number} lat
   * @param {number} lng
   */
  async getCurrentWeather(lat = 25.0330, lng = 121.5654) {
    try {
      const data = await apiClient.request(`/weather/current?lat=${lat}&lng=${lng}`)
      return {
        temperature: Math.round(data.temperature_c ?? 28),
        apparentTemperature: Math.round(data.apparent_temperature_c ?? 30),
        uvIndex: data.uv_index ?? 5,
        comfortLevel: data.comfort_level ?? 'MODERATE',
        description: data.weather_description ?? '晴朗舒適',
        isRainLikely: data.is_rain_likely ?? false,
        sunExposureLevel: data.sun_exposure_level ?? 'MODERATE',
        heatWarning: data.heat_warning ?? false,
        outdoorSuitability: data.outdoor_suitability ?? 75,
        advice: data.comfort_advice ?? '適合外出活動，注意防曬補水',
        isMock: false,
      }
    } catch (err) {
      console.warn('Weather API failed, using fallback:', err)
      return {
        temperature: 28,
        apparentTemperature: 30,
        uvIndex: 5,
        comfortLevel: 'MODERATE',
        description: '多雲舒適',
        isRainLikely: false,
        sunExposureLevel: 'MODERATE',
        heatWarning: false,
        outdoorSuitability: 80,
        advice: '天氣晴朗，適合探索城市展演與散步',
        isMock: true,
      }
    }
  }

  /**
   * Fetch solar exposure and shade analysis.
   */
  async getSolarExposure(lat = 25.0330, lng = 121.5654) {
    try {
      return await apiClient.request(`/weather/solar?lat=${lat}&lng=${lng}`)
    } catch (err) {
      console.warn('Solar API failed, using fallback:', err)
      return {
        solar_radiation_w_m2: 480.0,
        shade_recommendation: '建議配戴遮陽帽或善用捷運地下街連通道',
        uv_category: 'MODERATE',
      }
    }
  }
}

export const weatherService = new WeatherService()
