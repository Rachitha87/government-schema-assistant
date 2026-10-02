import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <main className="page">
      <div className="container narrow center">
        <h1>Page not found</h1>
        <p className="muted">That link does not lead anywhere.</p>
        <Link className="btn btn-primary" to="/">
          Go to the home page
        </Link>
      </div>
    </main>
  )
}