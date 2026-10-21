import { useEffect, useState, type ReactNode } from 'react'
import { allocations, defaultPresets } from '../constants/donation'
import { getPresets } from '../services/donations'
import { DonationContext, type Donation } from './DonationContext'

const initialDonation: Donation = {
  frequency: 'monthly',
  amount: 25,
  allocation: allocations[0],
}

export default function DonationProvider({ children }: { children: ReactNode }) {
  const [donation, setDonation] = useState(initialDonation)
  const [presets, setPresets] = useState(defaultPresets)

  useEffect(() => {
    getPresets()
      .then(setPresets)
      .catch(() => {}) // On garde les montants par défaut
  }, [])

  const updateDonation = (changes: Partial<Donation>) => setDonation((current) => ({ ...current, ...changes }))

  return <DonationContext value={{ donation, presets, updateDonation }}>{children}</DonationContext>
}
