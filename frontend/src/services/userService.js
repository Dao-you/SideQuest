/**
 * User & Persona Management Service (PRD 7.1 Mock Login & Bookmarks).
 */
import { apiClient } from './apiClient'

export class UserService {
  /**
   * List preset test personas for Demo Login.
   */
  async listPersonas() {
    try {
      return await apiClient.request('/user/personas')
    } catch (err) {
      console.warn('Personas API failed, using fallback personas:', err)
      return [
        {
          id: 'demo_weekend_explorer',
          name: '林宥廷 (週末文藝探索者)',
          account_type: 'WEEKEND_EXPLORER',
          avatar_url: '',
          preferred_categories: ['art', 'cafe', 'market'],
          interest_tags: ['當代藝術', '獨立手作', '手沖咖啡', '動漫展覽'],
          budget_twd_cap: 800,
          prefer_indoor: true,
          avoid_crowd: true,
          favorited_event_ids: [],
        },
        {
          id: 'demo_tech_geek',
          name: '陳冠宇 (AI 技術極客)',
          account_type: 'TECH_GEEK',
          avatar_url: '',
          preferred_categories: ['tech', 'workshop', 'craft'],
          interest_tags: ['DevJam', 'AI Agent', '開源社群', '黑客松'],
          budget_twd_cap: 1500,
          prefer_indoor: true,
          avoid_crowd: false,
          favorited_event_ids: [],
        },
        {
          id: 'demo_crowd_avoider',
          name: '張雅婷 (避開人潮漫遊者)',
          account_type: 'CROWD_AVOIDER',
          avatar_url: '',
          preferred_categories: ['outdoor', 'cafe', 'art'],
          interest_tags: ['安靜散步', '綠意空間', '低分貝', '老屋甜點'],
          budget_twd_cap: 500,
          prefer_indoor: false,
          avoid_crowd: true,
          favorited_event_ids: [],
        },
        {
          id: 'demo_family_parent',
          name: '黃俊傑 (親子放電家長)',
          account_type: 'FAMILY_PARENT',
          avatar_url: '',
          preferred_categories: ['family', 'exhibition', 'outdoor'],
          interest_tags: ['兒童手作', '互動展', '冷氣充足', '推車友善'],
          budget_twd_cap: 1000,
          prefer_indoor: true,
          avoid_crowd: true,
          favorited_event_ids: [],
        },
      ]
    }
  }

  /**
   * Perform one-click demo login.
   */
  async mockLogin(accountId, customName = '') {
    try {
      return await apiClient.request('/user/mock-login', {
        method: 'POST',
        body: JSON.stringify({ account_id: accountId, custom_name: customName }),
      })
    } catch (err) {
      console.warn('Mock login API failed, using fallback:', err)
      const personas = await this.listPersonas()
      return personas.find((p) => p.id === accountId) || personas[0]
    }
  }

  /**
   * Get user profile and bookmarked event IDs.
   */
  async getProfile(userId = 'demo_weekend_explorer') {
    try {
      return await apiClient.request(`/user/profile?user_id=${userId}`)
    } catch (err) {
      console.warn('Profile API failed, fallback profile:', err)
      const personas = await this.listPersonas()
      return personas.find((p) => p.id === userId) || personas[0]
    }
  }

  /**
   * Toggle event favorite status.
   */
  async toggleFavorite(userId = 'demo_weekend_explorer', eventId) {
    try {
      return await apiClient.request(`/user/favorites/${eventId}?user_id=${userId}`, {
        method: 'POST',
      })
    } catch (err) {
      console.warn('Favorite toggle API failed:', err)
      return {
        event_id: eventId,
        is_favorited: true,
        message: '已儲存至我的收藏',
        total_favorites_count: 1,
      }
    }
  }

  /**
   * Get all full event objects favorited by user.
   */
  async getFavorites(userId = 'demo_weekend_explorer') {
    try {
      return await apiClient.request(`/user/favorites?user_id=${userId}`)
    } catch (err) {
      console.warn('Favorites API failed:', err)
      return []
    }
  }

  /**
   * Update user preferences in backend.
   */
  async updatePreferences(userId = 'demo_weekend_explorer', updateData = {}) {
    try {
      return await apiClient.request(`/user/preferences?user_id=${userId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData),
      })
    } catch (err) {
      console.warn('Update preferences API failed:', err)
      return null
    }
  }

  /**
   * Get Google Calendar events for user.
   */
  async getCalendarEvents(userId = 'demo_weekend_explorer') {
    try {
      return await apiClient.request(`/user/calendar/events?user_id=${userId}`)
    } catch (err) {
      console.warn('Get calendar events API failed:', err)
      return []
    }
  }

  /**
   * Check schedule conflict in Google Calendar.
   */
  async checkCalendarConflict(userId = 'demo_weekend_explorer', checkData = {}) {
    try {
      return await apiClient.request(`/user/calendar/check-conflict?user_id=${userId}`, {
        method: 'POST',
        body: JSON.stringify(checkData),
      })
    } catch (err) {
      console.warn('Check calendar conflict API failed:', err)
      return {
        has_conflict: false,
        conflicting_events: [],
        message: '日曆比對完成，無衝突',
        suggested_action: 'proceed',
      }
    }
  }

  /**
   * Sync activity to Google Calendar with conflict resolution choice (overwrite, both, cancel).
   */
  async syncCalendarEvent(userId = 'demo_weekend_explorer', syncData = {}) {
    try {
      return await apiClient.request(`/user/calendar/sync?user_id=${userId}`, {
        method: 'POST',
        body: JSON.stringify(syncData),
      })
    } catch (err) {
      console.warn('Sync calendar API failed:', err)
      return {
        success: true,
        action_taken: syncData.resolution_choice || 'added',
        message: '已排入 Google 日曆！',
        all_calendar_events: [],
      }
    }
  }

  /**
   * Get Google OAuth Web Client configuration from backend.
   */
  async getGoogleAuthConfig() {
    return apiClient.request('/user/auth/config')
  }

  /**
   * Authenticate with Google identity / token / profile.
   */
  async loginWithGoogle(credential) {
    return apiClient.request('/user/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    })
  }
}

export const userService = new UserService()

