import { useCallback, useEffect, useRef, useState } from 'react'
import 'reactflow/dist/style.css'
import { AlertTriangle, Send } from 'lucide-react'

import { BreakdownPanels } from '../components/dashboard/BreakdownPanels'
import { ClaimSummary } from '../components/dashboard/ClaimSummary'
import { ClaimFilters } from '../components/dashboard/ClaimFilters'
import { DashboardNav } from '../components/dashboard/DashboardNav'
import { FreshnessStrip } from '../components/dashboard/FreshnessStrip'
import { RankingTable } from '../components/dashboard/RankingTable'
import { MutationExplorer } from '../components/dashboard/MutationExplorer'
import { SpreadTimeline } from '../components/dashboard/SpreadTimeline'
import { TrackedClaimList } from '../components/dashboard/TrackedClaimList'

import { Button } from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { useAppDispatch, showNotification } from '../context/AppContext'
import {
  getClaimAnalytics,
  getNewsStatus,
  getRankings,
  getTree,
  ingestClaim,
  listClaims,
  type ClaimAnalytics,
  type ClaimContext,
  type DashboardView,
  type Period,
  type RankingItem,
  type ClaimTree,
  type NewsStatus,
} from '../lib/api'

const CLAIM_PAGE_SIZE = 25

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted-foreground">
      <AlertTriangle className="h-6 w-6 text-destructive" />
      <p>{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-10 text-center text-muted-foreground">
      {message}
    </div>
  )
}

export default function Dashboard() {
  const dispatch = useAppDispatch()

  const [text, setText] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [view, setView] = useState<DashboardView>('overview')
  const [period, setPeriod] = useState<Period>('week')
  const [search, setSearch] = useState('')

  const [claims, setClaims] = useState<ClaimContext[]>([])
  const [claimsTotal, setClaimsTotal] = useState(0)
  const [claimsPage, setClaimsPage] = useState(1)
  const [claimsError, setClaimsError] = useState<string | null>(null)
  const [claimsLoading, setClaimsLoading] = useState(false)
  const [verifiedRankings, setVerifiedRankings] = useState<RankingItem[]>([])
  const [aiRankings, setAiRankings] = useState<RankingItem[]>([])
  const [rankingsLoading, setRankingsLoading] = useState(false)
  const [verifiedError, setVerifiedError] = useState<string | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [newsStatus, setNewsStatus] = useState<NewsStatus | null>(null)
  const [newsStatusError, setNewsStatusError] = useState<string | null>(null)
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [tree, setTree] = useState<ClaimTree | null>(null)
  const [analytics, setAnalytics] = useState<ClaimAnalytics | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailWarning, setDetailWarning] = useState<string | null>(null)
  const detailAvailable = useRef(false)
  detailAvailable.current = Boolean(tree || analytics)

  const refreshClaims = useCallback(async () => {
    setClaimsLoading(true)
    setClaimsError(null)
    try {
      const data = await listClaims({
        page: claimsPage,
        limit: CLAIM_PAGE_SIZE,
        query: search || undefined,
        tier: view === 'verified' ? 'verified_false' : undefined,
        platform: view === 'live' ? 'news' : undefined,
        period,
      })
      const items = Array.isArray(data) ? data : data.items
      setClaims(items)
      setClaimsTotal(Array.isArray(data) ? items.length : data.total)
    } catch (error) {
      setClaimsError(error instanceof Error ? error.message : 'Unable to load claims')
    } finally {
      setClaimsLoading(false)
    }
  }, [claimsPage, period, search, view])

  useEffect(() => {
    setClaimsPage(1)
  }, [period, search, view])

  const refreshNewsStatus = useCallback(async () => {
    setNewsStatusError(null)
    try {
      setNewsStatus(await getNewsStatus())
    } catch (error) {
      setNewsStatusError(error instanceof Error ? error.message : 'Freshness unavailable')
    }
  }, [])

  const refreshRankings = useCallback(async () => {
    setRankingsLoading(true)
    setVerifiedError(null)
    setAiError(null)
    const [verified, ai] = await Promise.allSettled([
      getRankings(period, 'verified_false'),
      getRankings(period, 'ai_flagged'),
    ])
    if (verified.status === 'fulfilled') setVerifiedRankings(verified.value)
    else setVerifiedError('Verified rankings are temporarily unavailable.')
    if (ai.status === 'fulfilled') setAiRankings(ai.value)
    else setAiError('Realtime AI rankings are temporarily unavailable.')
    setRankingsLoading(false)
  }, [period])

  const refreshDetail = useCallback(async () => {
    if (!selectedId) {
      setTree(null)
      setAnalytics(null)
      setDetailError(null)
      setDetailWarning(null)
      return
    }
    setDetailLoading(true)
    setDetailError(null)
    setDetailWarning(null)
    const [treeResult, analyticsResult] = await Promise.allSettled([
      getTree(selectedId),
      getClaimAnalytics(selectedId, period),
    ])
    if (treeResult.status === 'fulfilled') setTree(treeResult.value)
    if (analyticsResult.status === 'fulfilled') setAnalytics(analyticsResult.value)
    if (treeResult.status === 'rejected' || analyticsResult.status === 'rejected') {
      const message =
        treeResult.status === 'rejected' && analyticsResult.status === 'rejected'
          ? 'Investigation refresh failed. Showing the last successful detail when available.'
          : 'Part of this investigation could not refresh. Available detail remains visible.'
      if (detailAvailable.current) setDetailWarning(message)
      else if (treeResult.status === 'rejected' && analyticsResult.status === 'rejected') {
        setDetailError(message)
      } else setDetailWarning(message)
    }
    setDetailLoading(false)
  }, [period, selectedId])

  const refreshCallbacks = useRef({
    claims: refreshClaims,
    rankings: refreshRankings,
    status: refreshNewsStatus,
    detail: refreshDetail,
  })
  refreshCallbacks.current = {
    claims: refreshClaims,
    rankings: refreshRankings,
    status: refreshNewsStatus,
    detail: refreshDetail,
  }
  const refreshInFlight = useRef(false)
  const refreshQueued = useRef(false)

  const runRefreshCycle = useCallback((manual = false) => {
    if (manual) setManualRefreshing(true)
    if (refreshInFlight.current) {
      refreshQueued.current = true
      return
    }
    refreshInFlight.current = true
    void (async () => {
      do {
        refreshQueued.current = false
        const current = refreshCallbacks.current
        await Promise.allSettled([
          current.claims(),
          current.rankings(),
          current.status(),
          current.detail(),
        ])
        setLastUpdated(new Date().toISOString())
      } while (refreshQueued.current)
    })().finally(() => {
      refreshInFlight.current = false
      setManualRefreshing(false)
    })
  }, [])

  useEffect(() => {
    runRefreshCycle()
  }, [refreshClaims, refreshDetail, refreshNewsStatus, refreshRankings, runRefreshCycle])

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') runRefreshCycle()
    }
    const timer = window.setInterval(refreshWhenVisible, 60_000)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [runRefreshCycle])

  const handleAnalyze = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed) {
      showNotification(dispatch, 'Paste a claim to analyze first.', 'info')
      return
    }
    setAnalyzing(true)
    try {
      const claim = await ingestClaim(trimmed)
      showNotification(dispatch, 'Claim submitted for analysis.', 'success')
      setText('')
      if (claim && claim.id) {
        setSelectedId(claim.id)
      }
    } catch (error) {
      showNotification(
        dispatch,
        error instanceof Error ? error.message : 'Analysis failed — please try again.',
        'error'
      )
    } finally {
      setAnalyzing(false)
    }
  }, [text, dispatch])

  const handleRefresh = useCallback(() => {
    runRefreshCycle(true)
  }, [runRefreshCycle])

  const rankingClaim = [...verifiedRankings, ...aiRankings].find((item) => item.id === selectedId)
  const selectedClaim: ClaimContext | null =
    claims.find((c) => c.id === selectedId) ||
    (rankingClaim
      ? {
          id: rankingClaim.id,
          canonical: rankingClaim.canonical,
          domain: rankingClaim.domain,
          language: rankingClaim.language,
          source: rankingClaim.source,
          verdict: rankingClaim.verdict,
          rationale: rankingClaim.rationale,
          tier: rankingClaim.tier,
          confidence: rankingClaim.confidence,
          assessed_at: rankingClaim.assessed_at,
          evidence_url: rankingClaim.evidence_url,
          evidence_title: rankingClaim.evidence_title,
          variant_count: rankingClaim.current_count + rankingClaim.previous_count,
          first_seen: rankingClaim.first_seen,
          last_seen: rankingClaim.last_seen,
          current_count: rankingClaim.current_count,
          previous_count: rankingClaim.previous_count,
          top_platform: null,
        }
      : null)

  return (
    <div className="space-y-7">
      <div className="max-w-3xl">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">
          Evidence and monitoring
        </p>
        <h1 className="text-3xl font-bold text-foreground">Misinformation intelligence</h1>
        <p className="mt-2 text-base text-muted-foreground">
          Compare evidence-backed false claims with clearly labeled realtime AI signals.
        </p>
      </div>

      <DashboardNav value={view} onChange={setView} />
      <FreshnessStrip
        status={newsStatus}
        error={newsStatusError}
        refreshing={manualRefreshing}
        dashboardUpdatedAt={lastUpdated}
        onRefresh={handleRefresh}
      />
      <ClaimFilters search={search} onSearch={setSearch} period={period} onPeriod={setPeriod} />

      <Card>
        <CardHeader>
          <CardTitle>Analyze a claim</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste a claim in Nepali or English…"
            rows={4}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
            disabled={analyzing}
          />
          <div className="flex justify-end">
            <Button onClick={handleAnalyze} disabled={analyzing}>
              {analyzing ? <Spinner size="sm" className="text-primary-foreground" /> : <Send />}
              {analyzing ? 'Analyzing…' : 'Analyze'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className={`grid gap-6 ${view === 'overview' ? 'xl:grid-cols-2' : 'grid-cols-1'}`}>
        {view !== 'live' && (
          <RankingTable
            title="Verified false claims"
            items={verifiedRankings}
            loading={rankingsLoading}
            error={verifiedError}
            onSelect={setSelectedId}
          />
        )}
        {view !== 'verified' && (
          <RankingTable
            title="Realtime AI flags"
            items={aiRankings}
            loading={rankingsLoading}
            error={aiError}
            onSelect={setSelectedId}
            ai
          />
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>
              {view === 'verified'
                ? 'Verified corpus'
                : view === 'live'
                  ? 'Monitored claims'
                  : 'All claims'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {claimsLoading && claims.length === 0 ? (
              <div className="space-y-3 py-2" aria-label="Loading tracked claims">
                {[1, 2, 3].map((item) => (
                  <div
                    key={item}
                    className="h-28 animate-pulse rounded-md bg-muted motion-reduce:animate-none"
                  />
                ))}
              </div>
            ) : claims.length === 0 && claimsError ? (
              <ErrorState message={claimsError} />
            ) : claims.length === 0 ? (
              <EmptyState message="No claims match this view and search." />
            ) : (
              <>
                {claimsError && (
                  <p className="mb-3 text-xs text-destructive">
                    Refresh failed. Showing the last successful claim list.
                  </p>
                )}
                <TrackedClaimList
                  claims={claims}
                  selectedId={selectedId}
                  page={claimsPage}
                  pageSize={CLAIM_PAGE_SIZE}
                  total={claimsTotal}
                  onSelect={setSelectedId}
                  onPage={setClaimsPage}
                />
              </>
            )}
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          {!selectedId ? (
            <Card>
              <CardContent>
                <EmptyState message="Select a claim to see its mutation tree, velocity, and platform breakdown." />
              </CardContent>
            </Card>
          ) : detailLoading && !tree && !analytics ? (
            <Card>
              <CardContent>
                <div className="space-y-4 py-8" aria-label="Loading investigation">
                  <div className="h-8 w-2/3 animate-pulse rounded bg-muted motion-reduce:animate-none" />
                  <div className="h-28 animate-pulse rounded bg-muted motion-reduce:animate-none" />
                  <div className="h-64 animate-pulse rounded bg-muted motion-reduce:animate-none" />
                </div>
              </CardContent>
            </Card>
          ) : detailError ? (
            <Card>
              <CardContent>
                <ErrorState message={detailError} />
              </CardContent>
            </Card>
          ) : (
            <>
              {detailWarning && (
                <p className="rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
                  {detailWarning}
                </p>
              )}
              {analytics ? (
                <>
                  <ClaimSummary claim={selectedClaim} analytics={analytics} tree={tree} />
                  <SpreadTimeline data={analytics.timeline} />
                  <BreakdownPanels
                    platforms={analytics.platforms}
                    languages={analytics.languages}
                    mutations={analytics.mutations}
                  />
                </>
              ) : (
                <Card>
                  <CardContent>
                    <ErrorState message="Summary analytics are unavailable, but mutation data may still be shown." />
                  </CardContent>
                </Card>
              )}
              <MutationExplorer tree={tree || { nodes: [], edges: [] }} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
