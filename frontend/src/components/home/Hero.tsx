import { BadgeCheck } from 'lucide-react'
import heroImage from '../../assets/homepage-img.webp'
import Button from '../ui/Button'
import Card from '../ui/Card'
import Container from '../ui/Container'
import Eyebrow from '../ui/Eyebrow'

export default function Hero() {
  return (
    <section>
      <Container className="max-w-3xl py-20 text-center sm:py-28">
        <Eyebrow>Soutenir 12 000 personnes chaque année</Eyebrow>
        <h1 className="mx-auto font-heading mt-6 max-w-2xl text-5xl leading-[0.95] font-medium tracking-tighter sm:text-7xl">
          Chaque don compte. Donnez en quelques secondes.
        </h1>
        <p className="mx-auto mt-6 max-w-md text-muted">
          Dons ponctuels ou mensuels, paiement sécurisé et reçu fiscal automatique. Votre soutien est utilisé là où il
          est le plus utile.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          <Button href="#don">Faire un don</Button>
          <Button href="#don" variant="secondary">
            Devenir donateur mensuel
          </Button>
        </div>
      </Container>

      <Card className="relative overflow-hidden bg-stone">
        <img
          src={heroImage}
          alt="Bénéficiaires de l'association sur le terrain"
          className="aspect-4/3 w-full object-cover transition duration-700 hover:scale-102 sm:aspect-16/8"
        />
        <p className="absolute bottom-6 left-6 flex items-center gap-2 rounded-lg bg-sand px-4 py-2.5 text-sm">
          <BadgeCheck className="size-4 text-primary" />
          Reçu fiscal envoyé automatiquement
        </p>
      </Card>
    </section>
  )
}
