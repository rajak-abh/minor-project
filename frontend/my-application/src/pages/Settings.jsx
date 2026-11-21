import { useEffect, useState } from "react";
import api from "../api";

const defaults = { notifications_enabled: true, weekly_report: true, compact_mode: false };

export default function Settings() {
  const [settings, setSettings] = useState(defaults); const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { void api.get("/students/me/preferences").then(setSettings).catch((err) => setError(err.message)); }, []);
  useEffect(() => { document.body.classList.toggle("st-compact-mode", settings.compact_mode); return () => document.body.classList.remove("st-compact-mode"); }, [settings.compact_mode]);
  async function save(event) { event.preventDefault(); setBusy(true); setError(""); setMessage(""); try { const stored = await api.put("/students/me/preferences", settings); setSettings(stored); setMessage("Preferences saved to your account."); } catch (err) { setError(err.message); } finally { setBusy(false); } }
  async function reset() { setSettings(defaults); try { await api.put("/students/me/preferences", defaults); setMessage("Preferences reset."); } catch (err) { setError(err.message); } }
  function toggle(key) { setSettings((current) => ({ ...current, [key]: !current[key] })); }
  return <section className="st-page"><header className="st-page-header"><div><h1>Settings</h1><p>Preferences are saved with your account.</p></div></header>{error && <p role="alert">{error}</p>}
    <form className="st-card st-settings-card" onSubmit={save}><label className="st-toggle-row"><span><strong>Application notifications</strong><small>Receive updates related to applications.</small></span><input type="checkbox" checked={settings.notifications_enabled} onChange={() => toggle("notifications_enabled")} /></label><label className="st-toggle-row"><span><strong>Weekly report</strong><small>Enable weekly progress summaries.</small></span><input type="checkbox" checked={settings.weekly_report} onChange={() => toggle("weekly_report")} /></label><label className="st-toggle-row"><span><strong>Compact mode</strong><small>Reduce spacing on dashboard pages.</small></span><input type="checkbox" checked={settings.compact_mode} onChange={() => toggle("compact_mode")} /></label><div className="st-settings-actions"><button className="st-primary-btn" disabled={busy}>{busy ? "Saving…" : "Save preferences"}</button><button type="button" className="st-secondary-btn" onClick={reset}>Reset</button></div>{message && <p role="status">{message}</p>}</form>
  </section>;
}
