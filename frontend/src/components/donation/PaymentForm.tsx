import { useState, type SubmitEvent } from 'react'
import { useNavigate } from 'react-router'
import { countries } from '../../constants/donation'
import { useAuth } from '../../context/AuthContext'
import { useDonation } from '../../context/DonationContext'
import { ApiError } from '../../services/api'
import { createDonation } from '../../services/donations'
import { formatDonation } from '../../utils/format'
import Alert from '../ui/Alert'
import Button from '../ui/Button'
import SelectField from '../ui/SelectField'
import TextField from '../ui/TextField'

// Raisons renvoyées par l'API (failure_reason), plus "unavailable" quand l'API ne répond pas.
const errorMessages: Record<string, string> = {
  card_declined: 'Votre banque a refusé cette carte. Essayez une autre carte ou un autre moyen de paiement.',
  insufficient_funds: 'Les fonds sont insuffisants sur cette carte. Essayez une autre carte.',
  unknown_test_card: "Cette carte n'est pas reconnue. Vérifiez le numéro ou utilisez une autre carte.",
  unavailable: 'Le service de paiement ne répond pas pour le moment. Réessayez dans quelques instants.',
}

type PaymentFormProps = {
  error: string | null
  onError: (error: string) => void
}

export default function PaymentForm({ error, onError }: PaymentFormProps) {
  const { user, signOut } = useAuth()
  const { donation, updateDonation } = useDonation()
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const cardNumber = String(data.get('cardNumber')).replace(/\s/g, '')

    setSubmitting(true)
    try {
      const result = await createDonation(donation.amount, donation.frequency, cardNumber)
      if (result.status !== 'succeeded') return onError(result.failureReason ?? 'card_declined')

      updateDonation({ donorName: String(data.get('cardholder')) })
      navigate(`/don/confirmation/${result.id}`)
    } catch (err) {
      // Session expirée : la déconnexion renvoie vers la page de connexion
      if (err instanceof ApiError && err.status === 401) return signOut()
      onError('unavailable')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <Alert title="Le paiement n'a pas abouti">
          {errorMessages[error] ?? errorMessages.card_declined} Aucun montant n'a été prélevé.
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

      <TextField label="E-mail" name="email" type="email" value={user?.email} readOnly />
      <TextField
        label="Numéro de carte"
        name="cardNumber"
        inputMode="numeric"
        autoComplete="cc-number"
        placeholder="1234 1234 1234 1234"
        maxLength={19}
        pattern="[0-9 ]{16,19}"
        title="16 chiffres"
        required
        error={error && error !== 'unavailable' ? 'Cette carte a été refusée. Vérifiez-la ou utilisez-en une autre.' : undefined}
      />
      <div className="grid grid-cols-2 gap-2">
        <TextField label="Expiration" name="expiry" autoComplete="cc-exp" placeholder="MM / AA" required />
        <TextField label="CVC" name="cvc" inputMode="numeric" autoComplete="cc-csc" placeholder="123" maxLength={4} required />
      </div>
      <TextField label="Nom sur la carte" name="cardholder" autoComplete="cc-name" required />
      <SelectField label="Pays" name="country" options={countries} />

      <Button type="submit" className="w-full" disabled={submitting}>
        {submitting
          ? 'Paiement en cours…'
          : `${error ? 'Réessayer ·' : 'Donner'} ${formatDonation(donation.amount, donation.frequency)}`}
      </Button>
      <p className="text-center text-sm text-muted">
        Paiement chiffré par un prestataire certifié PCI DSS · Annulable à tout moment
      </p>
    </form>
  )
}
