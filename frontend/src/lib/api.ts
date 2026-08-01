export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface Claim {
  id: string
  canonical: string
  domain?: string | null
  language?: string | null
  label?: string | null
  verdict?: string | null
  rationale?: string | null
  source?: string | null
  variant_count?: number | null
  created_at?: string
}

export interface ClaimContext extends Claim {
  tier: 'VERIFIED_FALSE' | 'AI_FLAGGED' | 'UNVERIFIED'
  confidence?: number | null
  assessed_at?: string | null
  evidence_url?: string | null
  evidence_title?: string | null
  first_seen?: string | null
  last_seen?: string | null
  current_count: number
  previous_count: number
  top_platform?: string | null
}

export type Period = 'day' | 'week' | 'month' | 'year'
export type DashboardView = 'overview' | 'verified' | 'live'

export interface ClaimPage {
  items: ClaimContext[]
  total: number
  next_cursor?: string | null
}

export interface NewsStatus {
  state: 'fresh' | 'stale' | 'polling' | 'quota_delayed' | 'error'
  stale: boolean
  last_success_at?: string | null
  next_expected_at?: string | null
  latest_run?: {
    status: 'running' | 'succeeded' | 'failed' | 'quota_delayed'
    trigger: 'worker' | 'manual'
    started_at: string
    completed_at?: string | null
    lease_expires_at: string
    counters?: Record<string, number>
    error_summary?: string | null
  } | null
  staging: { pending: number; failed: number }
  sources: Array<{ name: string; url: string }>
}

export interface RankingItem {
  id: string
  canonical: string
  domain?: string | null
  language?: string | null
  source?: string | null
  tier: 'VERIFIED_FALSE' | 'AI_FLAGGED'
  verdict: string
  confidence?: number | null
  rationale?: string | null
  model?: string | null
  assessed_at?: string | null
  evidence_url?: string | null
  evidence_title?: string | null
  current_count: number
  previous_count: number
  percent_change?: number | null
  first_seen?: string | null
  last_seen?: string | null
}

export interface ResearchResource {
  name: string
  url: string
  advisory: string
}

// Matches the backend IngestResponse schema (POST /api/claims/ingest)
export interface IngestResponse {
  id: string
  variant_id: string
  parent_id?: string | null
  matched: boolean
  similarity?: number | null
  canonical: string
  domain: string
  language: string
  label: string
  verdict: string
  rationale: string
  research_resources: ResearchResource[]
  variant_count: number
}

export interface TreeNode {
  id: string
  label: string
  text?: string | null
  platform?: string | null
  ts?: string | null
  mutation_type?: string | null
  language?: string | null
  source?: string | null
  confidence?: number | null
  evidence_url?: string | null
  evidence_title?: string | null
}

export interface TreeEdge {
  source: string
  target: string
}

export interface ClaimTree {
  nodes: TreeNode[]
  edges: TreeEdge[]
}

export interface VelocityPoint {
  bucket: string
  count: number
}

export interface PlatformCount {
  platform: string
  count: number
}

export interface DistributionItem {
  label: string
  count: number
}
export interface TimelinePoint {
  date: string
  count: number
  cumulative: number
}
export interface ClaimAnalytics {
  summary: {
    first_seen?: string | null
    last_seen?: string | null
    observed_variants: number
    current_count: number
    previous_count: number
    top_platform?: string | null
  }
  timeline: TimelinePoint[]
  platforms: DistributionItem[]
  languages: DistributionItem[]
  mutations: DistributionItem[]
  top_variants: TreeNode[]
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })

  return handleResponse<T>(response)
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    // Token missing/expired: clear the session and send the user to login.
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('token')
    }
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.assign('/login')
    }
    throw new Error('Your session has expired. Please log in again.')
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') {
        detail = data.detail
      }
    } catch {
      // ignore JSON parse errors, keep default message
    }
    if (response.status === 429) {
      detail = 'You are submitting too fast. Please wait a moment and try again.'
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export function ingestClaim(text: string): Promise<IngestResponse> {
  return request<IngestResponse>('/api/claims/ingest', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

function queryString(params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

export function listClaims(
  params: {
    limit?: number
    page?: number
    query?: string
    source?: string
    domain?: string
    language?: string
    tier?: string
    period?: Period
    platform?: string
  } = {}
): Promise<ClaimContext[] | ClaimPage> {
  return request<ClaimContext[] | ClaimPage>(`/api/claims${queryString(params)}`)
}

export function getNewsStatus(): Promise<NewsStatus> {
  return request<NewsStatus>('/api/news/status')
}

export function getRankings(
  period: Period,
  tier: 'verified_false' | 'ai_flagged',
  limit = 10
): Promise<RankingItem[]> {
  return request<RankingItem[]>(`/api/analytics/rankings${queryString({ period, tier, limit })}`)
}

export function getClaimAnalytics(claimId: string, period: Period): Promise<ClaimAnalytics> {
  return request<ClaimAnalytics>(`/api/analytics/claims/${claimId}${queryString({ period })}`)
}

export function getTree(claimId: string): Promise<ClaimTree> {
  return request<ClaimTree>(`/api/claims/${claimId}/tree`)
}

export function getVelocity(claimId: string): Promise<VelocityPoint[]> {
  return request<VelocityPoint[]>(`/api/claims/${claimId}/velocity`)
}

export function getPlatforms(claimId: string): Promise<PlatformCount[]> {
  return request<PlatformCount[]>(`/api/claims/${claimId}/platforms`)
}
