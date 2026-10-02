export function Spinner({ dark = false }) {
  return <span className={`spinner${dark ? ' dark' : ''}`} aria-hidden="true" />
}

export function Loading({ label = 'Loading…' }) {
  return (
    <p className="loading-line">
      <Spinner dark /> {label}
    </p>
  )
}

export function ErrorBanner({ error }) {
  if (!error) return null
  return (
    <div className="note note-bad">
      <strong>Something went wrong.</strong> {String(error)}
    </div>
  )
}

export function EmptyState({ title, hint }) {
  return (
    <div className="placeholder">
      <strong>{title}</strong>
      {hint && <p>{hint}</p>}
    </div>
  )
}