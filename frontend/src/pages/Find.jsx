import { useState } from 'react'
import { Link } from 'react-router-dom'

import api from '../api/client.js'
import { useProfile } from '../context/ProfileContext.jsx'
import ProfileForm from '../components/ProfileForm.jsx'
import AskBox from '../components/AskBox.jsx'
import SchemeCard from '../components/SchemeCard.jsx'
import { ErrorBanner, Loading } from '../components/Feedback.jsx'
import TracePanel from '../components/TracePanel.jsx'

/**
 * The whole app in one page:
 *   1. tell us about yourself
 *   2. see what you can apply for
 *   3. ask a follow-up question
 */

const STEPS = [
  { n: 1, label: 'Tell us about yourself', hint: '5 quick questions' },
  { n: 2, label: 'See what you can apply for', hint: 'With the reason for each' },
  { n: 3, label: 'Ask any follow-up question', hint: 'Answered from the same scheme list' },
]

function Results({ result }) {
  const groups = [
    {
      key: 'eligible',
      title: 'You can apply for these',
      empty: 'Nothing here yet.',
      items: result.eligible,
      verdict: 'eligible',
      tone: 'good',
    },
    {
      key: 'needs_more_info',
      title: 'Answer one more thing to check these',
      empty: '',
      items: result.needs_more_info,
      verdict: 'insufficient',
      tone: 'maybe',
    },
    {
      key: 'near_misses',
      title: 'You miss only one condition on these',
      empty: '',
      items: result.near_misses,
      verdict: 'not_eligible',
      tone: 'warn',
    },
  ].filter((group) => group.items.length > 0)

  return (
    <div className="results">
      <h2>
        Your results
        <span className="count-pill">{result.eligible.length} to apply for</span>
      </h2>

      {result.missing_profile_fields.length > 0 && (
        <div className="note note-maybe">
          <strong>For a complete answer we still need:</strong>{' '}
          {result.missing_profile_fields.join(', ')}. Fill those in above and press Show my schemes
          again.
        </div>
      )}

      {groups.length === 0 && (
        <div className="note">
          No scheme in our sample list matches yet. Try the search box under{' '}
          <Link to="/schemes">All schemes</Link>, or ask a question below.
        </div>
      )}

      {groups.map((group) => (
        <section key={group.key} className={`result-group ${group.tone}`}>
          <h3>
            {group.title} <span className="count-pill">{group.items.length}</span>
          </h3>
          <div className="cards">
            {group.items.map((item) => (
              <SchemeCard
                key={item.scheme.scheme_id}
                scheme={item.scheme}
                verdict={group.verdict}
                note={item.reason}
                highlights={item.match_highlights}
                dim={group.key !== 'eligible'}
              />
            ))}
          </div>
        </section>
      ))}

      <TracePanel trace={result.trace} />
    </div>
  )
}

export default function Find({ disclaimer }) {
  const { profilePayload } = useProfile()
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function runSearch() {
    setLoading(true)
    setError(null)
    try {
      // ProfileForm writes straight into the profile context, which persists to
      // localStorage - ask the context for its cleaned-up payload.
      const data = await api.recommend(profilePayload(), 8)
      setResult(data)
      if (window.innerWidth < 900) {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <section className="hero">
        <div className="container">
          <h1>Find the schemes you can apply for</h1>
          <p className="lead">
            Answer a few questions. We check every scheme in our list against your details and tell
            you exactly why you can or cannot apply.
          </p>
          <ol className="steps">
            {STEPS.map((step) => (
              <li key={step.n}>
                <span className="step-n">{step.n}</span>
                <span>
                  <strong>{step.label}</strong>
                  <em>{step.hint}</em>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <main className="page">
        <div className="container">
          <div className="note note-warn">
            <strong>Please note:</strong> this is a demo with sample scheme data. Always confirm on
            the official government website before you apply.
          </div>

          <section className="panel">
            <h2>
              <span className="step-n">1</span> Tell us about yourself
            </h2>
            <p className="panel-hint">
              Everything is optional — fill in what you know. The more you add, the more accurate the
              eligibility check.
            </p>
            <ProfileForm onSubmit={runSearch} submitting={loading} />
          </section>

          <section className="panel" id="results">
            <h2>
              <span className="step-n">2</span> What you can apply for
            </h2>

            {loading && <Loading label="Checking every scheme against your details…" />}

            {!loading && error && <ErrorBanner error={error} />}

            {!loading && !error && !result && (
              <p className="placeholder">
                Your results will appear here. Start with the questions above — age, state, category,
                family income and what you are studying matter the most.
              </p>
            )}

            {!loading && result && <Results result={result} />}
          </section>

          <section className="panel">
            <h2>
              <span className="step-n">3</span> Any other question?
            </h2>
            <p className="panel-hint">
              Ask about deadlines, documents or a specific scheme. Answers come only from our scheme
              list.
            </p>
            <AskBox compact />
          </section>

          {disclaimer && <p className="fine-print">{disclaimer}</p>}
        </div>
      </main>
    </>
  )
}