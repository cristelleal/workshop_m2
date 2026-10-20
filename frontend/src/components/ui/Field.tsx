import type { ReactNode } from 'react'

export const inputClass = 'w-full rounded-lg border bg-white px-4 py-3 transition outline-none focus:border-primary'

type FieldProps = {
  id: string
  label: string
  action?: ReactNode
  error?: string
  children: ReactNode
}

export default function Field({ id, label, action, error, children }: FieldProps) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between text-sm">
        <label htmlFor={id}>{label}</label>
        {action}
      </div>
      {children}
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  )
}
