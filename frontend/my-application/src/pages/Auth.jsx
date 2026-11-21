import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

export default function Auth({ mode = "login", onAuthenticated }) {
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "student", company_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const register = mode === "register";

  async function submit(event) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const result = await api.post(register ? "/auth/register" : "/auth/login", form);
      localStorage.setItem("skilltrack-access-token", result.access_token);
      localStorage.setItem("skilltrack-refresh-token", result.refresh_token);
      const user = await api.get("/auth/me");
      onAuthenticated(user);
      navigate(user.role === "company" ? "/company" : user.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <main className="auth-page"><form className="auth-card" onSubmit={submit}>
    <h1>SkillTrack</h1><p>{register ? "Create your account" : "Sign in to continue"}</p>
    {register && <><label>Account type<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="student">Student</option><option value="company">Company</option></select></label>
      <label>{form.role === "company" ? "Company name" : "Full name"}<input required value={form.role === "company" ? form.company_name : form.full_name} onChange={(e) => setForm({ ...form, [form.role === "company" ? "company_name" : "full_name"]: e.target.value })} /></label></>}
    <label>Email<input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
    <label>Password<input type="password" autoComplete={register ? "new-password" : "current-password"} minLength={register ? 10 : 1} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
    {error && <p className="auth-error" role="alert">{error}</p>}
    <button className="st-primary-btn" disabled={busy}>{busy ? "Please wait…" : register ? "Create account" : "Sign in"}</button>
    <p>{register ? "Already registered?" : "New to SkillTrack?"} <Link to={register ? "/login" : "/register"}>{register ? "Sign in" : "Create an account"}</Link></p>
    {!register && <Link to="/forgot-password">Forgot your password?</Link>}
  </form></main>;
}
