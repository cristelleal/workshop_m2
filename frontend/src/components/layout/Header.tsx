import { Link } from 'react-router'
import Button from '../ui/Button'
import Container from '../ui/Container'
import Logo from '../ui/Logo'

const navLinks = [
  { label: 'Témoignages', href: '#temoignages' },
  { label: 'Transparence', href: '#transparence' },
]

export default function Header({ minimal = false }: { minimal?: boolean }) {
  return (
    <header>
      <Container className="flex h-20 items-center justify-between">
        <div className="flex items-center gap-8">
          <Logo />
          {!minimal && (
            <nav className="hidden gap-6 text-sm lg:flex">
              {navLinks.map((link) => (
                <a key={link.href} href={link.href} className="hover:text-primary">
                  {link.label}
                </a>
              ))}
            </nav>
          )}
        </div>

        {!minimal && (
          <div className="flex items-center gap-6 text-sm">
            <a href="#contact" className="hidden hover:text-primary sm:inline">
              Contact
            </a>
            <Link to="/connexion" className="hidden hover:text-primary sm:inline">
              Se connecter
            </Link>
            <Button href="#don" size="sm">
              Faire un don
            </Button>
          </div>
        )}
      </Container>
    </header>
  )
}
