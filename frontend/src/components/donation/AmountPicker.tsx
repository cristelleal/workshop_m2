import { useDonation } from '../../context/DonationContext'

type AmountPickerProps = {
  value: number | null
  onChange: (amount: number) => void
}

export default function AmountPicker({ value, onChange }: AmountPickerProps) {
  const { presets } = useDonation()

  return (
    <div className="grid grid-cols-4 gap-2">
      {presets.amounts.map((amount) => (
        <button
          key={amount}
          type="button"
          onClick={() => onChange(amount)}
          className={`rounded-lg border bg-white py-3 transition hover:border-primary/50 ${
            value === amount ? 'border-primary font-medium text-primary' : 'border-line'
          }`}
        >
          {amount} €
        </button>
      ))}
    </div>
  )
}
