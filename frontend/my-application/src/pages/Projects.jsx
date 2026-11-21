import { useEffect, useState } from "react";
import api from "../api";

export default function Projects() {
  const [items, setItems] = useState([]); const [form, setForm] = useState({ name: "", description: "", technologies: "", url: "" }); const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  async function load() { try { setItems(await api.get("/students/me/projects")); } catch (err) { setError(err.message); } }
  useEffect(() => { void api.get("/students/me/projects").then(setItems).catch((err) => setError(err.message)); }, []);
  async function add(event) { event.preventDefault(); setError(""); setMessage(""); setBusy(true); try { await api.post("/students/me/projects", { ...form, technologies: form.technologies.split(",").map((value) => value.trim()).filter(Boolean) }); setForm({ name: "", description: "", technologies: "", url: "" }); await load(); setMessage("Project saved to your account."); } catch (err) { setError(err.message); } finally { setBusy(false); } }
  async function remove(id) { try { await api.delete(`/students/me/projects/${id}`); setItems((old) => old.filter((item) => item.id !== id)); } catch (err) { setError(err.message); } }
  return <section className="st-page"><header className="st-page-header"><div><h1>My Projects</h1><p>Manage the projects saved in your profile.</p></div></header>{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form className="st-card st-project-form" onSubmit={add}><h2>Add project</h2><input required placeholder="Project name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /><textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /><input placeholder="Technologies, comma separated" value={form.technologies} onChange={(e) => setForm({ ...form, technologies: e.target.value })} /><input type="url" placeholder="Project URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /><button className="st-primary-btn" disabled={busy}>{busy ? "Saving…" : "Save project"}</button></form>
    {items.length ? <div className="st-project-grid">{items.map((item) => <article className="st-card" key={item.id}><h2>{item.name}</h2><p>{item.description}</p><div className="st-tags">{item.technologies.map((tech) => <span key={tech}>{tech}</span>)}</div>{item.url && <a href={item.url} target="_blank" rel="noreferrer">View project</a>}<p><button className="st-delete-btn" onClick={() => remove(item.id)}>Delete</button></p></article>)}</div> : <div className="st-card">No projects saved yet.</div>}
  </section>;
}
