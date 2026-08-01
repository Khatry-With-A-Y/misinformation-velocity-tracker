import { useNavigate } from 'react-router-dom'
import { Suspense, cache } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthContext'
import { useLoadingState } from '@/hooks/useLoadingState'

function LoginFormContent() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { toast } = useToast()
  const { state, setLoading, setError } = useLoadingState('login-form')

  const onSubmit = cache(async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    const formData = new FormData(event.currentTarget)
    const email = formData.get('email') as string
    const password = formData.get('password') as string

    const result = await login({ email, password })

    if (result.success) {
      toast({
        title: 'Welcome back!',
        description: 'You have successfully logged in.',
      })
      navigate('/dashboard')
    } else {
      setError(result.error || 'An error occurred during login')
      toast({
        variant: 'destructive',
        title: 'Error',
        description: result.error || 'An error occurred during login',
      })
    }

    setLoading(false)
  })

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Use your GuffGuard email and password</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium text-foreground">
              Email
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="name@example.com"
              required
              disabled={state.isLoading}
              className="w-full"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium text-foreground">
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="Enter your password"
              required
              disabled={state.isLoading}
              className="w-full"
            />
          </div>
          {state.error && <div className="text-sm text-destructive">{state.error}</div>}
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={state.isLoading} className="w-full">
            {state.isLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}

export default function LoginForm() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginFormContent />
    </Suspense>
  )
}
