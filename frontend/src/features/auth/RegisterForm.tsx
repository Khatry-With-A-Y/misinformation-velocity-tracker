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

function RegisterFormContent() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const { toast } = useToast()
  const { state, setLoading, setError } = useLoadingState('register-form')

  const onSubmit = cache(async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    const formData = new FormData(event.currentTarget)
    const email = formData.get('email') as string
    const username = formData.get('username') as string
    const password = formData.get('password') as string
    const confirmPassword = formData.get('confirmPassword') as string

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    const result = await register({ email, username, password, confirmPassword })

    if (result.success && result.requiresConfirmation) {
      toast({
        title: 'Check your email',
        description:
          result.message || 'Please confirm your email address, then log in.',
      })
      navigate('/login')
    } else if (result.success) {
      toast({
        title: 'Registration successful!',
        description: 'Your account has been created.',
      })
      navigate('/dashboard')
    } else {
      setError(result.error || 'An error occurred during registration')
      toast({
        variant: 'destructive',
        title: 'Error',
        description: result.error || 'An error occurred during registration',
      })
    }

    setLoading(false)
  })

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Start tracking claims with GuffGuard</CardDescription>
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
            <label htmlFor="username" className="text-sm font-medium text-foreground">
              Username
            </label>
            <Input
              id="username"
              name="username"
              type="text"
              placeholder="Choose a username"
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
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium text-foreground">
              Confirm password
            </label>
            <Input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              placeholder="Confirm your password"
              required
              disabled={state.isLoading}
              className="w-full"
            />
          </div>
          {state.error && <div className="text-sm text-destructive">{state.error}</div>}
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={state.isLoading} className="w-full">
            {state.isLoading ? 'Creating account...' : 'Create account'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}

export default function RegisterForm() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RegisterFormContent />
    </Suspense>
  )
}
