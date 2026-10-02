import { Link } from 'react-router-dom'

/**
 * One scheme as a card.
 *
 * `verdict` adds the friendly "Can I apply?" banner that the recommendation
 * results use. `compact` is the small version shown inside chat answers.
 */

const VERDICT = {
  eligible: { label: 'You can apply', className: 'verdict-yes', mark: '✓' },
  insufficient: { label: 'Need a little more info', className: 'verdict-maybe', mark: '?' },
  not_eligible: { label: 'Not eligible', className: 'verdict-no', mark: '✕' },
}

export default function SchemeCard({
  scheme,
  verdict,
  note,
  highlights,
  dim,
  compact = false,
  footerExtra,
}) {
  if (!scheme) return null

  const verdictInfo = VERDICT[verdict]

  return (
    <article className={`scheme-card${dim ? ' dim' : ''}${compact ? ' compact' : ''}`}>
      {verdictInfo && (
        <div className={`verdict ${verdictInfo.className}`}>
          <span className="verdict-mark" aria-hidden="true">
            {verdictInfo.mark}
          </span>
          {verdictInfo.label}
        </div>
      )}

      <h3 className="scheme-name">
        <Link to={`/schemes/${scheme.scheme_id}`}>{scheme.name}</Link>
      </h3>
      <p className="scheme-provider">Run by {scheme.provider}</p>

      {note && (
        <p className="scheme-why">
          <strong>Why:</strong> {note}
        </p>
      )}

      {highlights?.length > 0 && (
        <div className="quick-row tight">
          {highlights.map((item) => (
            <span key={item} className="tick">
              ✓ {item}
            </span>
          ))}
        </div>
      )}

      {!compact && (
        <>
          <p className="scheme-desc">{scheme.description}</p>

          <dl className="scheme-facts">
            <div>
              <dt>Who can apply</dt>
              <dd>{scheme.eligibility}</dd>
            </div>
            <div>
              <dt>What you get</dt>
              <dd>{scheme.benefits}</dd>
            </div>
            <div>
              <dt>Income limit</dt>
              <dd>{scheme.income_limit}</dd>
            </div>
            <div>
              <dt>Last date</dt>
              <dd>{scheme.deadline}</dd>
            </div>
          </dl>
        </>
      )}

      <div className="scheme-foot">
        <span className="sample-tag">Sample data</span>
        {footerExtra}
        {scheme.application_link ? (
          <a
            href={scheme.application_link}
            target="_blank"
            rel="noreferrer noopener"
            className="btn btn-outline"
          >
            Apply on official site ↗
          </a>
        ) : (
          <span className="scheme-provider">No official link recorded</span>
        )}
      </div>
    </article>
  )
}