import { useEffect, useState } from "react";
import api from "../api";

export default function Skills() {
  const [skills, setSkills] = useState([]); const [name, setName] = useState(""); const [category, setCategory] = useState("Technical"); const [proficiency, setProficiency] = useState(50); const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  async function load() { try { setSkills(await api.get("/students/me/skills")); } catch (err) { setError(err.message); } }
  useEffect(() => { void api.get("/students/me/skills").then(setSkills).catch((err) => setError(err.message)); }, []);
  async function add(event) { event.preventDefault(); setError(""); setMessage(""); setBusy(true); try { await api.post("/students/me/skills", { name, category, proficiency: Number(proficiency) }); setName(""); await load(); setMessage("Skill saved to your account."); } catch (err) { setError(err.message); } finally { setBusy(false); } }
  async function remove(id) { try { await api.delete(`/students/me/skills/${id}`); setSkills((items) => items.filter((item) => item.id !== id)); } catch (err) { setError(err.message); } }
  return <section className="st-page"><header className="st-page-header"><div><h1>My Skills</h1><p>Skills are stored in your profile and used for matching internships.</p></div></header>{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form className="st-card st-skill-form" onSubmit={add}><h2>Add a skill</h2><input placeholder="Skill name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} /><select value={category} onChange={(e) => setCategory(e.target.value)}><option>Technical</option><option>Framework</option><option>Database</option><option>Tool</option><option>Soft Skill</option></select><label>Proficiency: {proficiency}%</label><input type="range" min="0" max="100" value={proficiency} onChange={(e) => setProficiency(e.target.value)} /><button className="st-primary-btn" disabled={busy}>{busy ? "Saving…" : "Add skill"}</button></form>
    {!skills.length ? <div className="st-card">No skills saved yet. Add your first skill above.</div> : <div className="st-skill-grid">{skills.map((skill) => <article className="st-card st-skill-card" key={skill.id}><div className="st-skill-heading"><div><h3>{skill.name}</h3><span className="st-muted">{skill.category}</span></div><strong>{skill.proficiency}%</strong></div><div className="st-progress-track"><div className="st-progress-fill" style={{ width: `${skill.proficiency}%` }} /></div><button className="st-delete-btn" onClick={() => remove(skill.id)}>Remove</button></article>)}</div>}
  </section>;
}
