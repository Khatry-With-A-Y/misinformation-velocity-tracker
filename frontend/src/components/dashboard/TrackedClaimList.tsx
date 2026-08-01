import { ChevronLeft, ChevronRight } from 'lucide-react'

import type { ClaimContext } from '../../lib/api'
import { Button } from '../ui/Button'
import {
  formatObservedDate,
  provenanceLabel,
  recommendedAction,
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
      <ul className="max-h-[36rem] space-y-2 overflow-y-auto pr-1">
        {claims.map((claim) => {
          const trust = trustTreatment(claim.tier)
          return (
            <li key={claim.id}>
              <button
                type="button"
                onClick={() => onSelect(claim.id)}
                aria-pressed={claim.id === selectedId}
                className={`w-full rounded-md border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  claim.id === selectedId
                    ? 'border-primary bg-accent/60 ring-1 ring-primary/40'
                    : 'border-border hover:border-input hover:bg-accent/30'
                }`}
              >
                <span className="line-clamp-3 text-sm font-medium leading-snug text-foreground">
                  {claim.canonical}
                </span>
                <span className="mt-2.5 flex flex-wrap gap-1.5 text-xs">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${trust.className}`}>
                    {trust.label}
                  </span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
                    {claim.variant_count ?? 0} observed
                  </span>
                </span>
                <span className="mt-2.5 grid gap-x-3 gap-y-0.5 text-xs text-muted-foreground sm:grid-cols-2">
                  <span className="truncate">Origin: {provenanceLabel(claim.source)}</span>
                  <span className="truncate">Platform: {claim.top_platform || 'Unknown'}</span>
                  <span className="truncate">First seen: {formatObservedDate(claim.first_seen)}</span>
                  <span className="truncate">Last seen: {formatObservedDate(claim.last_seen)}</span>
                </span>
                <span className="mt-2 block text-xs font-medium text-primary">
                  Next: {recommendedAction(claim)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <div className="flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
        <span className="tabular-nums">
          Page {page} of {pageCount} · {total} tracked
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
