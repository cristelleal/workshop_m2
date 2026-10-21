import type { Frequency } from '../context/DonationContext'
import { postJson, request } from './api'

export type DonationStatus = 'pending' | 'succeeded' | 'failed'

export type DonationRecord = {
  id: string
  amount: number
  frequency: Frequency
  status: DonationStatus
  cardLast4: string | null
  failureReason: string | null
  date: Date
}

export type Presets = {
  amounts: number[]
  min: number
  max: number
}

type DonationResponse = {
  id: string
  amount_cents: number
  frequency: Frequency
  status: DonationStatus
  card_last4: string | null
  failure_reason: string | null
  created_at: string
  processed_at: string | null
}

type PresetsResponse = {
  presets_cents: number[]
  min_cents: number
  max_cents: number
}

// L'API compte en centimes, le front en euros : la conversion se fait uniquement ici.
const toEuros = (cents: number) => cents / 100

const toDonation = (donation: DonationResponse): DonationRecord => ({
  id: donation.id,
  amount: toEuros(donation.amount_cents),
  frequency: donation.frequency,
  status: donation.status,
  cardLast4: donation.card_last4,
  failureReason: donation.failure_reason,
  date: new Date(donation.processed_at ?? donation.created_at),
})

export async function getPresets(): Promise<Presets> {
  const presets = await request<PresetsResponse>('/donations/presets')
  return { amounts: presets.presets_cents.map(toEuros), min: toEuros(presets.min_cents), max: toEuros(presets.max_cents) }
}

export async function createDonation(amount: number, frequency: Frequency, cardNumber: string) {
  const donation = await postJson<DonationResponse>('/donations', {
    amount_cents: Math.round(amount * 100),
    frequency,
    card_number: cardNumber,
  })
  return toDonation(donation)
}

export const getMyDonations = async () => (await request<DonationResponse[]>('/donations/me')).map(toDonation)

export const getDonation = async (id: string) => toDonation(await request<DonationResponse>(`/donations/${id}`))
