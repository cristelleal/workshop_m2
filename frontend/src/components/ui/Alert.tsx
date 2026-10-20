import { CircleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

export default function Alert({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div role="alert" className="flex gap-3 rounded-lg border border-danger/20 bg-danger/5 p-4 text-sm">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-danger" />
      <div>
        <p className="font-medium text-danger">{title}</p>
        <p className="mt-1 text-muted">{children}</p>
      </div>
    </div>
  )
}
