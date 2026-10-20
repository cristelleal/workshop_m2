import type { ButtonHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router'

type Variant = 'primary' | 'secondary' | 'outline' | 'inverse'
type Size = 'sm' | 'md'

type ButtonProps = { variant?: Variant; size?: Size } & (
  | LinkProps
  | ButtonHTMLAttributes<HTMLButtonElement>
)

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary/90',
  secondary: 'bg-sand text-ink hover:bg-line',
  outline: 'border border-line bg-white text-ink hover:bg-sand',
  inverse: 'bg-white text-primary hover:bg-sand',
}

const sizes: Record<Size, string> = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-base',
}

export default function Button({ variant = 'primary', size = 'md', className = '', ...props }: ButtonProps) {
  const classes = `inline-flex items-center justify-center rounded-lg font-medium transition active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`

  if ('to' in props) return <Link className={classes} {...props} />
  return <button className={classes} {...props} />
}
