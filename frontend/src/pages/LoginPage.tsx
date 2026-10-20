import LoginForm from '../components/auth/LoginForm'
import Header from '../components/layout/Header'
import Container from '../components/ui/Container'
import Eyebrow from '../components/ui/Eyebrow'
import Heading from '../components/ui/Heading'
import Reveal from '../components/ui/Reveal'

export default function LoginPage() {
  return (
    <>
      <Header minimal />
      <main>
        <Reveal>
          <Container className="max-w-md py-20">
            <Eyebrow>Espace donateur</Eyebrow>
            <Heading as="h1" className="mt-4">
              Connexion
            </Heading>
            <p className="mt-4 mb-10 text-muted">Faire un don</p>
            <LoginForm />
          </Container>
        </Reveal>
      </main>
    </>
  )
}
