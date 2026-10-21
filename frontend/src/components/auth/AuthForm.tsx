import { useState, type SubmitEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { ApiError } from '../../services/api'
import Alert from '../ui/Alert'
import Button from '../ui/Button'
import TextField from '../ui/TextField'

type AuthFormProps = {
  submitLabel: string
  onSubmit: (email: string, password: string) => Promise<void>
  isRegister?: boolean
}

export default function AuthForm({ submitLabel, onSubmit, isRegister = false }: AuthFormProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)

    setSubmitting(true)
    setError(null)
    try {
      await onSubmit(String(data.get('email')), String(data.get('password')))
      // Retour à la page qui a demandé la connexion (ex. le paiement), sinon l'espace donateur
      navigate(location.state?.from ?? '/espace', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Le service ne répond pas. Réessayez dans quelques instants.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && <Alert title="Impossible de continuer">{error}</Alert>}

      <TextField label="E-mail" name="email" type="email" autoComplete="email" required />
      <TextField
        label="Mot de passe"
        name="password"
        type={showPassword ? 'text' : 'password'}
        autoComplete={isRegister ? 'new-password' : 'current-password'}
        minLength={isRegister ? 8 : undefined}
        required
        suffix={
          <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-muted hover:text-ink">
            {showPassword ? 'Masquer' : 'Afficher'}
          </button>
        }
      />

      <Button type="submit" className="w-full" disabled={submitting}>
        {submitting ? 'Un instant…' : submitLabel}
      </Button>
    </form>
  )
}
