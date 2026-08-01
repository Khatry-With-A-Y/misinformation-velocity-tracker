import { ChevronLeft, ChevronRight } from 'lucide-react'

import type { ClaimContext } from '../../lib/api'
import { Button } from '../ui/Button'
import {
  claimTrend,
  formatObservedDate,
  provenanceLabel,
  recommendedAction,
  trendLabel,
  trustTreatment,
} from './claimContext'

interface TrackedClaimListProps {
  claims: ClaimContext[]
  selectedId: string | null
  page: number
  pageSize: number
  total: number
  onSelect: (id: string) => void
  onPage: (page: number) => void
}

export function TrackedClaimList({
  claims,
  selectedId,
  page,
  pageSize,
  total,
  onSelect,
  onPage,
}: TrackedClaimListProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="space-y-4">
      <ul className="space-y-2">
        {claims.map((claim) => {
          const trust = trustTreatment(claim.tier)
          const trend = trendLabel(claimTrend(claim.current_count, claim.previous_count))
          return (
            <li key={claim.id}>
              <button
                type="button"
                onClick={() => onSelect(claim.id)}
                className={`w-full rounded-md border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  claim.id === selectedId
                    ? 'border-primary bg-accent/40'
                    : 'border-border hover:bg-accent/20'
                }`}
              >
                <span className="line-clamp-3 text-sm font-medium text-foreground">
                  {claim.canonical}
                </span>
                <span className="mt-2 flex flex-wrap gap-1.5 text-xs">
                  <span className={`rounded px-1.5 py-0.5 font-medium ${trust.className}`}>
                    {trust.label}
                  </span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">
                    {claim.variant_count ?? 0} observed
                  </span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">
                    {trend}
                  </span>
                </span>
                <span className="mt-2 grid gap-1 text-xs text-muted-foreground">
                  <span>Origin: {provenanceLabel(claim.source)}</span>
                  <span>Platform: {claim.top_platform || 'Unknown'}</span>
                  <span>First seen: {formatObservedDate(claim.first_seen)}</span>
                  <span>Last seen: {formatObservedDate(claim.last_seen)}</span>
                  <span className="font-medium text-foreground">
                    Next: {recommendedAction(claim)}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <div className="flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
        <span>
          Page {page} of {pageCount}, {total} tracked
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPage(page - 1)}
            disabled={page <= 1}
            aria-label="Previous claims page"
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPage(page + 1)}
            disabled={page >= pageCount}
            aria-label="Next claims page"
          >
            <ChevronRight />
          </Button>
        </div>
      </div>
    </div>
  )
}
