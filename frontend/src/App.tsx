import { BrowserRouter, Route, Routes } from 'react-router'
import Layout from './components/layout/Layout'
import ScrollToTop from './components/layout/ScrollToTop'
import DonationProvider from './context/DonationProvider'
import DonationAmountPage from './pages/DonationAmountPage'
import DonationConfirmationPage from './pages/DonationConfirmationPage'
import DonationPaymentPage from './pages/DonationPaymentPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <DonationProvider>
        <Routes>
          <Route
            path="/"
            element={
              <Layout>
                <HomePage />
              </Layout>
            }
          />
          <Route path="/connexion" element={<LoginPage />} />
          <Route path="/don" element={<DonationAmountPage />} />
          <Route path="/don/paiement" element={<DonationPaymentPage />} />
          <Route path="/don/confirmation" element={<DonationConfirmationPage />} />
        </Routes>
      </DonationProvider>
    </BrowserRouter>
  )
}
