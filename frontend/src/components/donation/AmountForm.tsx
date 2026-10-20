import { useState, type SubmitEvent } from 'react'
import { useNavigate } from 'react-router'
import { allocations, amounts } from '../../constants/donation'
import { useDonation } from '../../context/DonationContext'
import Button from '../ui/Button'
import SelectField from '../ui/SelectField'
import TextField from '../ui/TextField'
import AmountPicker from './AmountPicker'
import FrequencyToggle from './FrequencyToggle'

export default function AmountForm() {
  const { donation, updateDonation } = useDonation()
  const navigate = useNavigate()
  const [customAmount, setCustomAmount] = useState(amounts.includes(donation.amount) ? '' : String(donation.amount))

  const selectAmount = (amount: number) => {
    setCustomAmount('')
    updateDonation({ amount })
  }

  const changeCustomAmount = (value: string) => {
    setCustomAmount(value)
    updateDonation({ amount: Number(value) || 0 })
  }

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    navigate('/don/paiement')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <FrequencyToggle value={donation.frequency} onChange={(frequency) => updateDonation({ frequency })} />

      <div className="space-y-3">
        <p className="text-sm">Montant</p>
        <AmountPicker value={customAmount ? null : donation.amount} onChange={selectAmount} />
        <TextField
          label="Autre montant"
          type="number"
          min="1"
          step="0.01"
          inputMode="decimal"
          placeholder="0,00"
          suffix="€"
          value={customAmount}
          onChange={(event) => changeCustomAmount(event.target.value)}
        />
      </div>

      <SelectField
        label="Affectation"
        options={allocations}
        value={donation.allocation}
        onChange={(event) => updateDonation({ allocation: event.target.value })}
      />

      <Button type="submit" className="w-full" disabled={donation.amount <= 0}>
        Continuer
      </Button>
      <p className="text-center text-sm text-muted">Paiement sécurisé · Reçu fiscal envoyé par e-mail</p>
    </form>
  )
}
