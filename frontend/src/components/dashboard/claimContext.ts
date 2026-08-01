import type { ClaimAnalytics, ClaimContext, ClaimTree, TreeNode } from '../../lib/api'

export type Trend = 'rising' | 'steady' | 'falling' | 'new' | 'unknown'

export function formatObservedDate(value?: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleString()
}

export function claimTrend(current?: number | null, previous?: number | null): Trend {
  if (current == null || previous == null) return 'unknown'
  if (current > 0 && previous === 0) return 'new'
  if (current > previous) return 'rising'
  if (current < previous) return 'falling'
  return 'steady'
}

export function trendLabel(trend: Trend): string {
  return {
    rising: 'Rising',
    steady: 'Steady',
    falling: 'Falling',
    new: 'New activity',
    unknown: 'Trend unknown',
  }[trend]
}

export function effectivePlatform(
  claim?: ClaimContext | null,
  analytics?: ClaimAnalytics | null
): string {
  return claim?.top_platform || analytics?.summary.top_platform || 'Unknown'
}

export function trustTreatment(tier?: ClaimContext['tier'] | null) {
  if (tier === 'VERIFIED_FALSE') {
    return {
      label: 'Verified false',
      description: 'Evidence-backed false claim',
      className: 'bg-destructive/10 text-destructive',
    }
  }
  if (tier === 'AI_FLAGGED') {
    return {
      label: 'AI flagged',
      description: 'Automated signal, not a verified fact-check',
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    }
  }
  return {
    label: 'Not yet verified',
    description: 'No evidence-backed verdict has been recorded',
    className: 'bg-muted text-muted-foreground',
  }
}

export function provenanceLabel(source?: string | null): string {
  return source?.trim() || 'Source unknown'
}

export function recommendedAction(claim?: ClaimContext | null): string {
  if (!claim) return 'Select a claim'
  if (claim.tier === 'VERIFIED_FALSE' || claim.tier === 'AI_FLAGGED') {
    return 'Review evidence'
  }
  if (claim.current_count > claim.previous_count) return 'Monitor spread'
  return 'Add evidence'
}

export function findRootNodes(tree?: ClaimTree | null): TreeNode[] {
  if (!tree?.nodes.length) return []
  const nodeIds = new Set(tree.nodes.map((node) => node.id))
  const children = new Set(
    tree.edges.filter((edge) => nodeIds.has(edge.source)).map((edge) => edge.target)
  )
  const roots = tree.nodes.filter((node) => !children.has(node.id))
  const candidates = roots.length ? roots : tree.nodes
  return [...candidates].sort((a, b) => {
    const aTime = a.ts ? Date.parse(a.ts) : Number.POSITIVE_INFINITY
    const bTime = b.ts ? Date.parse(b.ts) : Number.POSITIVE_INFINITY
    return aTime - bTime || a.id.localeCompare(b.id)
  })
}
