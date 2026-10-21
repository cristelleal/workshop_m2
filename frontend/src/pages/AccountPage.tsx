import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import Header from '../components/layout/Header'
import Button from '../components/ui/Button'
import Container from '../components/ui/Container'
import Eyebrow from '../components/ui/Eyebrow'
import Heading from '../components/ui/Heading'
import Reveal from '../components/ui/Reveal'
import { useAuth } from '../context/AuthContext'
import { getMyDonations, type DonationRecord, type DonationStatus } from '../services/donations'
import { formatDate, formatEuro } from '../utils/format'

const statusLabels: Record<DonationStatus, string> = {
  succeeded: 'Confirmé',
  failed: 'Refusé',
  pending: 'En cours',
}

export default function AccountPage() {
  const { user, signOut } = useAuth()
  const [donations, setDonations] = useState<DonationRecord[] | null>(null)

  useEffect(() => {
    getMyDonations()
      .then(setDonations)
      .catch(() => setDonations([]))
  }, [])

  return (
    <>
      <Header minimal />
      <main>
        <Reveal>
          <Container className="max-w-xl py-20">
            <div className="flex items-center justify-between">
              <Eyebrow>Espace donateur</Eyebrow>
              <button type="button" onClick={signOut} className="text-sm text-muted hover:text-ink">
                Se déconnecter
              </button>
            </div>
            <Heading as="h1" className="mt-4">
              Mes dons
            </Heading>
            <p className="mt-4 mb-10 text-muted">Connecté avec {user?.email}</p>

            {donations?.length === 0 && <p className="text-muted">Vous n'avez pas encore fait de don.</p>}
            {donations && donations.length > 0 && (
              <ul className="divide-y divide-line border-y border-line">
                {donations.map((donation) => {
                  const row = (
                    <>
                      <span>
                        {formatEuro(donation.amount)}
                        {donation.frequency === 'monthly' && ' / mois'}
                        <span className="block text-sm text-muted">{formatDate(donation.date)}</span>
                      </span>
                      <span className={`text-sm ${donation.status === 'failed' ? 'text-danger' : 'text-muted'}`}>
                        {statusLabels[donation.status]}
                      </span>
                    </>
                  )
                  const rowClass = 'flex items-center justify-between gap-4 py-4'

                  return (
                    <li key={donation.id}>
                      {donation.status === 'succeeded' ? (
                        <Link to={`/don/confirmation/${donation.id}`} className={`${rowClass} hover:text-primary`}>
                          {row}
                        </Link>
                      ) : (
                        <div className={rowClass}>{row}</div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}

            <Button to="/don" className="mt-8 w-full">
              Faire un don
            </Button>
          </Container>
        </Reveal>
      </main>
    </>
  )
}
