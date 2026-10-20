import type { AnchorHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'inverse'
type Size = 'sm' | 'md'

type ButtonProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: Variant
  size?: Size
}

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
  return (
    <a
      className={`inline-flex items-center justify-center rounded-lg font-medium transition active:scale-[0.98] ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    />
  )
}
