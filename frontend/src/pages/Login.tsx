import { Link } from 'react-router-dom'
import LoginForm from '../features/auth/LoginForm'
import { BrandMark } from '../components/ui/BrandMark'

export default function Login() {
  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <BrandMark className="h-8 w-8 text-primary" />
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Welcome back
          </h2>
          <p className="text-sm text-muted-foreground">
            Sign in to continue to GuffGuard
          </p>
        </div>
        <LoginForm />
        <p className="text-center text-sm text-muted-foreground">
          New to GuffGuard?{' '}
          <Link
            to="/register"
            className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
