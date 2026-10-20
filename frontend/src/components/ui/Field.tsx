import type { ReactNode } from 'react'

export const inputClass = 'w-full rounded-lg border bg-white px-4 py-3 transition outline-none focus:border-primary'

type FieldProps = {
  id: string
  label: string
  error?: string
  children: ReactNode
}

export default function Field({ id, label, error, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm">
        {label}
      </label>
      {children}
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  )
}
