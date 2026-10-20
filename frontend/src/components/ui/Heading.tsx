import type { ReactNode } from 'react'

type HeadingProps = {
  children: ReactNode
  className?: string
}

export default function Heading({ children, className = '' }: HeadingProps) {
  return <h2 className={`font-heading text-4xl leading-tight font-medium tracking-tight sm:text-5xl ${className}`}>{children}</h2>
}
