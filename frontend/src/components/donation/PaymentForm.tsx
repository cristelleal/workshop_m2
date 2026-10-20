import type { SubmitEvent } from 'react'
import { useNavigate } from 'react-router'
import { countries } from '../../constants/donation'
import { useDonation } from '../../context/DonationContext'
import { formatDonation } from '../../utils/format'
import Alert from '../ui/Alert'
import Button from '../ui/Button'
import SelectField from '../ui/SelectField'
import TextField from '../ui/TextField'

// Simulation front : aucun prestataire n'est encore branché, cette carte de test est toujours refusée.
const REFUSED_TEST_CARD = '4000000000000002'

type PaymentFormProps = {
  refused: boolean
  onRefused: () => void
}

export default function PaymentForm({ refused, onRefused }: PaymentFormProps) {
  const { donation, updateDonation } = useDonation()
  const navigate = useNavigate()

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const cardNumber = String(data.get('cardNumber')).replace(/\s/g, '')

    if (cardNumber === REFUSED_TEST_CARD) return onRefused()

    updateDonation({
      payment: {
        email: String(data.get('email')),
        cardholder: String(data.get('cardholder')),
        last4: cardNumber.slice(-4),
        receiptNumber: `GIV-${Date.now().toString().slice(-8)}`,
        date: new Date(),
      },
    })
    navigate('/don/confirmation')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {refused && (
        <Alert title="Le paiement n'a pas abouti">
          Votre banque a refusé cette carte. Essayez une autre carte ou un autre moyen de paiement. Aucun montant n'a été
          prélevé.
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-2">
        <Button type="button" variant="outline">
          Apple Pay
        </Button>
        <Button type="button" variant="outline">
          Google Pay
        </Button>
      </div>

      <div className="flex items-center gap-4 text-sm text-muted">
        <span className="h-px flex-1 bg-line" />
        ou payer par carte
        <span className="h-px flex-1 bg-line" />
      </div>

      <TextField label="E-mail" name="email" type="email" autoComplete="email" placeholder="vous@exemple.fr" required />
      <TextField
        label="Numéro de carte"
        name="cardNumber"
        inputMode="numeric"
        autoComplete="cc-number"
        placeholder="1234 1234 1234 1234"
        maxLength={19}
        required
        error={refused ? 'Cette carte a été refusée. Vérifiez-la ou utilisez-en une autre.' : undefined}
      />
      <div className="grid grid-cols-2 gap-2">
        <TextField label="Expiration" name="expiry" autoComplete="cc-exp" placeholder="MM / AA" required />
        <TextField label="CVC" name="cvc" inputMode="numeric" autoComplete="cc-csc" placeholder="123" maxLength={4} required />
      </div>
      <TextField label="Nom sur la carte" name="cardholder" autoComplete="cc-name" required />
      <SelectField label="Pays" name="country" options={countries} />

      <Button type="submit" className="w-full">
        {refused ? 'Réessayer ·' : 'Donner'} {formatDonation(donation.amount, donation.frequency)}
      </Button>
      <p className="text-center text-sm text-muted">
        Paiement chiffré par un prestataire certifié PCI DSS · Annulable à tout moment
      </p>
    </form>
  )
}
