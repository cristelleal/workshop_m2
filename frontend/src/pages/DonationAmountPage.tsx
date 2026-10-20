import AmountForm from '../components/donation/AmountForm'
import DonationSummary from '../components/donation/DonationSummary'
import CheckoutLayout from '../components/layout/CheckoutLayout'
import Eyebrow from '../components/ui/Eyebrow'
import Heading from '../components/ui/Heading'
import { useDonation } from '../context/DonationContext'
import { formatEuro } from '../utils/format'

export default function DonationAmountPage() {
  const { donation } = useDonation()

  const summary = (
    <DonationSummary
      items={[
        { label: 'Don', value: formatEuro(donation.amount) },
        { label: 'Fréquence', value: donation.frequency === 'monthly' ? 'Mensuelle' : 'Ponctuelle' },
        { label: 'Affectation', value: donation.allocation },
      ]}
      note="Vous pouvez modifier ou arrêter votre don à tout moment depuis votre espace donateur."
    />
  )

  return (
    <CheckoutLayout summary={summary}>
      <Eyebrow>Étape 1 sur 2</Eyebrow>
      <Heading as="h1" className="mt-4">
        Soutenez notre action
      </Heading>
      <p className="mt-4 mb-10 text-muted">
        Votre don finance nos programmes toute l'année, en totalité, sans frais pour le bénéficiaire.
      </p>
      <AmountForm />
    </CheckoutLayout>
  )
}
