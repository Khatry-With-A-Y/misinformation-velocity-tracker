import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import type { RankingItem } from '../../lib/api'

function changeLabel(item: RankingItem) {
  if (item.percent_change == null) return 'New in this period'
  if (item.percent_change === 0) return 'No change'
  return `${Math.abs(item.percent_change)}% ${item.percent_change > 0 ? 'increase' : 'decrease'}`
}

export function RankingTable({
  title,
  items,
  loading,
  error,
  onSelect,
  ai = false,
}: {
  title: string
  items: RankingItem[]
  loading: boolean
  error?: string | null
  onSelect: (id: string) => void
  ai?: boolean
}) {
  return (
    <section
      aria-labelledby={`${title.replace(/\s/g, '-')}-title`}
      className="overflow-hidden rounded-lg border border-border bg-card"
    >
      <div className="border-b border-border px-5 py-4">
        <h2 id={`${title.replace(/\s/g, '-')}-title`} className="text-lg font-semibold">
          {title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {ai
            ? 'Automated signals, not verified facts. Review confidence and rationale.'
            : 'Evidence-backed false claims ranked by observed variants in this window.'}
        </p>
      </div>
      {loading && items.length === 0 ? (
        <div className="space-y-3 p-5" aria-label="Loading rankings">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-14 animate-pulse rounded bg-muted motion-reduce:animate-none"
            />
          ))}
        </div>
      ) : error && items.length === 0 ? (
        <p className="p-5 text-sm text-destructive">{error}</p>
      ) : items.length === 0 ? (
        <p className="p-5 text-sm text-muted-foreground">
          No observed activity qualifies for this period.
        </p>
      ) : (
        <>
          {error && (
            <p className="border-b border-border px-5 py-3 text-sm text-destructive">
              Refresh failed. Showing the last successful ranking.
            </p>
          )}
          <ol className="divide-y divide-border">
            {items.map((item, index) => {
              const ChangeIcon =
                item.percent_change == null || item.percent_change === 0
                  ? Minus
                  : item.percent_change > 0
                    ? ArrowUp
                    : ArrowDown
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id)}
                    className="grid w-full grid-cols-[2rem_1fr_auto] gap-3 px-5 py-4 text-left hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                  >
                    <span className="pt-0.5 text-sm font-semibold text-muted-foreground">
                      {index + 1}
                    </span>
                    <span className="min-w-0">
                      <span className="line-clamp-2 text-sm font-medium text-foreground">
                        {item.canonical}
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {item.source || 'Unknown source'}
                        {item.evidence_title ? ` · ${item.evidence_title}` : ''}
                      </span>
                    </span>
                    <span className="text-right">
                      <span className="block text-sm font-semibold">{item.current_count}</span>
                      <span
                        className="mt-1 flex items-center justify-end gap-1 text-xs text-muted-foreground"
                        title={changeLabel(item)}
                      >
                        <ChangeIcon className="h-3 w-3" />
                        {item.percent_change == null ? 'new' : `${item.percent_change}%`}
                      </span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        </>
      )}
    </section>
  )
}
