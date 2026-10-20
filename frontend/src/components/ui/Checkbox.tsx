import type { InputHTMLAttributes } from 'react'

type CheckboxProps = InputHTMLAttributes<HTMLInputElement> & { label: string }

export default function Checkbox({ label, ...props }: CheckboxProps) {
  return (
    <label className="flex items-center gap-3 text-sm">
      <input type="checkbox" className="size-4 accent-primary" {...props} />
      {label}
    </label>
  )
}
