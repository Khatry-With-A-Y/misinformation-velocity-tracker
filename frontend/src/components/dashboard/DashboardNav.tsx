import type { DashboardView } from '../../lib/api'

const views: { id: DashboardView; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'verified', label: 'Verified claims' },
  { id: 'live', label: 'Live monitor' },
]

export function DashboardNav({
  value,
  onChange,
}: {
  value: DashboardView
  onChange: (view: DashboardView) => void
}) {
  return (
    <nav aria-label="Dashboard views" className="flex gap-1 overflow-x-auto border-b border-border">
      {views.map((view) => (
        <button
          key={view.id}
          type="button"
          onClick={() => onChange(view.id)}
          aria-current={value === view.id ? 'page' : undefined}
          className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
            value === view.id
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          {view.label}
        </button>
      ))}
    </nav>
  )
}
