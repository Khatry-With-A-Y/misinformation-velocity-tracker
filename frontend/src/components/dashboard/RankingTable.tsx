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
        <div className="flex flex-wrap items-center gap-2">
          <h2 id={`${title.replace(/\s/g, '-')}-title`} className="text-lg font-semibold tracking-tight">
            {title}
          </h2>
          <span
            className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
              ai
                ? 'border-amber-700/40 text-amber-700 dark:border-amber-300/40 dark:text-amber-300'
                : 'border-destructive/40 text-destructive'
            }`}
          >
            {ai ? 'AI signal' : 'Verified'}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {ai
            ? 'AI signal, not verified fact. Review confidence and rationale.'
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
                    className="grid w-full grid-cols-[1.75rem_1fr_auto] gap-3 px-5 py-3.5 text-left transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                  >
                    <span className="pt-0.5 text-sm font-semibold tabular-nums text-muted-foreground">
                      {index + 1}
                    </span>
                    <span className="min-w-0">
                      <span className="line-clamp-2 text-sm font-medium leading-snug text-foreground">
                        {item.canonical}
                      </span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {item.source || 'Unknown source'}
                        {item.evidence_title ? ` · ${item.evidence_title}` : ''}
                      </span>
                    </span>
                    <span className="text-right">
                      <span className="block text-sm font-semibold tabular-nums">
                        {item.current_count}
                      </span>
                      <span
                        className={`mt-1 flex items-center justify-end gap-1 text-xs tabular-nums ${
                          item.percent_change != null && item.percent_change > 0
                            ? 'text-destructive'
                            : 'text-muted-foreground'
                        }`}
                        title={changeLabel(item)}
                      >
                        <ChangeIcon className="h-3 w-3" aria-hidden="true" />
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
