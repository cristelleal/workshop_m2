import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import Field, { inputClass } from './Field'

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  suffix?: ReactNode
  error?: string
}

export default function TextField({ label, suffix, error, ...props }: TextFieldProps) {
  const id = useId()

  return (
    <Field id={id} label={label} error={error}>
      <div className="relative">
        <input
          id={id}
          aria-invalid={Boolean(error)}
          className={`${inputClass} ${error ? 'border-danger' : 'border-line'}`}
          {...props}
        />
        {suffix && <div className="absolute inset-y-0 right-4 flex items-center text-sm text-muted">{suffix}</div>}
      </div>
    </Field>
  )
}
