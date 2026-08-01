import type { ClaimAnalytics, ClaimContext, ClaimTree } from '../../lib/api'
import {
  claimTrend,
  effectivePlatform,
  findRootNodes,
  formatObservedDate,
  provenanceLabel,
  recommendedAction,
  trendLabel,
  trustTreatment,
} from './claimContext'

export function ClaimSummary({
  claim,
  analytics,
  tree,
}: {
  claim?: ClaimContext | null
  analytics: ClaimAnalytics
  tree?: ClaimTree | null
}) {
  const { summary } = analytics
  const trust = trustTreatment(claim?.tier)
  const roots = findRootNodes(tree)
  const root = roots[0]
  const trend = trendLabel(claimTrend(summary.current_count, summary.previous_count))
  const metrics = [
    ['Observed records', claim?.variant_count ?? summary.observed_variants],
    ['Current activity', summary.current_count],
    ['Previous activity', summary.previous_count],
    ['Trend', trend],
    ['Top platform', effectivePlatform(claim, analytics)],
    ['Next action', recommendedAction(claim)],
  ]
  return (
    <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">
          Investigation
        </p>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${trust.className}`}>
          {trust.label}
        </span>
      </div>
      <h2 className="mt-3 text-xl font-semibold leading-snug tracking-tight sm:text-2xl">
        {claim?.canonical || 'Selected claim'}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">{trust.description}.</p>
      <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border sm:grid-cols-3">
        {metrics.map(([label, value]) => (
          <div key={label} className="bg-card px-3.5 py-3">
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="mt-1 truncate text-base font-semibold tabular-nums" title={String(value)}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="mt-6 grid gap-5 text-sm sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Origin
          </p>
          <p className="mt-1.5 leading-relaxed text-foreground">
            {root ? root.text || root.label : 'Root variant not identified'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {provenanceLabel(root?.source || claim?.source)} ·{' '}
            {root?.platform || 'Platform unknown'} ·{' '}
            {formatObservedDate(root?.ts || claim?.first_seen || summary.first_seen)}
          </p>
          {roots.length > 1 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {roots.length} possible roots are present in this lineage.
            </p>
          )}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Evidence
          </p>
          <p className="mt-1.5 leading-relaxed text-foreground">
            {claim?.evidence_title || claim?.rationale || 'No evidence note recorded.'}
          </p>
          {claim?.evidence_url ? (
            <a
              href={claim.evidence_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Open supporting evidence
            </a>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">Evidence link not recorded.</p>
          )}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1 border-t border-border pt-4 text-xs text-muted-foreground">
        <p>First seen: {formatObservedDate(claim?.first_seen || summary.first_seen)}</p>
        <p>Last seen: {formatObservedDate(claim?.last_seen || summary.last_seen)}</p>
      </div>
    </section>
  )
}
