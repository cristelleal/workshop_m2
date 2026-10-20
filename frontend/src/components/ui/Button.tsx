import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'inverse'
type Size = 'sm' | 'md'

type ButtonProps = { variant?: Variant; size?: Size } & (
  | (AnchorHTMLAttributes<HTMLAnchorElement> & { href: string })
  | ButtonHTMLAttributes<HTMLButtonElement>
)

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary/90',
  secondary: 'bg-sand text-ink hover:bg-line',
  inverse: 'bg-white text-primary hover:bg-sand',
}

const sizes: Record<Size, string> = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-base',
}

export default function Button({ variant = 'primary', size = 'md', className = '', ...props }: ButtonProps) {
  const classes = `inline-flex items-center justify-center rounded-lg font-medium transition active:scale-[0.98] ${variants[variant]} ${sizes[size]} ${className}`

  if ('href' in props) return <a className={classes} {...props} />
  return <button className={classes} {...props} />
}
