import { Navigate, Route, Routes } from "react-router"

import AppLayout from "../components/layout/app-layout"
import CandidatesPage from "../pages/candidates-page"
import DashboardPage from "../pages/dashboard-page"
import JobsPage from "../pages/jobs-page"
import NotFoundPage from "../pages/not-found-page"

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/candidates" element={<CandidatesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}