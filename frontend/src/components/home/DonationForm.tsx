<<<<<<< HEAD
import { useState } from 'react'
import Card from '../ui/Card'
import Heading from '../ui/Heading'

type Frequency = 'once' | 'monthly'
type Status = 'idle' | 'loading' | 'success' | 'error'

const frequencies: { value: Frequency; label: string }[] = [
  { value: 'once', label: 'Une fois' },
  { value: 'monthly', label: 'Chaque mois' },
]

const amounts = [10, 25, 50, 100]

export default function DonationForm() {
  const [frequency, setFrequency] = useState<Frequency>('monthly')
  const [amount, setAmount] = useState(25)
  const [status, setStatus] = useState<Status>('idle')

  async function submitDonation() {
    setStatus('loading')
    try {
      const response = await fetch('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, currency: 'EUR', frequency }),
      })
      setStatus(response.ok ? 'success' : 'error')
    } catch {
      setStatus('error')
    }
  }
=======
import { useDonation } from '../../context/DonationContext'
import { formatDonation } from '../../utils/format'
import AmountPicker from '../donation/AmountPicker'
import FrequencyToggle from '../donation/FrequencyToggle'
import Button from '../ui/Button'
import Card from '../ui/Card'
import Heading from '../ui/Heading'

export default function DonationForm() {
  const { donation, updateDonation } = useDonation()
>>>>>>> main

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
<<<<<<< HEAD
          <div className="inline-flex rounded-lg bg-line p-1 text-sm">
            {frequencies.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setFrequency(option.value)}
                className={`rounded-md px-4 py-1.5 transition ${frequency === option.value ? 'bg-white shadow-sm' : 'text-muted'}`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-4 gap-2">
            {amounts.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setAmount(value)}
                className={`rounded-lg border bg-white py-3 transition hover:border-primary/50 ${
                  amount === value ? 'border-primary font-medium text-primary' : 'border-line'
                }`}
              >
                {value} €
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={submitDonation}
            disabled={status === 'loading'}
            className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-6 py-3 text-base font-medium text-white transition hover:bg-primary/90 active:scale-[0.98] disabled:opacity-60"
          >
            Continuer · {amount} € {frequency === 'monthly' && 'par mois'}
          </button>

          {status === 'success' && <p className="text-sm text-primary">Merci, votre don a bien été enregistré.</p>}
          {status === 'error' && <p className="text-sm text-red-600">Le paiement a échoué, réessayez dans un instant.</p>}
=======
          <FrequencyToggle value={donation.frequency} onChange={(frequency) => updateDonation({ frequency })} />
          <AmountPicker value={donation.amount} onChange={(amount) => updateDonation({ amount })} />
          <Button to="/don" className="w-full">
            Continuer · {formatDonation(donation.amount, donation.frequency)}
          </Button>
>>>>>>> main
        </div>
      </Card>
    </section>
  )
}
