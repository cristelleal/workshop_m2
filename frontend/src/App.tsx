import { BrowserRouter, Route, Routes } from 'react-router'
import RequireAuth from './components/auth/RequireAuth'
import Layout from './components/layout/Layout'
import ScrollToTop from './components/layout/ScrollToTop'
import AuthProvider from './context/AuthProvider'
import DonationProvider from './context/DonationProvider'
import AccountPage from './pages/AccountPage'
import DonationAmountPage from './pages/DonationAmountPage'
import DonationConfirmationPage from './pages/DonationConfirmationPage'
import DonationPaymentPage from './pages/DonationPaymentPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <AuthProvider>
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
            <Route path="/inscription" element={<RegisterPage />} />

            {/* Pages réservées aux donateurs connectés (l'API exige un token) */}
            <Route path="/don" element={<RequireAuth><DonationAmountPage /></RequireAuth>} />
            <Route path="/don/paiement" element={<RequireAuth><DonationPaymentPage /></RequireAuth>} />
            <Route path="/don/confirmation/:id" element={<RequireAuth><DonationConfirmationPage /></RequireAuth>} />
            <Route path="/espace" element={<RequireAuth><AccountPage /></RequireAuth>} />
          </Routes>
        </DonationProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
