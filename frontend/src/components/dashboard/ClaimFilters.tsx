import { Search } from 'lucide-react'
import type { Period } from '../../lib/api'

const periods: Period[] = ['day', 'week', 'month', 'year']

export function ClaimFilters({
  search,
  onSearch,
  period,
  onPeriod,
}: {
  search: string
  onSearch: (value: string) => void
  period: Period
  onPeriod: (value: Period) => void
}) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <label className="relative block w-full md:max-w-md">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <span className="sr-only">Search claims</span>
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search claim text"
          className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </label>
      <div className="flex rounded-md border border-border bg-card p-1" aria-label="Ranking period">
        {periods.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onPeriod(option)}
            aria-pressed={period === option}
            className={`rounded px-3 py-1.5 text-xs font-medium capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              period === option
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            }`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}
