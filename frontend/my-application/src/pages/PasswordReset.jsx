import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function PasswordReset() {
  const [email, setEmail] = useState(""); const [token, setToken] = useState(""); const [password, setPassword] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function request(event) { event.preventDefault(); setError(""); try { const result = await api.post("/auth/forgot-password", { email }); if (result.development_reset_token) setToken(result.development_reset_token); setMessage(result.message); } catch (err) { setError(err.message); } }
  async function reset(event) { event.preventDefault(); setError(""); try { const result = await api.post("/auth/reset-password", { token, password }); setMessage(result.message); setToken(""); setPassword(""); } catch (err) { setError(err.message); } }
  return <main className="auth-page"><div className="auth-card"><h1>Password reset</h1><p>Request a short-lived reset token, then choose a new password.</p><form onSubmit={request}><label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><button className="st-primary-btn">Request reset token</button></form><form onSubmit={reset}><label>Reset token<input required value={token} onChange={(e) => setToken(e.target.value)} /></label><label>New password<input type="password" minLength={10} maxLength={128} required value={password} onChange={(e) => setPassword(e.target.value)} /></label><button className="st-primary-btn">Set new password</button></form>{message && <p role="status">{message}</p>}{error && <p className="auth-error" role="alert">{error}</p>}<Link to="/login">Back to sign in</Link></div></main>;
}
