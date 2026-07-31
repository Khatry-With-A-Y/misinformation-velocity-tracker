import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, Send } from 'lucide-react'

import { Button } from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { useAppDispatch, showNotification } from '../context/AppContext'
import {
  getPlatforms,
  getTree,
  getVelocity,
  ingestClaim,
  listClaims,
  type Claim,
  type ClaimTree,
  type PlatformCount,
  type VelocityPoint,
} from '../lib/api'

function toFlow(tree: ClaimTree): { nodes: Node[]; edges: Edge[] } {
  // Simple top-down layout: order nodes by timestamp and stack them by depth.
  const ordered = [...tree.nodes].sort((a, b) => (a.ts || '').localeCompare(b.ts || ''))
  const nodes: Node[] = ordered.map((n, index) => ({
    id: n.id,
    position: { x: (index % 3) * 260, y: index * 120 },
    data: {
      label: `${n.label}\n${n.platform || 'unknown platform'} · ${n.mutation_type || 'unknown mutation'}`,
    },
    style: {
      whiteSpace: 'pre-wrap',
      fontSize: 12,
      width: 220,
      borderRadius: 8,
    },
  }))

  const edges: Edge[] = tree.edges.map((e, index) => ({
    id: `${e.source}-${e.target}-${index}`,
    source: e.source,
    target: e.target,
  }))

  return { nodes, edges }
}

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

  const [claims, setClaims] = useState<Claim[]>([])
  const [claimsError, setClaimsError] = useState<string | null>(null)
  const [claimsLoading, setClaimsLoading] = useState(false)

  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [tree, setTree] = useState<ClaimTree | null>(null)
  const [velocity, setVelocity] = useState<VelocityPoint[]>([])
  const [platforms, setPlatforms] = useState<PlatformCount[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  const refreshClaims = useCallback(async () => {
    setClaimsLoading(true)
    setClaimsError(null)
    try {
      const data = await listClaims()
      setClaims(Array.isArray(data) ? data : [])
    } catch (error) {
      setClaims([])
      setClaimsError(error instanceof Error ? error.message : 'Unable to load claims')
    } finally {
      setClaimsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshClaims()
  }, [refreshClaims])

  useEffect(() => {
    if (!selectedId) {
      setTree(null)
      setVelocity([])
      setPlatforms([])
      setDetailError(null)
      return
    }

    let cancelled = false
    setDetailLoading(true)
    setDetailError(null)

    Promise.allSettled([
      getTree(selectedId),
      getVelocity(selectedId),
      getPlatforms(selectedId),
    ])
      .then(([treeRes, velocityRes, platformsRes]) => {
        if (cancelled) return
        setTree(treeRes.status === 'fulfilled' ? treeRes.value : { nodes: [], edges: [] })
        setVelocity(
          velocityRes.status === 'fulfilled' && Array.isArray(velocityRes.value)
            ? velocityRes.value
            : []
        )
        setPlatforms(
          platformsRes.status === 'fulfilled' && Array.isArray(platformsRes.value)
            ? platformsRes.value
            : []
        )
        if (
          treeRes.status === 'rejected' &&
          velocityRes.status === 'rejected' &&
          platformsRes.status === 'rejected'
        ) {
          setDetailError('Analysis failed — check backend configuration or try again later.')
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedId])

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
      await refreshClaims()
      if (claim && claim.id) {
        setSelectedId(claim.id)
      }
    } catch (error) {
      showNotification(
        dispatch,
        error instanceof Error
          ? `Analysis failed — check backend configuration. ${error.message}`
          : 'Analysis failed — check backend configuration.',
        'error'
      )
    } finally {
      setAnalyzing(false)
    }
  }, [text, dispatch, refreshClaims])

  const flow = useMemo(
    () => (tree ? toFlow(tree) : { nodes: [], edges: [] }),
    [tree]
  )

  const selectedClaim = claims.find((c) => c.id === selectedId) || null

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4 text-foreground">Tracker Dashboard</h1>
        <p className="text-lg text-muted-foreground">
          Paste a claim to see how it spreads and mutates across public platforms in Nepal.
        </p>
      </div>

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Claims</CardTitle>
          </CardHeader>
          <CardContent>
            {claimsLoading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : claimsError ? (
              <ErrorState message={claimsError} />
            ) : claims.length === 0 ? (
              <EmptyState message="No claims yet. Analyze one above to get started." />
            ) : (
              <ul className="space-y-2">
                {claims.map((claim) => (
                  <li key={claim.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(claim.id)}
                      className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                        claim.id === selectedId
                          ? 'border-primary bg-accent/40 text-foreground'
                          : 'border-border hover:bg-accent/20 text-muted-foreground'
                      }`}
                    >
                      <span className="line-clamp-2 block">{claim.canonical}</span>
                      {typeof claim.variant_count === 'number' && (
                        <span className="mt-1 mr-2 inline-block rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-foreground">
                          {claim.variant_count} variant{claim.variant_count === 1 ? '' : 's'}
                        </span>
                      )}
                      {claim.verdict && (
                        <span className="mt-1 inline-block text-xs font-medium text-primary">
                          {claim.verdict}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
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
          ) : detailLoading ? (
            <Card>
              <CardContent>
                <div className="flex justify-center py-16">
                  <Spinner size="lg" />
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
              {selectedClaim && (
                <Card>
                  <CardHeader>
                    <CardTitle>Selected claim</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{selectedClaim.canonical}</p>
                    {selectedClaim.verdict && (
                      <p className="mt-2 font-medium text-primary">
                        Verdict: {selectedClaim.verdict}
                      </p>
                    )}
                    {selectedClaim.rationale && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        Rationale: {selectedClaim.rationale}
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <CardTitle>Mutation tree</CardTitle>
                </CardHeader>
                <CardContent>
                  {flow.nodes.length === 0 ? (
                    <EmptyState message="No mutations recorded for this claim yet." />
                  ) : (
                    <div className="h-96 w-full rounded-md border border-border">
                      <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView>
                        <Background />
                        <Controls />
                      </ReactFlow>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Velocity</CardTitle>
                </CardHeader>
                <CardContent>
                  {velocity.length === 0 ? (
                    <EmptyState message="No velocity data available yet." />
                  ) : (
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={velocity}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis dataKey="bucket" fontSize={12} />
                          <YAxis allowDecimals={false} fontSize={12} />
                          <Tooltip />
                          <Line
                            type="monotone"
                            dataKey="count"
                            stroke="var(--primary, #6366f1)"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Platform breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  {platforms.length === 0 ? (
                    <EmptyState message="No platform data available yet." />
                  ) : (
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={platforms}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis dataKey="platform" fontSize={12} />
                          <YAxis allowDecimals={false} fontSize={12} />
                          <Tooltip />
                          <Bar dataKey="count" fill="var(--primary, #6366f1)" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
