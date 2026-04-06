import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import Login from "./pages/Login";

// Lazy load pages for bundle optimization
import { lazy, Suspense } from "react";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const IncomeExpenses = lazy(() => import("./pages/IncomeExpenses"));
const FireSettings = lazy(() => import("./pages/FireSettings"));
const FundAllocation = lazy(() => import("./pages/FundAllocation"));
const GrowthProjection = lazy(() => import("./pages/GrowthProjection"));
const RetirementAnalysis = lazy(() => import("./pages/RetirementAnalysis"));
const SipTracker = lazy(() => import("./pages/SipTracker"));
const PreciousMetals = lazy(() => import("./pages/PreciousMetals"));
const SettingsPrivacy = lazy(() => import("./pages/SettingsPrivacy"));
const Projects = lazy(() => import("./pages/Projects"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function LoginRoute() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <Login />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
        <Suspense
          fallback={
            <div className="min-h-screen bg-[#0D1B2A] flex items-center justify-center text-[#E8ECF1]">
              Loading...
            </div>
          }
        >
          <Routes>
            <Route
              path="/login"
              element={<LoginRoute />}
            />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/income-expenses"
              element={
                <ProtectedRoute>
                  <IncomeExpenses />
                </ProtectedRoute>
              }
            />
            <Route
              path="/fire-settings"
              element={
                <ProtectedRoute>
                  <FireSettings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/fund-allocation"
              element={
                <ProtectedRoute>
                  <FundAllocation />
                </ProtectedRoute>
              }
            />
            <Route
              path="/growth-projection"
              element={
                <ProtectedRoute>
                  <GrowthProjection />
                </ProtectedRoute>
              }
            />
            <Route
              path="/retirement-analysis"
              element={
                <ProtectedRoute>
                  <RetirementAnalysis />
                </ProtectedRoute>
              }
            />
            <Route
              path="/sip-tracker"
              element={
                <ProtectedRoute>
                  <SipTracker />
                </ProtectedRoute>
              }
            />
            <Route
              path="/precious-metals"
              element={
                <ProtectedRoute>
                  <PreciousMetals />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings-privacy"
              element={
                <ProtectedRoute>
                  <SettingsPrivacy />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects"
              element={
                <ProtectedRoute>
                  <Projects />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
