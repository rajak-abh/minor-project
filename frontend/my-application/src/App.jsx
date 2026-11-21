import "./App.css";
import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import api from "./api";
import Sidebar from "./components/side2.jsx";
const Auth = lazy(() => import("./pages/Auth.jsx"));
const CompanyDashboard = lazy(() => import("./pages/CompanyDashboard.jsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const Profile = lazy(() => import("./pages/Profile.jsx"));
const Internships = lazy(() => import("./pages/Internships.jsx"));
const Projects = lazy(() => import("./pages/Projects.jsx"));
const Certifications = lazy(() => import("./pages/Certifications.jsx"));
const Skills = lazy(() => import("./pages/Skills.jsx"));
const MockInterviews = lazy(() => import("./pages/MockInterviews.jsx"));
const Performance = lazy(() => import("./pages/Performance.jsx"));
const Settings = lazy(() => import("./pages/Settings.jsx"));
const Assessments = lazy(() => import("./pages/Assessments.jsx"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard.jsx"));
const PasswordReset = lazy(() => import("./pages/PasswordReset.jsx"));

function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(localStorage.getItem("skilltrack-access-token")));
  useEffect(() => {
    if (!checking) return;
    api.get("/auth/me").then(setUser).catch(() => {
      localStorage.removeItem("skilltrack-access-token");
      localStorage.removeItem("skilltrack-refresh-token");
    }).finally(() => setChecking(false));
  }, [checking]);
  useEffect(() => {
    const expireSession = () => setUser(null);
    window.addEventListener("skilltrack:session-expired", expireSession);
    return () => window.removeEventListener("skilltrack:session-expired", expireSession);
  }, []);
  function signOut() {
    const accessToken = localStorage.getItem("skilltrack-access-token");
    const refreshToken = localStorage.getItem("skilltrack-refresh-token");
    api.post("/auth/logout", { refresh_token: refreshToken }, { headers: { Authorization: `Bearer ${accessToken}` } }).catch(() => {});
    localStorage.removeItem("skilltrack-access-token");
    localStorage.removeItem("skilltrack-refresh-token");
    setUser(null);
  }
  if (checking) return <div className="auth-page">Checking your session…</div>;
  const landing = user?.role === "company" ? "/company" : user?.role === "admin" ? "/admin" : "/dashboard";
  const student = (page) => user?.role === "student" ? page : <Navigate to={user ? landing : "/login"} replace />;
  return <BrowserRouter>
    {user && <Sidebar user={user} onSignOut={signOut} />}
    <Suspense fallback={<div className="auth-page">Loading page…</div>}><Routes>
      <Route path="/" element={<Navigate to={user ? landing : "/login"} replace />} />
      <Route path="/login" element={user ? <Navigate to={landing} replace /> : <Auth onAuthenticated={setUser} />} />
      <Route path="/register" element={user ? <Navigate to={landing} replace /> : <Auth mode="register" onAuthenticated={setUser} />} />
      <Route path="/forgot-password" element={user ? <Navigate to={landing} replace /> : <PasswordReset />} />
      <Route path="/company" element={user?.role === "company" ? <CompanyDashboard /> : <Navigate to={user ? landing : "/login"} replace />} />
      <Route path="/admin" element={user?.role === "admin" ? <AdminDashboard /> : <Navigate to={user ? landing : "/login"} replace />} />
      <Route path="/dashboard" element={student(<Dashboard />)} /><Route path="/profile" element={student(<Profile />)} />
      <Route path="/internships" element={student(<Internships />)} /><Route path="/projects" element={student(<Projects />)} />
      <Route path="/certifications" element={student(<Certifications />)} /><Route path="/skills" element={student(<Skills />)} />
      <Route path="/mock-interviews" element={student(<MockInterviews />)} /><Route path="/performance" element={student(<Performance />)} />
      <Route path="/assessments" element={student(<Assessments />)} />
      <Route path="/settings" element={student(<Settings />)} />
      <Route path="*" element={<Navigate to={user ? "/dashboard" : "/login"} replace />} />
    </Routes></Suspense>
  </BrowserRouter>;
}

export default App;
