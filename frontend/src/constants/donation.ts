import type { Frequency } from '../context/DonationContext'

export const amounts = [10, 25, 50, 100]

export const frequencies: { value: Frequency; label: string }[] = [
  { value: 'once', label: 'Une fois' },
  { value: 'monthly', label: 'Chaque mois' },
]

export const allocations = ['Toutes nos actions', 'Cartables pour tous', 'Urgence solidaire']

export const countries = ['France', 'Belgique', 'Suisse', 'Luxembourg', 'Canada']
