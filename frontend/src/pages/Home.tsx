import { Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { CircleCheck, Sparkles } from 'lucide-react'
import { ErrorBoundary } from '../features/health/ErrorBoundary'
import { HealthStatus } from '../features/health/HealthStatus'
import { LoadingStatus } from '../features/health/LoadingStatus'
import { Button } from '../components/ui/Button'

type FeatureItem = {
  id: string
  text: string
}

const features: FeatureItem[] = [
  { id: '1', text: 'Track how a single claim spreads across public platforms' },
  { id: '2', text: 'See mutations over time in an interactive mutation tree' },
  { id: '3', text: 'Measure spread velocity with time-bucketed charts' },
  { id: '4', text: 'Break down reach by platform (Facebook, TikTok, X, and more)' },
  { id: '5', text: 'Reach a clear verdict to support your fact-check' },
  { id: '6', text: 'Built for the Nepal information landscape' },
  { id: '7', text: 'Nepali and English claim support' },
  { id: '8', text: 'Made for journalists and fact-checkers' },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="space-y-12 py-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4 text-foreground">
          Misinformation Velocity Tracker
        </h1>
        <p className="text-lg text-muted-foreground">
          Follow a misinformation claim as it spreads and mutates across public platforms in Nepal:
          velocity, mutation tree, and a verdict to back your fact-check.
        </p>
        <p className="mt-3 text-sm font-medium text-primary">
          No account required for the demo.
        </p>
      </div>

      <div className="grid gap-6">
        <div
          className="p-6 rounded-lg border border-border
          bg-card text-card-foreground shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0 p-2 rounded-lg bg-accent text-accent-foreground">
              <CircleCheck />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold mb-4 text-card-foreground">Backend Status</h2>
              <ErrorBoundary>
                <Suspense fallback={<LoadingStatus />}>
                  <HealthStatus />
                </Suspense>
              </ErrorBoundary>
            </div>
          </div>
        </div>

        <div
          className="p-6 rounded-lg border border-border
          bg-card text-card-foreground shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0 p-2 rounded-lg bg-accent text-accent-foreground">
              <Sparkles />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold mb-4 text-card-foreground">Features</h2>
              <ul className="space-y-3 text-muted-foreground">
                {features.map(({ id, text }) => (
                  <li key={id} className="flex items-center">
                    <span className="text-primary mr-2">✓</span>
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-center space-x-4">
        <Button onClick={() => navigate('/dashboard')} variant="default">
          Open Demo Dashboard
        </Button>
        <Button onClick={() => navigate('/about')} variant="secondary">
          Learn More
        </Button>
      </div>
    </div>
  )
}
