import { useState, type SubmitEvent } from 'react'
import { Link } from 'react-router'
import Button from '../ui/Button'
import TextField from '../ui/TextField'

export default function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    // TODO : brancher sur le service d'authentification
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <TextField label="Nom d'utilisateur" name="username" autoComplete="username" required />

      <TextField
        label="Mot de passe"
        name="password"
        type={showPassword ? 'text' : 'password'}
        autoComplete="current-password"
        required
        action={
          <Link to="/mot-de-passe-oublie" className="text-muted underline hover:text-ink">
            Mot de passe oublié ?
          </Link>
        }
        suffix={
          <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-muted hover:text-ink">
            {showPassword ? 'Masquer' : 'Afficher'}
          </button>
        }
      />

      <label className="flex items-center gap-3 text-sm">
        <input type="checkbox" name="remember" className="size-4 accent-primary" />
        Se souvenir de moi
      </label>

      <Button type="submit" className="w-full">
        Se connecter
      </Button>

      <p className="text-sm text-muted">
        Pas encore de compte ?{' '}
        <Link to="/inscription" className="text-ink underline hover:text-primary">
          Créer un compte
        </Link>
      </p>
    </form>
  )
}
