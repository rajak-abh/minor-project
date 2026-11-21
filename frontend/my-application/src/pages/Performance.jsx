import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api";

export default function Performance() {
  const [history, setHistory] = useState([]); const [analytics, setAnalytics] = useState(null); const [error, setError] = useState("");
  useEffect(() => { void Promise.all([api.get("/assessments/history"), api.get("/analytics/student")]).then(([results, stats]) => { setHistory(results); setAnalytics(stats); }).catch((err) => setError(err.message)); }, []);
  const chart = history.slice(0, 10).reverse().map((item, index) => ({ attempt: `Attempt ${index + 1}`, score: item.score }));
  return <section className="st-page"><header className="st-page-header"><div><h1>Performance</h1><p>Assessment results and application progress from your account.</p></div></header>{error && <p role="alert">{error}</p>}{!analytics ? !error && <p>Loading your results…</p> : <div className="st-stats-grid"><article className="st-card"><span>Assessment average</span><h2>{analytics.assessment_average}%</h2></article><article className="st-card"><span>Completed assessments</span><h2>{history.length}</h2></article><article className="st-card"><span>Selected applications</span><h2>{analytics.selected_applications}</h2></article></div>}
    <div className="st-card"><h2>Assessment scores</h2>{chart.length ? <div style={{ height: 280 }}><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#344054" /><XAxis dataKey="attempt" stroke="#aab5c8" /><YAxis domain={[0, 100]} stroke="#aab5c8" /><Tooltip /><Bar dataKey="score" fill="#818cf8" /></BarChart></ResponsiveContainer></div> : <p>Complete an assessment to start tracking results.</p>}</div>
    <div className="st-card st-history"><h2>Skill wise recommendations</h2>{history.length ? Object.entries(history[0].skill_breakdown).map(([skill, result]) => <p key={skill}>{skill}: {result.correct}/{result.total} correct. {result.correct < result.total ? "Review this topic and try another assessment." : "Strong result. Keep practising."}</p>) : <p>Your next steps will be based on assessment results.</p>}</div>
  </section>;
}
