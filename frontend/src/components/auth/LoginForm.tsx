import { useState, type SubmitEvent } from 'react'
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
        suffix={
          <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-muted hover:text-ink">
            {showPassword ? 'Masquer' : 'Afficher'}
          </button>
        }
      />

      <Button type="submit" className="w-full">
        Se connecter
      </Button>
    </form>
  )
}
