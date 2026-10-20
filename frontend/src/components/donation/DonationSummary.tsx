import { useDonation } from '../../context/DonationContext'
import { formatEuro } from '../../utils/format'
import DetailList, { type Detail } from '../ui/DetailList'
import Eyebrow from '../ui/Eyebrow'

type DonationSummaryProps = {
  items: Detail[]
  total?: number
  note: string
}

export default function DonationSummary({ items, total, note }: DonationSummaryProps) {
  const { donation } = useDonation()

  return (
    <>
      <Eyebrow>Récapitulatif</Eyebrow>
      <p className="mt-3 font-heading text-4xl font-medium tracking-tight">
        {formatEuro(donation.amount)}
        {donation.frequency === 'monthly' && <span className="font-sans text-base text-muted"> / mois</span>}
      </p>

      <DetailList items={items} className="mt-6 border-t border-line text-sm" />
      {total !== undefined && (
        <div className="flex justify-between border-y border-ink py-3 text-sm font-medium">
          <span>Total aujourd'hui</span>
          <span>{formatEuro(total)}</span>
        </div>
      )}

      <p className="mt-6 text-sm text-muted">{note}</p>
    </>
  )
}
