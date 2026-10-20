import type { ReactNode } from 'react'

export default function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="font-mono text-xs tracking-wide text-muted uppercase">{children}</p>
}
