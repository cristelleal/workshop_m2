import type { ReactNode } from 'react'

export type Detail = { label: string; value: ReactNode }

type DetailListProps = {
  items: Detail[]
  className?: string
}

export default function DetailList({ items, className = '' }: DetailListProps) {
  return (
    <dl className={`divide-y divide-line ${className}`}>
      {items.map((item) => (
        <div key={item.label} className="flex justify-between gap-4 py-3">
          <dt className="text-muted">{item.label}</dt>
          <dd className="text-right">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
