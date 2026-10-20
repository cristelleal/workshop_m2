import Container from '../ui/Container'
import Eyebrow from '../ui/Eyebrow'
import Heading from '../ui/Heading'

const programs = [
  { name: 'Cartables pour tous', category: "Accès à l'éducation", share: '62 %' },
  { name: 'Urgence solidaire', category: "Aide d'urgence", share: '28 %' },
  { name: 'Vie de l’association', category: 'Fonctionnement et collecte', share: '10 %' },
]

export default function Transparency() {
  return (
    <section id="transparence" className="bg-sand py-24">
      <Container className="grid gap-12 md:grid-cols-2">
        <div>
          <Eyebrow>Transparence</Eyebrow>
          <Heading className="mt-4">Chaque euro a une destination.</Heading>
          <p className="mt-6 max-w-sm text-muted">
            Répartition publiée chaque année, rapport d'activité en ligne et suivi des programmes financés par vos dons.
          </p>
        </div>

        <ul className="border-t border-line">
          {programs.map((program) => (
            <li key={program.name} className="flex items-center justify-between border-b border-line py-6">
              <div>
                <p className="text-lg">{program.name}</p>
                <p className="text-sm text-muted">{program.category}</p>
              </div>
              <p className="text-4xl text-primary">{program.share}</p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  )
}
