import { useState, type SubmitEvent } from 'react'
import { useNavigate } from 'react-router'
import { allocations } from '../../constants/donation'
import { useDonation } from '../../context/DonationContext'
import { formatEuro } from '../../utils/format'
import Button from '../ui/Button'
import SelectField from '../ui/SelectField'
import TextField from '../ui/TextField'
import AmountPicker from './AmountPicker'
import FrequencyToggle from './FrequencyToggle'

export default function AmountForm() {
  const { donation, presets, updateDonation } = useDonation()
  const navigate = useNavigate()
  const [customAmount, setCustomAmount] = useState(presets.amounts.includes(donation.amount) ? '' : String(donation.amount))

  const selectAmount = (amount: number) => {
    setCustomAmount('')
    updateDonation({ amount })
  }

  const changeCustomAmount = (value: string) => {
    setCustomAmount(value)
    updateDonation({ amount: Number(value) || 0 })
  }

  const outOfRange = donation.amount < presets.min || donation.amount > presets.max

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
          min={presets.min}
          max={presets.max}
          step="0.01"
          inputMode="decimal"
          placeholder="0,00"
          suffix="€"
          value={customAmount}
          onChange={(event) => changeCustomAmount(event.target.value)}
          error={customAmount && outOfRange ? `Le montant doit être compris entre ${formatEuro(presets.min)} et ${formatEuro(presets.max)}.` : undefined}
        />
      </div>

      <SelectField
        label="Affectation"
        options={allocations}
        value={donation.allocation}
        onChange={(event) => updateDonation({ allocation: event.target.value })}
      />

      <Button type="submit" className="w-full" disabled={outOfRange}>
        Continuer
      </Button>
      <p className="text-center text-sm text-muted">Paiement sécurisé · Reçu fiscal envoyé par e-mail</p>
    </form>
  )
}
