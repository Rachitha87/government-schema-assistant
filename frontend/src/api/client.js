/**
 * Tiny API client.
 *
 * Every backend call in the app goes through this file, so the base URL is
 * configured in exactly one place.
 */

const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      /* response was not JSON - keep the default message */
    }
    throw new Error(detail)
  }

  return response.json()
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

export const api = {
  baseUrl: BASE_URL,

  getMeta: () => request('/meta'),

  getHealth: () => request('/health'),

  listSchemes: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== '' && value != null),
    ).toString()
    return request(`/schemes${query ? `?${query}` : ''}`)
  },

  getScheme: (schemeId) => request(`/schemes/${schemeId}`),

  getFilters: () => request('/schemes/filters'),

  recommend: (profile, topN = 6) =>
    request('/recommend', {
      method: 'POST',
      body: JSON.stringify({ profile, top_n: topN, include_near_misses: true }),
    }),

  chat: (message, profile, history = [], topN = 5) =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, profile, history, top_n: topN }),
    }),
}

export default api
