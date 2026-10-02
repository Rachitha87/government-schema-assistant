import { Link } from 'react-router-dom'

import AskBox from '../components/AskBox.jsx'

/** Standalone question page (the same box that sits at the bottom of the home page). */
export default function Chat() {
  return (
    <main className="page">
      <div className="container narrow">
        <div className="page-head">
          <h1>Ask a question</h1>
          <p>
            Ask in your own words. We use the details you already saved in step 1, so you do not
            have to repeat them.
          </p>
        </div>

        <AskBox />

        <p className="fine-print">
          Looking for a full list instead? <Link to="/schemes">Browse all schemes</Link> or{' '}
          <Link to="/">start again</Link>.
        </p>
      </div>
    </main>
  )
}