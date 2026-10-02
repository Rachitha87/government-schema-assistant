import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import api from '../api/client.js'
import { ErrorBanner, Loading } from '../components/Feedback.jsx'
import SchemeCard from '../components/SchemeCard.jsx'

/** Full details of one scheme. */
export default function SchemeDetail() {
  const { id } = useParams()
  const [scheme, setScheme] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api
      .getScheme(id)
      .then(setScheme)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <Loading label="Loading scheme…" />
  if (error) {
    return (
      <main className="page">
        <div className="container narrow">
          <ErrorBanner error={error} />
          <Link className="btn btn-outline" to="/schemes">
            ← Back to all schemes
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="page">
      <div className="container narrow">
        <Link className="btn btn-quiet back-link" to="/schemes">
          ← Back to all schemes
        </Link>
        <SchemeCard scheme={scheme} />

        <div className="panel">
          <h3>How to use this safely</h3>
          <p className="panel-hint">
            This record is sample data for a demonstration project. The official link is the real
            starting point — read the current notification there for the correct eligibility,
            benefit amount and last date before you apply.
          </p>
        </div>
      </div>
    </main>
  )
}