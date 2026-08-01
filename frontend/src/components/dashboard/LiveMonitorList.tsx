import type { Claim } from '../../lib/api'

export function LiveMonitorList({
  claims,
  onSelect,
}: {
  claims: Claim[]
  onSelect: (id: string) => void
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-lg font-semibold">Recently monitored news</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Headlines promoted from RSS after claim extraction. Unverified unless marked as an AI flag.
      </p>
      {claims.length === 0 ? (
        <p className="mt-5 text-sm text-muted-foreground">No matching monitored claims.</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {claims.slice(0, 12).map((claim) => (
            <li key={claim.id}>
              <button
                type="button"
                onClick={() => onSelect(claim.id)}
                className="w-full py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="line-clamp-2 text-sm font-medium">{claim.canonical}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {claim.source || 'RSS source'} · {claim.domain || 'other'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
