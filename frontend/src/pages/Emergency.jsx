import { Phone, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

/** Big, readable, works offline from the last saved copy. Meant to be shown to someone else. */
export default function Emergency() {
  const nav = useNavigate();
  const [c, setC] = useState(() => { try { return JSON.parse(localStorage.getItem("ruvia-emergency")); } catch { return null; } });
  useEffect(() => { api("/emergency-card/").then((x) => { setC(x); try { localStorage.setItem("ruvia-emergency", JSON.stringify(x)); } catch { /* ignore */ } }).catch(() => {}); }, []);
  if (!c) return <div className="page">Loading</div>;
  return (
    <div className="page" style={{ background: "var(--sheet)", minHeight: "100dvh" }}>
      <div className="row between" style={{ marginBottom: 20 }}>
        <span className="pill plum" style={{ fontSize: 14, padding: "6px 12px" }}>Emergency card</span>
        <button className="icon-btn" aria-label="Close" onClick={() => nav(-1)}><X size={20} /></button>
      </div>
      <h1 style={{ fontSize: 38 }}>{c.full_name}</h1>
      {c.date_of_birth && <p className="muted" style={{ fontSize: 18 }}>Born {c.date_of_birth}</p>}
      <div className="stack-lg" style={{ marginTop: 24, fontSize: 18 }}>
        <div className="row" style={{ gap: 14 }}>
          <div className="sheet grow center"><div className="small muted">Blood type</div><div className="num" style={{ fontSize: 40, color: "var(--plum)" }}>{c.blood_type || "?"}</div></div>
          <div className="sheet grow center"><div className="small muted">Allergies</div><div style={{ fontWeight: 700, fontSize: 20 }}>{c.allergies.map((a) => a.substance).join(", ") || "None known"}</div></div>
        </div>
        {c.conditions && <div><div className="small muted">Conditions</div><p style={{ fontWeight: 700 }}>{c.conditions}</p></div>}
        {c.medications.length > 0 && <div><div className="small muted">Medicines</div>{c.medications.map((m) => <p key={m.name} style={{ fontWeight: 700 }}>{m.name}{m.dose_text ? `, ${m.dose_text}` : ""}{m.frequency ? `, ${m.frequency}` : ""}</p>)}</div>}
        {c.doctor && <div><div className="small muted">Doctor</div><p>{c.doctor}</p></div>}
        {c.health_card_note && <div><div className="small muted">Health card</div><p>{c.health_card_note}</p></div>}
        {c.notes && <div><div className="small muted">Notes</div><p>{c.notes}</p></div>}
        <div className="stack">
          {c.contacts.map((p) => <a key={p.phone} href={`tel:${p.phone}`} className="btn plum block" style={{ textDecoration: "none", minHeight: 58, fontSize: 18 }}><Phone size={20} /> Call {p.name}{p.relation ? ` (${p.relation})` : ""}</a>)}
          <a href="tel:911" className="btn danger block" style={{ textDecoration: "none", minHeight: 58, fontSize: 18 }}><Phone size={20} /> Call 911</a>
        </div>
      </div>
    </div>
  );
}
