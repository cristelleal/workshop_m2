import Container from '../ui/Container'
import Eyebrow from '../ui/Eyebrow'

export default function Testimonial() {
  return (
    <section id="temoignages">
      <Container className="max-w-3xl py-28 text-center">
        <span aria-hidden className="font-serif text-5xl leading-none font-bold text-primary">
          “
        </span>
        <blockquote className="mx-auto mt-8 max-w-2xl text-3xl leading-snug font-medium tracking-tight sm:text-4xl">
          Grâce à mon don mensuel, une classe entière a reçu ses fournitures pour la rentrée. Je vois enfin où va mon argent.
        </blockquote>
        <div className="mt-6">
          <Eyebrow>Julien, donateur depuis 2021</Eyebrow>
        </div>
      </Container>
    </section>
  )
}
