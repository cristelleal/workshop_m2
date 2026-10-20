import Button from '../ui/Button'
import Card from '../ui/Card'

export default function CallToAction() {
  return (
    <section className="py-8">
      <Card className="bg-primary-dark px-6 py-20 text-center text-white">
        <h2 className="font-heading text-4xl font-medium tracking-tight sm:text-6xl">Prêt à faire la différence ?</h2>
        <p className="mx-auto mt-4 max-w-sm text-white/80">
          Chaque don, quel que soit son montant, finance des actions concrètes.
        </p>
        <Button href="#don" variant="inverse" className="mt-8">
          Faire un don
        </Button>
      </Card>
    </section>
  )
}
