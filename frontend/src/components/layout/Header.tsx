import Button from '../ui/Button'
import Container from '../ui/Container'

const navLinks = [
  { label: 'Témoignages', href: '#temoignages' },
  { label: 'Transparence', href: '#transparence' },
]

export default function Header() {
  return (
    <header>
      <Container className="flex items-center justify-between py-5">
        <div className="flex items-center gap-8">
          <a href="/" className="text-lg font-medium">
            Given
          </a>
          <nav className="hidden gap-6 text-sm lg:flex">
            {navLinks.map((link) => (
              <a key={link.href} href={link.href} className="hover:text-primary">
                {link.label}
              </a>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-6 text-sm">
          <a href="#contact" className="hidden hover:text-primary sm:inline">
            Contact
          </a>
          <a href="/connexion" className="hidden hover:text-primary sm:inline">
            Se connecter
          </a>
          <Button href="#don" size="sm">
            Faire un don
          </Button>
        </div>
      </Container>
    </header>
  )
}
