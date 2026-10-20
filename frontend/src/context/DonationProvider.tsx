import { useState, type ReactNode } from 'react'
import { allocations } from '../constants/donation'
import { DonationContext, type Donation } from './DonationContext'

const initialDonation: Donation = {
  frequency: 'monthly',
  amount: 25,
  allocation: allocations[0],
  anonymous: false,
}

export default function DonationProvider({ children }: { children: ReactNode }) {
  const [donation, setDonation] = useState(initialDonation)

  const updateDonation = (changes: Partial<Donation>) => setDonation((current) => ({ ...current, ...changes }))

  return <DonationContext value={{ donation, updateDonation }}>{children}</DonationContext>
}
