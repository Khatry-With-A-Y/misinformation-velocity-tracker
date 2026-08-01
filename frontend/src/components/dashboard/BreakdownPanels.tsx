import type { DistributionItem } from '../../lib/api'

function Breakdown({
  title,
  data,
  percentages = false,
}: {
  title: string
  data: DistributionItem[]
  percentages?: boolean
}) {
  const max = Math.max(...data.map((item) => item.count), 1)
  const total = data.reduce((sum, item) => sum + item.count, 0)
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      {data.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">No data recorded.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <thead className="sr-only">
            <tr>
              <th>Value</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 6).map((item) => (
              <tr key={item.label}>
                <td className="py-2 pr-3">
                  <span className="block truncate text-foreground">{item.label || 'Unknown'}</span>
                  <span className="mt-1.5 block h-1 rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary/70"
                      style={{ width: `${(item.count / max) * 100}%` }}
                    />
                  </span>
                </td>
                <td className="w-20 whitespace-nowrap text-right align-top text-xs font-medium tabular-nums text-muted-foreground">
                  <span className="text-sm text-foreground">{item.count}</span>
                  {percentages && total > 0 ? ` (${Math.round((item.count / total) * 100)}%)` : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function BreakdownPanels({
  platforms,
  languages,
  mutations,
}: {
  platforms: DistributionItem[]
  languages: DistributionItem[]
  mutations: DistributionItem[]
}) {
  const platformTotal = platforms.reduce((sum, item) => sum + item.count, 0)
  const dominant = [...platforms].sort(
    (a, b) => b.count - a.count || a.label.localeCompare(b.label)
  )[0]
  return (
    <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Where it spread</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {platformTotal} recorded observations. Dominant platform:{' '}
          <span className="font-medium text-foreground">{dominant?.label || 'Unknown'}</span>.
        </p>
      </div>
      <div className="mt-6 grid gap-8 md:grid-cols-3 md:gap-6">
        <Breakdown title="Recorded platforms" data={platforms} percentages />
        <Breakdown title="Languages" data={languages} />
        <Breakdown title="Mutation types" data={mutations} />
      </div>
    </section>
  )
}
