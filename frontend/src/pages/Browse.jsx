import { useEffect, useState } from 'react'

import api from '../api/client.js'
import { EmptyState, ErrorBanner, Loading } from '../components/Feedback.jsx'
import SchemeCard from '../components/SchemeCard.jsx'

/** Search and filter the full scheme list. */
export default function Browse() {
  const [options, setOptions] = useState({})
  const [filters, setFilters] = useState({ state: '', category: '', education_level: '' })
  const [query, setQuery] = useState('')
  const [schemes, setSchemes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getFilters().then(setOptions).catch(() => setOptions({}))
  }, [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    api
      .listSchemes({ ...filters, q: query })
      .then((data) => active && setSchemes(data.schemes))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [query, filters.state, filters.category, filters.education_level])

  function onSelect(key, value) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <main className="page">
      <div className="container">
        <div className="page-head">
          <h1>All schemes</h1>
          <p>Search the complete list, or filter by your state and background.</p>
        </div>

        <div className="panel">
          <label className="field">
            <span className="field-label">Search</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. girl, engineering, Karnataka, scholarship"
            />
          </label>

          <div className="profile-grid">
            <label className="field">
              <span className="field-label">State</span>
              <select
                value={filters.state}
                onChange={(e) => onSelect('state', e.target.value)}
              >
                <option value="">Any state</option>
                {(options.states || []).map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field-label">Category</span>
              <select
                value={filters.category}
                onChange={(e) => onSelect('category', e.target.value)}
              >
                <option value="">Any category</option>
                {(options.categories || []).map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field-label">Studying level</span>
              <select
                value={filters.education_level}
                onChange={(e) => onSelect('education_level', e.target.value)}
              >
                <option value="">Any level</option>
                {(options.education_levels || []).map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {error && <ErrorBanner error={error} />}
        {loading && <Loading label="Loading schemes…" />}

        {!loading && !error && schemes.length === 0 && (
          <EmptyState
            title="No schemes matched"
            hint="Try a shorter search word, or clear one of the filters."
          />
        )}

        {!loading && schemes.length > 0 && (
          <p className="result-count">
            Showing {schemes.length} scheme{schemes.length === 1 ? '' : 's'}
          </p>
        )}

        {!loading && schemes.length > 0 && (
          <div className="cards">
            {schemes.map((scheme) => (
              <SchemeCard key={scheme.scheme_id} scheme={scheme} />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}