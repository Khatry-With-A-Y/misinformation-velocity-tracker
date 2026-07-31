import { ReactNode } from 'react'
import { StatusDot } from '../../components/ui/StatusDot'

export function ErrorBoundary({ children }: { children: ReactNode }) {
  let error: Error | undefined = undefined
  try {
    return children
  } catch (e) {
    error = e instanceof Error ? e : new Error(String(e))
  }

  return (
    <div className="flex items-center">
      <StatusDot status="error" />
      <span className="text-red-600">Error: {error?.message || 'Something went wrong'}</span>
    </div>
  )
}
