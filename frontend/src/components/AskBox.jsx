import { useEffect, useRef, useState } from 'react'

import api from '../api/client.js'
import { useProfile } from '../context/ProfileContext.jsx'
import { ErrorBanner, Spinner } from './Feedback.jsx'
import SchemeCard from './SchemeCard.jsx'
import TracePanel from './TracePanel.jsx'

/**
 * The question box. Used inline on the home page and on its own page.
 * Suggestions do double duty as examples of the plain wording that works.
 */

const SUGGESTIONS = [
  'Any scholarship for a girl studying engineering?',
  'I study MCA in Karnataka. What can I apply for?',
  'What is the last date to apply for Karnataka post matric?',
  'I have a disability. Which schemes support me?',
]

export default function AskBox({ compact = false }) {
  const { profilePayload } = useProfile()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  async function send(text) {
    const message = (text ?? input).trim()
    if (!message || busy) return

    setInput('')
    setError(null)
    setBusy(true)
    setMessages((current) => [...current, { role: 'user', content: message }])

    try {
      const history = messages
        .filter((item) => item.role === 'user' || item.role === 'assistant')
        .map(({ role, content }) => ({ role, content }))
      const data = await api.chat(message, profilePayload(), history, 4)
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: data.answer,
          schemes: data.matched_schemes,
          citations: data.citations,
          grounded: data.grounded,
          warnings: data.grounding_warnings,
          trace: data.trace,
          retrieval: data.retrieval_debug,
        },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`askbox${compact ? ' compact' : ''}`}>
      {error && <ErrorBanner error={error} />}

      <div className="ask-log" ref={logRef}>
        {messages.length === 0 && (
          <div className="ask-empty">
            <p className="ask-hint">
              Ask anything in your own words. The answer comes only from our scheme list — if we do
              not have a matching scheme, we will say so.
            </p>
            <div className="quick-row">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="quick-chip wide"
                  onClick={() => send(suggestion)}
                  disabled={busy}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) =>
          message.role === 'user' ? (
            <div className="bubble bubble-user" key={index}>
              {message.content}
            </div>
          ) : (
            <div className="answer" key={index}>
              <div className="bubble">{message.content}</div>

              {message.schemes?.length > 0 && (
                <div className="answer-cards">
                  {message.schemes.map((scheme) => (
                    <SchemeCard key={scheme.scheme_id} scheme={scheme} compact />
                  ))}
                </div>
              )}

              {message.citations?.length > 0 && (
                <p className="sources">From: {message.citations.join(' · ')}</p>
              )}

              {!message.grounded && (
                <p className="sources warn">{message.warnings.join(' ')}</p>
              )}

              <TracePanel trace={message.trace} retrieval={message.retrieval} />
            </div>
          ),
        )}

        {busy && (
          <div className="bubble muted-bubble">
            <Spinner dark /> Looking through the schemes…
          </div>
        )}
      </div>

      <form
        className="ask-input"
        onSubmit={(event) => {
          event.preventDefault()
          send()
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question here…"
          aria-label="Your question"
        />
        <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>
          Ask
        </button>
      </form>
    </div>
  )
}