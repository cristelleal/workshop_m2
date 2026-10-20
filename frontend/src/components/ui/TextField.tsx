import { useId, type InputHTMLAttributes, type ReactNode } from 'react'

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  action?: ReactNode
  suffix?: ReactNode
}

export default function TextField({ label, action, suffix, ...props }: TextFieldProps) {
  const id = useId()

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between text-sm">
        <label htmlFor={id}>{label}</label>
        {action}
      </div>
      <div className="relative">
        <input
          id={id}
          className="w-full rounded-lg border border-line bg-white px-4 py-3 transition outline-none focus:border-primary"
          {...props}
        />
        {suffix && <div className="absolute inset-y-0 right-4 flex items-center text-sm">{suffix}</div>}
      </div>
    </div>
  )
}
