import type { ReactNode } from 'react'
import Container from '../ui/Container'
import Reveal from '../ui/Reveal'
import Header from './Header'

type CheckoutLayoutProps = {
  children: ReactNode
  summary: ReactNode
}

export default function CheckoutLayout({ children, summary }: CheckoutLayoutProps) {
  return (
    <>
      <Header minimal />
      <main>
        <Reveal>
          <Container className="grid items-start gap-10 py-20 lg:grid-cols-[1fr_22rem] lg:gap-16">
            <div className="w-full max-w-xl">{children}</div>
            <aside className="rounded-2xl bg-sand p-8 lg:sticky lg:top-8">{summary}</aside>
          </Container>
        </Reveal>
      </main>
    </>
  )
}
