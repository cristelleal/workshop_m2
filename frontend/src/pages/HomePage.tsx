import CallToAction from '../components/home/CallToAction'
import DonationForm from '../components/home/DonationForm'
import Faq from '../components/home/Faq'
import Features from '../components/home/Features'
import Hero from '../components/home/Hero'
import Partners from '../components/home/Partners'
import Testimonial from '../components/home/Testimonial'
import Transparency from '../components/home/Transparency'
import Reveal from '../components/ui/Reveal'

const sections = [Hero, Partners, Features, Transparency, Testimonial, DonationForm, Faq, CallToAction]

export default function HomePage() {
  return sections.map((Section, index) => (
    <Reveal key={index}>
      <Section />
    </Reveal>
  ))
}
