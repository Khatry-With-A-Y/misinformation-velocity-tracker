import { RefreshCw } from 'lucide-react'

import type { NewsStatus } from '../../lib/api'
import { Button } from '../ui/Button'
import { formatObservedDate } from './claimContext'

export function FreshnessStrip({
  status,
  error,
  refreshing,
  dashboardUpdatedAt,
  onRefresh,
}: {
  status: NewsStatus | null
  error: string | null
  refreshing: boolean
  dashboardUpdatedAt: string | null
  onRefresh: () => void
}) {
  const counters = status?.latest_run?.counters
  const state = error ? 'Status unavailable' : status?.state.replace('_', ' ') || 'Checking'
  return (
    <section
      aria-label="News freshness"
      className="flex flex-col gap-3 border-y border-border py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-semibold capitalize text-foreground">{state}</span>
        <span className="text-muted-foreground">
          Last successful poll: {formatObservedDate(status?.last_success_at)}
        </span>
        <span className="text-muted-foreground">
          Dashboard updated: {formatObservedDate(dashboardUpdatedAt)}
        </span>
        <span className="text-muted-foreground">
          {counters
            ? `${counters.promoted || 0} promoted, ${counters.duplicates || 0} duplicates`
            : 'No poll counters yet'}
        </span>
        {status && (status.staging.pending > 0 || status.staging.failed > 0) && (
          <span className="text-muted-foreground">
            Staging: {status.staging.pending} pending, {status.staging.failed} failed
          </span>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
        <RefreshCw className={refreshing ? 'animate-spin motion-reduce:animate-none' : ''} />
        Refresh
      </Button>
    </section>
  )
}
