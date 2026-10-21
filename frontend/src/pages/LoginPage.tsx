import { Link, useLocation } from 'react-router'
import AuthForm from '../components/auth/AuthForm'
import AuthLayout from '../components/layout/AuthLayout'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { signIn } = useAuth()
  const location = useLocation()

  return (
    <AuthLayout
      title="Connexion"
      subtitle={
        <>
          Pas encore de compte ?{' '}
          <Link to="/inscription" state={location.state} className="text-ink underline hover:text-primary">
            Créer un compte
          </Link>
        </>
      }
    >
      <AuthForm submitLabel="Se connecter" onSubmit={signIn} />
    </AuthLayout>
  )
}
