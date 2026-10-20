import type { Frequency } from '../context/DonationContext'

const euro = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' })

export const formatEuro = (amount: number) => euro.format(amount)

export const formatDonation = (amount: number, frequency: Frequency) =>
  frequency === 'monthly' ? `${formatEuro(amount)} par mois` : formatEuro(amount)

export const formatDate = (date: Date) =>
  date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
