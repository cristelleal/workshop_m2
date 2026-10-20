import { useDonation } from '../../context/DonationContext'
import { formatDonation } from '../../utils/format'
import AmountPicker from '../donation/AmountPicker'
import FrequencyToggle from '../donation/FrequencyToggle'
import Button from '../ui/Button'
import Card from '../ui/Card'
import Heading from '../ui/Heading'

export default function DonationForm() {
  const { donation, updateDonation } = useDonation()

  return (
    <section id="don" className="py-8">
      <Card className="grid items-center gap-10 bg-sand px-6 py-12 sm:px-14 md:grid-cols-2">
        <div>
          <Heading>Donnez en un clic.</Heading>
          <p className="mt-4 max-w-sm text-muted">
            Choisissez un montant, la fréquence, et finalisez votre don. Le paiement prend moins d'une minute.
          </p>
        </div>

        <div className="space-y-4">
          <FrequencyToggle value={donation.frequency} onChange={(frequency) => updateDonation({ frequency })} />
          <AmountPicker value={donation.amount} onChange={(amount) => updateDonation({ amount })} />
          <Button to="/don" className="w-full">
            Continuer · {formatDonation(donation.amount, donation.frequency)}
          </Button>
        </div>
      </Card>
    </section>
  )
}
