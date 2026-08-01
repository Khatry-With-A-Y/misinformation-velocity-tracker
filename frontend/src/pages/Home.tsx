import { Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorBoundary } from '../features/health/ErrorBoundary'
import { HealthStatus } from '../features/health/HealthStatus'
import { LoadingStatus } from '../features/health/LoadingStatus'
import { Button } from '../components/ui/Button'

type Feature = {
  id: string
  title: string
  text: string
}

const features: Feature[] = [
  {
    id: '1',
    title: 'Mutation tree',
    text: 'See how a claim is reworded, translated, and reshared, from the first observed post outward.',
  },
  {
    id: '2',
    title: 'Spread velocity',
    text: 'Time-bucketed charts show when a claim surges, so you can act before it peaks.',
  },
  {
    id: '3',
    title: 'Platform breakdown',
    text: 'Know where the spread is happening: Facebook, TikTok, X, news sites, and more.',
  },
  {
    id: '4',
    title: 'Evidence-backed verdicts',
    text: 'Verified false claims carry sources. AI flags are labeled as signals, not verified facts.',
  },
  {
    id: '5',
    title: 'Built for Nepal',
    text: 'Handles claims in Nepali and English, tuned to the local information landscape.',
  },
  {
    id: '6',
    title: 'Made for newsrooms',
    text: 'A simple workflow: paste a claim, analyze it, and share the verdict with readers.',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-3xl space-y-14 py-6">
      <section>
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">GuffGuard</p>
        <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight text-foreground sm:text-4xl">
          GuffGuard tracks how rumors mutate before they become impossible to untangle.
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Follow a misinformation claim as it spreads across public platforms in Nepal: spread
          velocity, mutation trees, platform reach, and evidence-backed verdicts to support your
          fact-check.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button onClick={() => navigate('/dashboard')} variant="default">
            Open the dashboard
          </Button>
          <Button onClick={() => navigate('/about')} variant="outline">
            How it works
          </Button>
        </div>
      </section>

      <section aria-labelledby="features-title">
        <h2 id="features-title" className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
          What you can do
        </h2>
        <dl className="mt-5 grid gap-x-10 gap-y-7 sm:grid-cols-2">
          {features.map(({ id, title, text }) => (
            <div key={id} className="border-t border-border pt-4">
              <dt className="font-semibold text-foreground">{title}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{text}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="status-title" className="rounded-lg border border-border bg-card p-5">
        <h2 id="status-title" className="text-sm font-semibold text-card-foreground">
          Backend status
        </h2>
        <div className="mt-3">
          <ErrorBoundary>
            <Suspense fallback={<LoadingStatus />}>
              <HealthStatus />
            </Suspense>
          </ErrorBoundary>
        </div>
      </section>
    </div>
  )
}
