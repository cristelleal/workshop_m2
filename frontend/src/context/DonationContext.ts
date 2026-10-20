import { createContext, useContext } from 'react'

export type Frequency = 'once' | 'monthly'

export type Payment = {
  email: string
  cardholder: string
  last4: string
  receiptNumber: string
  date: Date
}

export type Donation = {
  frequency: Frequency
  amount: number
  allocation: string
  anonymous: boolean
  payment?: Payment
}

type DonationContextValue = {
  donation: Donation
  updateDonation: (changes: Partial<Donation>) => void
}

export const DonationContext = createContext<DonationContextValue | null>(null)

export function useDonation() {
  const context = useContext(DonationContext)
  if (!context) throw new Error('useDonation doit être utilisé dans un DonationProvider')
  return context
}
