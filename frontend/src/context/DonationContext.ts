import { createContext, useContext } from 'react'
import type { Presets } from '../services/donations'

export type Frequency = 'once' | 'monthly'

export type Donation = {
  frequency: Frequency
  amount: number
  allocation: string
  donorName?: string
}

type DonationContextValue = {
  donation: Donation
  presets: Presets
  updateDonation: (changes: Partial<Donation>) => void
}

export const DonationContext = createContext<DonationContextValue | null>(null)

export function useDonation() {
  const context = useContext(DonationContext)
  if (!context) throw new Error('useDonation doit être utilisé dans un DonationProvider')
  return context
}
