import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TimelinePoint } from '../../lib/api'

export function SpreadTimeline({ data }: { data: TimelinePoint[] }) {
  const total = data.at(-1)?.cumulative || 0
  const peak = data.reduce<TimelinePoint | null>(
    (best, point) => (!best || point.count > best.count ? point : best),
    null
  )
  const compactDate = (value: string) => {
    const date = new Date(`${value}T00:00:00`)
    return Number.isNaN(date.getTime())
      ? value
      : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }
  return (
    <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
      <h2 className="text-lg font-semibold tracking-tight">Spread over time</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Daily observations and cumulative variants, not estimated audience reach.
      </p>
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No timestamped activity in this period.
        </p>
      ) : (
        <>
          <dl className="mt-4 flex flex-wrap gap-x-10 gap-y-2 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Recorded total</dt>
              <dd className="mt-0.5 font-semibold tabular-nums">{total} observations</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Peak day</dt>
              <dd className="mt-0.5 font-semibold tabular-nums">
                {peak?.count || 0} on {peak ? compactDate(peak.date) : 'Unknown'}
              </dd>
            </div>
          </dl>
          <div className="mt-5 h-72">
            <ResponsiveContainer>
              <ComposedChart data={data}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  fontSize={11}
                  tick={{ fill: 'var(--muted-foreground)' }}
                  axisLine={{ stroke: 'var(--border)' }}
                  tickLine={{ stroke: 'var(--border)' }}
                  tickFormatter={compactDate}
                  label={{
                    value: 'Observation date',
                    position: 'insideBottom',
                    offset: -4,
                    fill: 'var(--muted-foreground)',
                    fontSize: 11,
                  }}
                  height={48}
                />
                <YAxis
                  allowDecimals={false}
                  fontSize={11}
                  tick={{ fill: 'var(--muted-foreground)' }}
                  axisLine={{ stroke: 'var(--border)' }}
                  tickLine={{ stroke: 'var(--border)' }}
                  label={{
                    value: 'Observed variants',
                    angle: -90,
                    position: 'insideLeft',
                    fill: 'var(--muted-foreground)',
                    fontSize: 11,
                  }}
                  width={54}
                />
                <Tooltip
                  cursor={{ fill: 'var(--muted)', opacity: 0.4 }}
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    color: 'var(--popover-foreground)',
                    fontSize: 12,
                    boxShadow: 'none',
                  }}
                  labelStyle={{ color: 'var(--muted-foreground)', marginBottom: 4 }}
                  itemStyle={{ color: 'var(--popover-foreground)' }}
                  labelFormatter={(value) => `Date: ${compactDate(String(value))}`}
                  formatter={(value, name) => [
                    `${value} observed variant${Number(value) === 1 ? '' : 's'}`,
                    name === 'Daily observations' ? 'Daily' : 'Cumulative',
                  ]}
                />
                <Bar
                  dataKey="count"
                  name="Daily observations"
                  fill="var(--chart-1)"
                  opacity={0.4}
                  radius={[3, 3, 0, 0]}
                />
                <Line
                  dataKey="cumulative"
                  name="Cumulative observations"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <table className="sr-only">
            <caption>Spread over time, recorded variants only</caption>
            <thead>
              <tr>
                <th>Date</th>
                <th>Daily observed variants</th>
                <th>Cumulative observed variants</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point) => (
                <tr key={point.date}>
                  <td>{point.date}</td>
                  <td>{point.count}</td>
                  <td>{point.cumulative}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
