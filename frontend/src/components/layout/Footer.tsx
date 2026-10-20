import Container from '../ui/Container'

const footerLinks = [
  { label: 'Mentions légales', href: '/mentions-legales' },
  { label: 'Confidentialité', href: '/confidentialite' },
  { label: 'Transparence financière', href: '#transparence' },
  { label: 'Contact', href: '#contact' },
]

export default function Footer() {
  return (
    <footer id="contact" className="mt-8 border-t border-line">
      <Container className="space-y-4 py-8 text-sm text-muted">
        <nav className="flex flex-wrap gap-x-5 gap-y-2">
          <a href="/" className="font-medium text-ink">
            Given
          </a>
          {footerLinks.map((link) => (
            <a key={link.label} href={link.href} className="hover:text-ink">
              {link.label}
            </a>
          ))}
        </nav>
        <p>Paiement sécurisé par un prestataire certifié PCI DSS · © 2026 Given</p>
      </Container>
    </footer>
  )
}
