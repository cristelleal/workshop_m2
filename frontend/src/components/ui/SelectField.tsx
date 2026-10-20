import { useId, type SelectHTMLAttributes } from 'react'
import Field, { inputClass } from './Field'

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  options: string[]
}

export default function SelectField({ label, options, ...props }: SelectFieldProps) {
  const id = useId()

  return (
    <Field id={id} label={label}>
      <select id={id} className={`${inputClass} border-line`} {...props}>
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </Field>
  )
}
