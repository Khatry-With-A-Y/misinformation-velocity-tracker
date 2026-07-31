// Matches the backend UserResponse schema (GET /api/auth/me)
export interface User {
  id: string
  email?: string | null
  username?: string | null
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials extends LoginCredentials {
  username: string
  confirmPassword?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface AuthResult {
  success: boolean
  error: string | null
  /** Set when registration succeeded but email confirmation is pending. */
  requiresConfirmation?: boolean
  message?: string | null
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}
