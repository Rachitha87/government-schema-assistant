/** Shows the agent-by-agent trace of the last request (RAG + LangGraph demo). */
export default function TracePanel({ trace = [], retrieval = [] }) {
  if (!trace.length && !retrieval.length) return null

  return (
    <details className="trace" style={{ marginTop: '0.75rem' }}>
      <summary>How this answer was produced (agent trace + retrieval scores)</summary>

      {trace.length > 0 && (
        <div style={{ marginTop: '0.6rem' }}>
          {trace.map((step, index) => (
            <div className="trace-step" key={`${step.agent}-${index}`}>
              <span className="trace-agent">{step.agent}</span>
              <span>{step.summary}</span>
            </div>
          ))}
        </div>
      )}

      {retrieval.length > 0 && (
        <div style={{ marginTop: '0.75rem' }}>
          <div className="meta-line" style={{ marginBottom: '0.3rem' }}>
            Top retrieved knowledge-base chunks:
          </div>
          {retrieval.slice(0, 6).map((item, index) => (
            <div className="trace-step" key={`${item.scheme_id}-${item.section}-${index}`}>
              <span className="trace-agent">
                {item.scheme_id} &middot; {item.section}
              </span>
              <span>
                {item.scheme_name} &mdash; score {Number(item.score).toFixed(3)} (bm25{' '}
                {Number(item.lexical_score).toFixed(2)} / semantic{' '}
                {Number(item.semantic_score).toFixed(2)})
              </span>
            </div>
          ))}
        </div>
      )}
    </details>
  )
}
