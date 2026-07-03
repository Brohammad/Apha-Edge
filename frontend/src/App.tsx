import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import StrategiesPage from './pages/StrategiesPage'
import StrategyDetailPage from './pages/StrategyDetailPage'
import BacktestsPage from './pages/BacktestsPage'
import BacktestDetailPage from './pages/BacktestDetailPage'
import OptimizationsPage from './pages/OptimizationsPage'
import OptimizationDetailPage from './pages/OptimizationDetailPage'
import PortfoliosPage from './pages/PortfoliosPage'
import PortfolioDetailPage from './pages/PortfolioDetailPage'
import OrdersPage from './pages/OrdersPage'
import InsightsPage from './pages/InsightsPage'
import InsightDetailPage from './pages/InsightDetailPage'
import MarketplacePage from './pages/MarketplacePage'
import OrganizationsPage from './pages/OrganizationsPage'
import OAuthCallbackPage from './pages/OAuthCallbackPage'
import VerifyEmailPage from './pages/VerifyEmailPage'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="font-mono text-sm text-ink-300">Booting terminal…</div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/strategies" element={<StrategiesPage />} />
        <Route path="/strategies/:strategyId" element={<StrategyDetailPage />} />
        <Route path="/backtests" element={<BacktestsPage />} />
        <Route path="/backtests/:runId" element={<BacktestDetailPage />} />
        <Route path="/optimizations" element={<OptimizationsPage />} />
        <Route path="/optimizations/:runId" element={<OptimizationDetailPage />} />
        <Route path="/portfolios" element={<PortfoliosPage />} />
        <Route path="/portfolios/:portfolioId" element={<PortfolioDetailPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/insights/:insightId" element={<InsightDetailPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/organizations" element={<OrganizationsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
