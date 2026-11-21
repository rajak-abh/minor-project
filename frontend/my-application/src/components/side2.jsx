import { NavLink } from "react-router-dom";

const menuItems = [
  { label: "Dashboard", path: "/dashboard" }, { label: "My Profile", path: "/profile" },
  { label: "Internships", path: "/internships" }, { label: "Projects", path: "/projects" },
  { label: "Certifications", path: "/certifications" }, { label: "Skills", path: "/skills" },
  { label: "Mock Interviews", path: "/mock-interviews" }, { label: "Assessments", path: "/assessments" }, { label: "Performance", path: "/performance" },
];
const linkStyle = ({ isActive }) => ({ display: "block", padding: "10px 12px", borderRadius: "8px", color: "white", textDecoration: "none", backgroundColor: isActive ? "#1f2937" : "transparent" });

export default function Sidebar({ user, onSignOut }) {
  const items = user?.role === "company" ? [{ label: "Company Dashboard", path: "/company" }] : user?.role === "admin" ? [{ label: "Admin Dashboard", path: "/admin" }] : menuItems;
  return <aside className="skilltrack-sidebar" style={{ width: 250, height: "100vh", backgroundColor: "#111827", color: "white", position: "fixed", left: 0, top: 0, padding: "25px 18px", zIndex: 9999 }}>
    <h2>SkillTrack</h2><small>{user?.email}</small>
    <nav style={{ marginTop: 30 }}>{items.map((item) => <NavLink key={item.path} to={item.path} style={linkStyle}>{item.label}</NavLink>)}</nav>
    {user?.role === "student" && <NavLink to="/settings" style={linkStyle}>Settings</NavLink>}
    <button type="button" className="sidebar-signout" onClick={onSignOut}>Sign out</button>
  </aside>;
}
