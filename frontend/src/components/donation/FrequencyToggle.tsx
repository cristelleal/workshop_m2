import { frequencies } from '../../constants/donation'
import type { Frequency } from '../../context/DonationContext'

type FrequencyToggleProps = {
  value: Frequency
  onChange: (frequency: Frequency) => void
}

export default function FrequencyToggle({ value, onChange }: FrequencyToggleProps) {
  return (
    <div className="inline-flex rounded-lg bg-line p-1 text-sm">
      {frequencies.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-md px-4 py-1.5 transition ${value === option.value ? 'bg-white shadow-sm' : 'text-muted'}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
