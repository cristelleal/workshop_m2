import type { ReactNode } from 'react'

type CardProps = {
  children: ReactNode
  className?: string
}

export default function Card({ children, className = '' }: CardProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-3 sm:px-4">
      <div className={`rounded-2xl ${className}`}>{children}</div>
    </div>
  )
}
