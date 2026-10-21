import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import DonationSummary from '../components/donation/DonationSummary'
import PaymentForm from '../components/donation/PaymentForm'
import CheckoutLayout from '../components/layout/CheckoutLayout'
import Eyebrow from '../components/ui/Eyebrow'
import Heading from '../components/ui/Heading'
import { useDonation } from '../context/DonationContext'
import { formatEuro } from '../utils/format'

export default function DonationPaymentPage() {
  const { donation } = useDonation()
  const [error, setError] = useState<string | null>(null)
  const isMonthly = donation.frequency === 'monthly'

  const summary = (
    <DonationSummary
      items={[
        { label: isMonthly ? 'Don mensuel' : 'Don ponctuel', value: formatEuro(donation.amount) },
        { label: 'Affectation', value: donation.allocation },
      ]}
      total={error ? 0 : donation.amount}
      note={
        error
          ? "Aucun prélèvement n'a eu lieu. Votre don sera enregistré dès que le paiement aura abouti."
          : `${isMonthly ? `Ensuite, ${formatEuro(donation.amount)} seront prélevés chaque mois. ` : ''}Un reçu fiscal est envoyé après chaque paiement.`
      }
    />
  )

  return (
    <CheckoutLayout summary={summary}>
      <div className="flex items-center justify-between">
        <Link to="/don" className="flex items-center gap-1 text-sm text-muted hover:text-ink">
          <ArrowLeft className="size-4" />
          Modifier le don
        </Link>
        <Eyebrow>Étape 2 sur 2</Eyebrow>
      </div>
      <Heading as="h1" className="mt-4">
        Paiement
      </Heading>
      <p className="mt-4 mb-10 text-muted">
        Don {isMonthly ? 'mensuel' : 'ponctuel'} de {formatEuro(donation.amount)} à Given.
      </p>
      <PaymentForm error={error} onError={setError} />
    </CheckoutLayout>
  )
}
