import { useEffect, useState } from "react";
import api from "../api";

export default function AdminDashboard() {
  const [activity, setActivity] = useState(null); const [users, setUsers] = useState([]); const [jobs, setJobs] = useState([]); const [error, setError] = useState("");
  async function load() { try { const [a, u, j] = await Promise.all([api.get("/admin/activity"), api.get("/admin/users"), api.get("/admin/internships")]); setActivity(a); setUsers(u); setJobs(j); } catch (err) { setError(err.message); } }
  useEffect(() => { void Promise.all([api.get("/admin/activity"), api.get("/admin/users"), api.get("/admin/internships")]).then(([a, u, j]) => { setActivity(a); setUsers(u); setJobs(j); }).catch((err) => setError(err.message)); }, []);
  async function toggleUser(user) { try { await api.patch(`/admin/users/${user.id}/active`, { is_active: !user.is_active }); await load(); } catch (err) { setError(err.message); } }
  async function toggleJob(job) { try { await api.patch(`/admin/internships/${job.id}/active`, { is_active: !job.is_active }); await load(); } catch (err) { setError(err.message); } }
  return <section className="st-page"><header className="st-page-header"><div><h1>Admin Dashboard</h1><p>Platform users, internship postings, and activity.</p></div></header>{error && <p role="alert">{error}</p>}
    {activity && <div className="st-stats-grid">{Object.entries(activity).map(([key, count]) => <article className="st-card" key={key}><span>{key}</span><h2>{count}</h2></article>)}</div>}
    <div className="st-card"><h2>Users</h2>{users.map((user) => <article className="st-history-item" key={user.id}><strong>{user.name || user.email}</strong><p>{user.email} · {user.role} · {user.is_active ? "Active" : "Disabled"}</p><button className="st-secondary-btn" onClick={() => toggleUser(user)}>{user.is_active ? "Disable" : "Enable"} account</button></article>)}</div>
    <div className="st-card"><h2>Internships</h2>{jobs.map((job) => <article className="st-history-item" key={job.id}><strong>{job.title}</strong><p>{job.company} · {job.applications} applications · {job.is_active ? "Active" : "Closed"}</p><button className="st-secondary-btn" onClick={() => toggleJob(job)}>{job.is_active ? "Close" : "Reopen"}</button></article>)}</div>
  </section>;
}
