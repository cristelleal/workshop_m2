import type { ReactNode } from 'react'

type HeadingProps = {
  children: ReactNode
  as?: 'h1' | 'h2'
  className?: string
}

export default function Heading({ children, as: Tag = 'h2', className = '' }: HeadingProps) {
  return (
    <Tag className={`font-heading text-4xl leading-tight font-medium tracking-tight sm:text-5xl ${className}`}>
      {children}
    </Tag>
  )
}
