import { Plus } from 'lucide-react'
import Container from '../ui/Container'
import Heading from '../ui/Heading'

const questions = [
  {
    question: 'Puis-je annuler mon don mensuel ?',
    answer:
      "Oui, à tout moment depuis votre espace donateur ou en nous écrivant. Aucun frais d'annulation n'est appliqué.",
  },
  {
    question: 'Mon don est-il déductible des impôts ?',
    answer:
      'Oui, selon votre situation fiscale et le régime applicable dans votre pays. Le reçu fiscal détaille le montant à déclarer.',
  },
  {
    question: 'Mes informations bancaires sont-elles protégées ?',
    answer:
      "Les paiements sont chiffrés et traités par un prestataire certifié PCI DSS. L'association ne reçoit jamais le numéro complet de votre carte.",
  },
]

export default function Faq() {
  return (
    <Container className="grid gap-10 py-24 md:grid-cols-[1fr_1.3fr]">
      <Heading>
        Questions <br className="hidden md:block" />
        fréquentes.
      </Heading>

      <div className="border-t border-line">
        {questions.map((item) => (
          <details key={item.question} className="group border-b border-line">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-lg">
              {item.question}
              <Plus className="size-4 shrink-0 text-muted transition-transform group-open:rotate-45" />
            </summary>
            <p className="pb-5 text-muted group-open:animate-fade-in">{item.answer}</p>
          </details>
        ))}
      </div>
    </Container>
  )
}
