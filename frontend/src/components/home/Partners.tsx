import Container from '../ui/Container'
import Eyebrow from '../ui/Eyebrow'

const partners = ['Fondation Lumen', 'Groupe Atlas', 'Fonds Nova', 'Coop Terra', 'Réseau Avenir']

export default function Partners() {
  return (
    <Container className="py-20 text-center">
      <Eyebrow>Ils nous font confiance</Eyebrow>
      <ul className="mt-6 flex flex-wrap justify-center gap-x-12 gap-y-4 text-lg font-medium text-muted/70">
        {partners.map((partner) => (
          <li key={partner}>{partner}</li>
        ))}
      </ul>
    </Container>
  )
}
