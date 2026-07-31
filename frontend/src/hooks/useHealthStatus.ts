// Cache the promise to avoid creating a new one on every render
import { API_URL } from '@/lib/api'

interface HealthStatusData {
  status: string
  message?: string
}

let healthPromise: Promise<HealthStatusData> | null = null

export function useHealthStatus() {
  if (!healthPromise) {
    healthPromise = fetchHealthStatus()
  }
  return healthPromise
}

async function fetchHealthStatus() {
  try {
    const response = await fetch(`${API_URL}/api/health`)
    if (!response.ok) return { status: 'error' }
    const data = await response.json()
    return data
  } catch (error) {
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Unknown error',
    }
  }
}
