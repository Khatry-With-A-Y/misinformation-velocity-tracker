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
  platform?: string | null
  ts?: string | null
  mutation_type?: string | null
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

export function listClaims(): Promise<Claim[]> {
  return request<Claim[]>('/api/claims')
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
