/** Footer. The technical status lives here so it stays out of the user's way. */
export default function Footer({ meta }) {
  const llmOn = meta?.llm?.llm_enabled

  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div>
          <strong>{meta?.app || 'Government Scheme Assistant'}</strong>
          <p className="fine-print">
            A demonstration project. Scheme details are sample data — always confirm on the
            official government portal before you apply.
          </p>
        </div>
        <div className="fine-print">
          {meta?.knowledge_base?.schemes || 0} sample schemes
          {llmOn ? (
            <> &middot; answers written by {meta.llm.provider}</>
          ) : (
            <> &middot; answers written directly from the scheme list</>
          )}
          {meta?.agents?.runtime ? <> &middot; {meta.agents.runtime}</> : null}
        </div>
      </div>
    </footer>
  )
}