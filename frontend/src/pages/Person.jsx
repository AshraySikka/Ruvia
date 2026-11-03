import { CalendarClock, CloudRain, Droplet, Heart, Phone, Pill, Shield } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { EpisodeLine } from "../components/Cards";
import { Avatar, Skeleton, TopBar } from "../components/ui";
import { api } from "../lib/api";
import { scoreTone, shortDate } from "../lib/format";
import { ShareSheet } from "./Care";

export default function Person() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [share, setShare] = useState(false);
  const [error, setError] = useState("");
  const load = () => api(`/care/people/${id}/`).then(setP).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  if (error) return <div className="page"><TopBar title="Care circle" back="/care" /><p className="error">{error}</p></div>;
  if (!p) return <div className="page stack"><Skeleton h={80} /><Skeleton h={200} /></div>;
  const nothing = !Object.entries(p.they_share).some(([k, v]) => v && k !== "rough_day");
  return (
    <div className="page">
      <TopBar title={p.name} back="/care" />
      <div className="row" style={{ gap: 14, marginBottom: 22 }}>
        <Avatar name={p.name} hue={p.hue} size={64} />
        <div className="grow"><div className="muted">{p.relation || "Care circle"}</div>
          {p.today?.overall != null && <div><span className="num" style={{ fontSize: 34 }}>{p.today.overall}%</span> <span className="faint">today</span></div>}</div>
      </div>
      <div className="stack-lg">
        {p.rough_day && <div className="panel-euc row" style={{ background: "var(--plum-soft)" }}><CloudRain size={20} color="var(--plum)" /><span><strong>Rough day today.</strong> They chose not to share why. A kind message goes a long way.</span></div>}
        {p.week?.length > 0 && (
          <section>
            <div className="section-head"><h2>Last 7 days</h2></div>
            <div className="row" style={{ gap: 6, alignItems: "flex-end", height: 110 }}>
              {p.week.map((w) => (
                <div key={w.date} className="grow center">
                  <div style={{ height: `${Math.max(8, w.overall || 0)}px`, background: scoreTone(w.overall), borderRadius: 8 }} />
                  <div className="tiny faint" style={{ marginTop: 4 }}>{shortDate(w.date).split(" ")[1]}</div>
                </div>
              ))}
            </div>
          </section>
        )}
        {p.tags?.length > 0 && <section><div className="section-head"><h2>Today</h2></div><div className="chips">{p.tags.map((t) => <span key={t} className="chip symptom">{t}</span>)}</div></section>}
        {p.water && <div className="row"><Droplet size={18} color="var(--water)" /><span>{p.water.ml} of {p.water.goal} ml of water today</span></div>}
        {p.cycle && (
          <div className="sheet" style={{ background: "var(--rose-soft)", borderColor: "transparent" }}>
            <strong>{p.cycle.on_period ? "On their period" : `Period expected around ${shortDate(p.cycle.next_start)}`}</strong>
            <div className="small muted">{p.cycle.phase_title}. {p.cycle.days_until >= 0 && p.cycle.days_until <= 3 && !p.cycle.on_period ? "A heating pad and snacks nearby would be thoughtful." : ""}</div>
          </div>
        )}
        {p.recent_symptoms?.length > 0 && <section><div className="section-head"><h2>Recent symptoms</h2></div>{p.recent_symptoms.map((e, i) => <EpisodeLine key={i} e={{ ...e, triggers: [], tried: [] }} />)}</section>}
        {p.dates?.length > 0 && (
          <section><div className="section-head"><h2>Coming up</h2></div>
            <div className="list">{p.dates.map((d) => <div key={d.title + d.date} className="list-row"><span className="ico"><CalendarClock size={17} /></span><div className="grow"><strong>{d.title}</strong><div className="small muted">{shortDate(d.date)}{d.time ? `, ${d.time}` : ""}</div></div></div>)}</div>
          </section>
        )}
        {p.medications?.length > 0 && <section><div className="section-head"><h2>Medicines</h2></div><div className="list">{p.medications.map((m) => <div key={m.name} className="list-row"><span className="ico"><Pill size={17} /></span><div className="grow"><strong>{m.name}</strong><div className="small muted">{m.frequency}</div></div></div>)}</div></section>}
        {p.emergency_card && (
          <section className="sheet" style={{ borderColor: "var(--plum)" }}>
            <div className="row" style={{ marginBottom: 8 }}><Heart size={18} color="var(--plum)" /><h3>Emergency card</h3></div>
            <p><strong>Blood type:</strong> {p.emergency_card.blood_type || "Not set"}</p>
            <p><strong>Allergies:</strong> {p.emergency_card.allergies.map((a) => a.substance).join(", ") || "None listed"}</p>
            {p.emergency_card.conditions && <p><strong>Conditions:</strong> {p.emergency_card.conditions}</p>}
            {p.emergency_card.contacts.map((c) => <a key={c.phone} href={`tel:${c.phone}`} className="chip" style={{ marginTop: 8, textDecoration: "none" }}><Phone size={13} /> {c.name}, {c.phone}</a>)}
          </section>
        )}
        {nothing && <p className="note neutral">{p.name} is not sharing details right now. You will still get a gentle heads up on rough days if they allow it.</p>}
        <button className="btn ghost block" onClick={() => setShare(true)}><Shield size={17} /> What I share with {p.name}</button>
      </div>
      <ShareSheet person={share ? p : null} onClose={() => { setShare(false); load(); }} />
    </div>
  );
}
