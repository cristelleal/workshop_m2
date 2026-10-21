import type { Frequency } from '../context/DonationContext'
import type { Presets } from '../services/donations'

// Valeurs de secours, identiques à GET /donations/presets, si l'API ne répond pas.
export const defaultPresets: Presets = { amounts: [5, 10, 25, 50], min: 1, max: 10_000 }

export const frequencies: { value: Frequency; label: string }[] = [
  { value: 'once', label: 'Une fois' },
  { value: 'monthly', label: 'Chaque mois' },
]

export const allocations = ['Toutes nos actions', 'Cartables pour tous', 'Urgence solidaire']

export const countries = ['France', 'Belgique', 'Suisse', 'Luxembourg', 'Canada']
