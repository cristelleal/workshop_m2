import { useState } from 'react'
import Button from '../ui/Button'
import Card from '../ui/Card'
import Heading from '../ui/Heading'

type Frequency = 'once' | 'monthly'

const frequencies: { value: Frequency; label: string }[] = [
  { value: 'once', label: 'Une fois' },
  { value: 'monthly', label: 'Chaque mois' },
]

const amounts = [10, 25, 50, 100]

export default function DonationForm() {
  const [frequency, setFrequency] = useState<Frequency>('monthly')
  const [amount, setAmount] = useState(25)

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

          <Button href="/don" className="w-full">
            Continuer · {amount} € {frequency === 'monthly' && 'par mois'}
          </Button>
        </div>
      </Card>
    </section>
  )
}
