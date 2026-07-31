type StatusDotStatus = 'healthy' | 'error' | 'loading'

export function StatusDot({ status }: { status: string }) {
  const colors: Record<StatusDotStatus, string> = {
    healthy: 'bg-green-500',
    error: 'bg-red-500',
    loading: 'bg-gray-300 animate-pulse',
  }

  return (
    <div
      className={`w-3 h-3 rounded-full mr-2 ${colors[status as StatusDotStatus] || colors.error}`}
    />
  )
}
