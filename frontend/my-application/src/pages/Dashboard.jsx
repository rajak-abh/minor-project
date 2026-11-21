import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api";

export default function Dashboard() {
  const [analytics, setAnalytics] = useState(null); const [recommendations, setRecommendations] = useState([]); const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.get("/analytics/student"), api.get("/recommendations")]).then(([stats, recs]) => { setAnalytics(stats); setRecommendations(recs.slice(0, 4)); }).catch((err) => setError(err.message)); }, []);
  return <main className="st-page"><header className="st-page-header"><div><h1>Dashboard</h1><p>Your progress and internship recommendations.</p></div></header>
    {error && <div className="st-card" role="alert">{error} — check that the API server is running.</div>}
    {!analytics && !error ? <p>Loading dashboard…</p> : analytics && <>
      <div className="st-stats-grid">{[["Skills", analytics.total_skills], ["Projects", analytics.total_projects], ["Profile completion", `${analytics.profile_completion}%`], ["Applications", analytics.total_applications], ["Shortlisted", analytics.shortlisted_applications], ["Assessment average", `${analytics.assessment_average}%`]].map(([label, value]) => <article className="st-card" key={label}><span>{label}</span><h2>{value}</h2></article>)}</div>
      <div className="st-card"><h2>Application progress</h2><div style={{ height: 260 }}><ResponsiveContainer width="100%" height="100%"><BarChart data={Object.entries(analytics.application_statuses).map(([status, count]) => ({ status, count }))}><CartesianGrid strokeDasharray="3 3" stroke="#344054" /><XAxis dataKey="status" stroke="#aab5c8" /><YAxis allowDecimals={false} stroke="#aab5c8" /><Tooltip /><Bar dataKey="count" fill="#818cf8" /></BarChart></ResponsiveContainer></div></div>
      <div className="st-card"><h2>Recommended internships</h2>{recommendations.length ? recommendations.map((item) => <article className="st-history-item" key={item.id}><strong>{item.title} · {item.match_percentage}% match</strong><p>{item.company_name} · {item.location || "Location not specified"}</p><p>Matched: {item.matching_skills.join(", ") || "No required skills matched"} · Missing: {item.missing_skills.join(", ") || "None"}</p><Link to="/internships">Browse internships</Link></article>) : <p>No active internships yet. Check back as companies post opportunities.</p>}</div>
    </>}
  </main>;
}
