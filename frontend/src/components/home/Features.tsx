import { CreditCard, FileText, Lock } from 'lucide-react'
import Container from '../ui/Container'
import Heading from '../ui/Heading'

const features = [
  {
    icon: CreditCard,
    title: 'Dons ponctuels ou mensuels',
    description:
      "Un montant unique ou un engagement récurrent, modifiable et annulable à tout moment depuis l'espace donateur.",
  },
  {
    icon: Lock,
    title: 'Paiement chiffré',
    description:
      "Carte bancaire, Apple Pay ou Google Pay. Les données de paiement sont traitées par un prestataire certifié PCI DSS, jamais stockées par l'association.",
  },
  {
    icon: FileText,
    title: 'Reçus fiscaux automatiques',
    description:
      'Chaque paiement génère son reçu, envoyé par e-mail et téléchargeable à tout moment dans votre espace.',
  },
]

export default function Features() {
  return (
    <Container className="py-20">
      <Heading>Donner, sans friction.</Heading>
      <p className="mt-4 max-w-md text-muted">
        Le parcours de don est court, lisible sur mobile et pensé pour que chaque personne puisse donner sans réfléchir
        à la technique.
      </p>

      <ul className="mt-14 grid gap-10 md:grid-cols-3">
        {features.map(({ icon: Icon, title, description }) => (
          <li key={title} className="border-t border-line pt-6">
            <Icon className="size-5 text-primary" />
            <h3 className="mt-6 text-xl font-medium">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{description}</p>
          </li>
        ))}
      </ul>
    </Container>
  )
}
