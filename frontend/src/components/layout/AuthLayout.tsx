import type { ReactNode } from 'react'
import Container from '../ui/Container'
import Eyebrow from '../ui/Eyebrow'
import Heading from '../ui/Heading'
import Reveal from '../ui/Reveal'
import Header from './Header'

type AuthLayoutProps = {
  title: string
  subtitle: ReactNode
  children: ReactNode
}

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <>
      <Header minimal />
      <main>
        <Reveal>
          <Container className="max-w-md py-20">
            <Eyebrow>Espace donateur</Eyebrow>
            <Heading as="h1" className="mt-4">
              {title}
            </Heading>
            <p className="mt-4 mb-10 text-muted">{subtitle}</p>
            {children}
          </Container>
        </Reveal>
      </main>
    </>
  )
}
