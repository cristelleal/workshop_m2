import { Check } from 'lucide-react'
import { Link, Navigate } from 'react-router'
import Header from '../components/layout/Header'
import Button from '../components/ui/Button'
import Container from '../components/ui/Container'
import DetailList from '../components/ui/DetailList'
import Heading from '../components/ui/Heading'
import Reveal from '../components/ui/Reveal'
import { useDonation } from '../context/DonationContext'
import { formatDate, formatEuro } from '../utils/format'

export default function DonationConfirmationPage() {
  const { donation } = useDonation()
  const { payment } = donation

  if (!payment) return <Navigate to="/don" replace />

  const isMonthly = donation.frequency === 'monthly'
  const firstName = payment.cardholder.split(' ')[0]

  return (
    <>
      <Header minimal />
      <main>
        <Reveal>
          <Container className="max-w-xl py-20">
            <span className="flex size-16 items-center justify-center rounded-full bg-primary/10">
              <Check className="size-6 text-primary" />
            </span>
            <Heading as="h1" className="mt-8">
              Merci, {firstName}.
            </Heading>
            <p className="mt-4 text-muted">
              Votre don {isMonthly && 'mensuel '}de {formatEuro(donation.amount)} est confirmé.{' '}
              {isMonthly ? 'Le premier prélèvement a été effectué' : 'Le paiement a été effectué'} aujourd'hui, et votre
              reçu fiscal est envoyé à {payment.email}.
            </p>

            <DetailList
              className="mt-10 rounded-2xl border border-line px-6 py-2"
              items={[
                { label: 'Montant', value: `${formatEuro(donation.amount)}${isMonthly ? ' / mois' : ''}` },
                { label: 'Date', value: formatDate(payment.date) },
                { label: 'Affectation', value: donation.allocation },
                { label: 'Moyen de paiement', value: `Carte se terminant par ${payment.last4}` },
                { label: 'Numéro de reçu', value: payment.receiptNumber },
              ]}
            />

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <Button type="button" variant="outline" onClick={() => window.print()}>
                Télécharger le reçu
              </Button>
              <Button to="/">Retour à Given</Button>
            </div>
            <p className="mt-6 text-sm text-muted">
              Pour modifier ou arrêter votre don, rendez-vous dans{' '}
              <Link to="/connexion" className="text-ink underline hover:text-primary">
                votre espace donateur
              </Link>
              .
            </p>
          </Container>
        </Reveal>
      </main>
    </>
  )
}
