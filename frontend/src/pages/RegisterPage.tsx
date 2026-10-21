import { Link, useLocation } from 'react-router'
import AuthForm from '../components/auth/AuthForm'
import AuthLayout from '../components/layout/AuthLayout'
import { useAuth } from '../context/AuthContext'

export default function RegisterPage() {
  const { signUp } = useAuth()
  const location = useLocation()

  return (
    <AuthLayout
      title="Créer un compte"
      subtitle={
        <>
          Déjà inscrit ?{' '}
          <Link to="/connexion" state={location.state} className="text-ink underline hover:text-primary">
            Se connecter
          </Link>
        </>
      }
    >
      <AuthForm submitLabel="Créer mon compte" onSubmit={signUp} isRegister />
    </AuthLayout>
  )
}
