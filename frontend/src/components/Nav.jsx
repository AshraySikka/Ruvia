import { CalendarDays, HeartHandshake, Mic, Sun, UserRound } from "lucide-react";
import { NavLink } from "react-router-dom";

export default function Nav() {
  const cls = ({ isActive }) => (isActive ? "active" : "");
  return (
    <nav className="nav" aria-label="Main">
      <div className="nav-inner">
        <NavLink to="/" end className={cls}><Sun size={22} />Today</NavLink>
        <NavLink to="/calendar" className={cls}><CalendarDays size={22} />Calendar</NavLink>
        <NavLink to="/chat" className={({ isActive }) => `talk-wrap ${isActive ? "active" : ""}`} aria-label="Talk to Ruvia">
          <span className="talk"><Mic size={24} /></span><span style={{ marginTop: 2 }}>Talk</span>
        </NavLink>
        <NavLink to="/care" className={cls}><HeartHandshake size={22} />Care</NavLink>
        <NavLink to="/me" className={cls}><UserRound size={22} />Me</NavLink>
      </div>
    </nav>
  );
}
