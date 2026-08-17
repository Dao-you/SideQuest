/**
 * Crowd Density & Heatmap Layer Service.
 */
import { apiClient } from './apiClient'

export class CrowdService {
  /**
   * Fetch heatmap points for Google Maps HeatmapLayer.
   * @returns {Promise<Array<{latitude: number, longitude: number, weight: number}>>}
   */
  async getHeatmapPoints() {
    try {
      return await apiClient.request('/crowd/heatmap')
    } catch (err) {
      console.warn('Heatmap API failed, using fallback:', err)
      return [
        { latitude: 25.0438, longitude: 121.5608, weight: 0.85 }, // Songshan Cultural Park
        { latitude: 25.0441, longitude: 121.5294, weight: 0.72 }, // Huashan 1914
        { latitude: 25.0330, longitude: 121.5654, weight: 0.90 }, // Taipei 101 / Xinyi
        { latitude: 25.0566, longitude: 121.5085, weight: 0.45 }, // Dadaocheng
        { latitude: 25.0527, longitude: 121.5203, weight: 0.38 }, // Zhongshan Linear Park
        { latitude: 25.0577, longitude: 121.6169, weight: 0.28 }, // Taipei Music Center
        { latitude: 25.0604, longitude: 121.4616, weight: 0.32 }, // New Taipei Art Museum
      ]
    }
  }

  /**
   * Fetch live crowd and wait times for major Taipei venues.
   */
  async getVenuesStatus() {
    try {
      return await apiClient.request('/crowd/venues')
    } catch (err) {
      console.warn('Venues API failed, using fallback:', err)
      return []
    }
  }
}

export const crowdService = new CrowdService()
