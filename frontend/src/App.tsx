import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { AppShell } from './components/AppShell'
import { ErrorBoundary, ToastProvider } from './components/Ui'
import {
  AmbulanceOperatorPage,
  AmbulancesPage,
  AnalyticsPage,
  AuthPage,
  DashboardPage,
  DispatchPage,
  DsaLabPage,
  EmergenciesPage,
  HospitalOperatorPage,
  HospitalsPage,
  LandingPage,
  MapPage,
  NotFoundPage,
  ProfilePage,
  PublicSosPage,
  SettingsPage,
  SosTrackingPage,
} from './pages/Pages'

function RequireAuth() {
  const { user } = useAuth()
  const location = useLocation()
  return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />
}

function ApplicationRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/sos" element={<PublicSosPage />} />
        <Route path="/sos/track/:id" element={<SosTrackingPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="emergencies" element={<EmergenciesPage />} />
            <Route path="map" element={<MapPage />} />
            <Route path="ambulances" element={<AmbulancesPage />} />
            <Route path="hospitals" element={<HospitalsPage />} />
            <Route path="dispatch" element={<DispatchPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="dsa" element={<DsaLabPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="/operator/ambulance" element={<AppShell />}><Route index element={<AmbulanceOperatorPage />} /></Route>
          <Route path="/operator/hospital" element={<AppShell />}><Route index element={<HospitalOperatorPage />} /></Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}

function App() {
  useEffect(() => {
    document.documentElement.dataset.theme = localStorage.getItem('resqnet.theme') ?? 'dark'
    document.documentElement.dataset.compact = localStorage.getItem('resqnet.compact') ?? 'false'
  }, [])
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <ApplicationRoutes />
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
