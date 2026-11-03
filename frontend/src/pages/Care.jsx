import { CalendarPlus, Check, CloudRain, Droplet, Heart, HeartHandshake, MessageCircleHeart, Plus, Send, Shield, Target, Trash2, UserPlus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Avatar, Seg, Sheet, Skeleton, Toggle, TopBar, useToast } from "../components/ui";
import { api } from "../lib/api";
import { ago, shortDate, todayISO, vibrate } from "../lib/format";

export const SHARE_LABELS = {
  scores: ["Daily scores", "Your physical, mental and overall percentages"],
  tags: ["Day tags", "Words like Headache or Acidity on your calendar"],
  symptoms: ["Symptom details", "Severity, what you tried and how it went"],
  water: ["Water", "How much you drank today"],
  cycle: ["Cycle", "Next expected period and current phase"],
  cycle_alerts: ["Period heads up", "A notification 2 days before"],
  rough_day: ["Rough day signal", "A heads up with no details when you tap Rough day"],
  dates: ["Health dates", "Appointments, tests and renewals"],
  emergency_card: ["Emergency card", "Blood type, allergies, contacts"],
  medications: ["Medicines", "Names and how often"],
};
const NUDGES = [
  { kind: "hug", label: "Send a hug", icon: Heart },
  { kind: "water", label: "Drink some water", icon: Droplet },
  { kind: "checkin", label: "How are you?", icon: MessageCircleHeart },
  { kind: "thinking", label: "Thinking of you", icon: HeartHandshake },
];

export default function Care() {
  const loc = useLocation();
  const nav = useNavigate();
  const tab = new URLSearchParams(loc.search).get("tab") || "people";
  return (
    <div className="page">
      <TopBar title="Care circle" />
      <Seg label="Section" value={tab} onChange={(v) => nav(`/care?tab=${v}`, { replace: true })}
        options={[{ value: "people", label: "People" }, { value: "goals", label: "Goals" }, { value: "dates", label: "Dates" }]} />
      <div style={{ marginTop: 20 }}>
        {tab === "people" && <People />}
        {tab === "goals" && <Goals />}
        {tab === "dates" && <Dates />}
      </div>
    </div>
  );
}

function People() {
  const toast = useToast();
  const [d, setD] = useState(null);
  const [invite, setInvite] = useState(false);
  const [share, setShare] = useState(null);
  const [nudge, setNudge] = useState(null);
  const load = useCallback(() => api("/care/").then(setD), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (d?.nudges?.some((n) => !n.read)) api("/care/nudge/", { method: "PATCH" }).catch(() => {}); }, [d]);

  if (!d) return <div className="stack"><Skeleton h={160} /><Skeleton h={100} /></div>;
  const unread = d.nudges.filter((n) => !n.read);
  return (
    <div className="stack-lg">
      {unread.map((n) => (
        <div key={n.id} className="panel-euc row" style={{ gap: 12 }}>
          <Heart size={22} color="var(--plum)" fill="var(--plum)" />
          <div className="grow"><strong>{n.from} {n.text}</strong>{n.message && <div className="small">"{n.message}"</div>}<div className="tiny faint">{ago(n.at)}</div></div>
        </div>
      ))}

      {d.invites_received.map((i) => (
        <div key={i.id} className="sheet lifted">
          <strong>{i.from} invited you to their care circle</strong>
          <p className="small muted" style={{ margin: "4px 0 12px" }}>Nothing is shared until you choose. You can change it any time.</p>
          <div className="row">
            <button className="btn sm" onClick={async () => { await api(`/care/invites/${i.id}/accept/`, { method: "POST" }); toast("You are connected"); load(); }}>Accept</button>
            <button className="btn ghost sm" onClick={async () => { await api(`/care/invites/${i.id}/decline/`, { method: "POST" }); load(); }}>Not now</button>
          </div>
        </div>
      ))}

      {d.people.map((p) => (
        <section key={p.id} className="sheet" style={{ padding: 0, overflow: "hidden" }}>
          <Link to={`/care/person/${p.id}`} className="row" style={{ padding: 18, textDecoration: "none", color: "inherit", gap: 14 }}>
            <Avatar name={p.name} hue={p.hue} size={54} />
            <div className="grow">
              <h2>{p.name}</h2>
              <div className="small muted">{p.relation || "Care circle"}</div>
            </div>
            {p.today?.overall != null && <div style={{ textAlign: "right" }}><div className="num" style={{ fontSize: 30, color: "var(--euc)" }}>{p.today.overall}%</div><div className="tiny faint">today</div></div>}
          </Link>
          {p.rough_day && (
            <div className="row" style={{ background: "var(--plum-soft)", padding: "12px 18px", gap: 10 }}>
              <CloudRain size={18} color="var(--plum)" /><span className="small grow"><strong>{p.name} is having a rough day.</strong> No details, just a heads up.</span>
            </div>
          )}
          {(p.cycle || p.water || p.tags?.length > 0) && (
            <div style={{ padding: "0 18px 14px" }} className="stack">
              {p.tags?.length > 0 && <div className="chips">{p.tags.map((t) => <span key={t} className="chip symptom">{t}</span>)}</div>}
              <div className="row wrap" style={{ gap: 16 }}>
                {p.water && <span className="small row" style={{ gap: 6 }}><Droplet size={15} color="var(--water)" />{p.water.ml} of {p.water.goal} ml</span>}
                {p.cycle && <span className="small row" style={{ gap: 6, color: "var(--rose)" }}>{p.cycle.on_period ? "On period" : `Period in about ${p.cycle.days_until} days`}</span>}
              </div>
            </div>
          )}
          <div className="row" style={{ borderTop: "1px solid var(--rule)", padding: "10px 12px", gap: 6 }}>
            <button className="btn soft sm grow" onClick={() => setNudge(p)}><Heart size={15} /> Send love</button>
            <button className="btn ghost sm grow" onClick={() => setShare(p)}><Shield size={15} /> What I share</button>
          </div>
        </section>
      ))}

      {!d.people.length && !d.invites_received.length && (
        <div className="sheet center" style={{ padding: 28 }}>
          <HeartHandshake size={34} color="var(--euc)" style={{ margin: "0 auto 10px" }} />
          <h2>Bring someone in</h2>
          <p className="muted" style={{ margin: "8px 0 16px" }}>Invite your partner or family. Each of you picks exactly what to share.</p>
        </div>
      )}

      <button className="btn block" onClick={() => setInvite(true)}><UserPlus size={18} /> Invite someone</button>
      {d.invites_sent.length > 0 && <p className="small faint center">Waiting on: {d.invites_sent.map((i) => i.email).join(", ")}</p>}

      <InviteSheet open={invite} onClose={() => setInvite(false)} onDone={load} />
      <ShareSheet person={share} onClose={() => { setShare(null); load(); }} />
      <NudgeSheet person={nudge} onClose={() => setNudge(null)} />
    </div>
  );
}

function InviteSheet({ open, onClose, onDone }) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [relation, setRelation] = useState("");
  const [error, setError] = useState("");
  const send = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const r = await api("/care/invite/", { method: "POST", body: { email, relation } });
      toast(r.existing_user ? "Invite sent in the app" : "Invite sent by email");
      setEmail(""); setRelation(""); onClose(); onDone();
    } catch (err) { setError(err.message); }
  };
  return (
    <Sheet open={open} onClose={onClose} label="Invite someone">
      <h2 style={{ marginBottom: 6 }}>Invite someone</h2>
      <p className="small muted" style={{ marginBottom: 16 }}>They get an email or an in-app invite. Nothing is shared until you turn it on.</p>
      <form onSubmit={send} className="stack">
        <label className="field"><span>Their email</span><input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label className="field"><span>Who are they to you? (optional)</span><input className="input" value={relation} onChange={(e) => setRelation(e.target.value)} placeholder="Wife, Dad, Sister" /></label>
        {error && <p className="error">{error}</p>}
        <button className="btn block"><Send size={17} /> Send invite</button>
      </form>
    </Sheet>
  );
}

export function ShareSheet({ person, onClose }) {
  const [flags, setFlags] = useState(person?.i_share || {});
  useEffect(() => { setFlags(person?.i_share || {}); }, [person]);
  const flip = async (k, v) => {
    const next = { ...flags, [k]: v, ...(k === "cycle" && !v ? { cycle_alerts: false } : {}) };
    setFlags(next);
    setFlags(await api(`/care/share/${person.id}/`, { method: "PATCH", body: { [k]: v } }));
  };
  return (
    <Sheet open={!!person} onClose={onClose} label="What I share">
      {person && (
        <>
          <h2>What {person.name} can see</h2>
          <p className="small muted" style={{ margin: "6px 0 14px" }}>Changes apply right away. Turn anything off whenever you like.</p>
          <div className="list">
            {Object.entries(SHARE_LABELS).map(([k, [label, sub]]) => (k === "cycle_alerts" && !flags.cycle) ? null : (
              <div key={k} className="list-row">
                <div className="grow"><div style={{ fontWeight: 700 }}>{label}</div><div className="small muted">{sub}</div></div>
                <Toggle checked={flags[k]} onChange={(v) => flip(k, v)} label={label} />
              </div>
            ))}
          </div>
          <RemovePerson person={person} onDone={onClose} />
        </>
      )}
    </Sheet>
  );
}

function RemovePerson({ person, onDone }) {
  const nav = useNavigate();
  return (
    <button className="btn danger block" style={{ marginTop: 18 }} onClick={async () => {
      if (!confirm(`Remove ${person.name} from your circle? Sharing stops both ways.`)) return;
      await api(`/care/people/${person.id}/`, { method: "DELETE" });
      onDone(); nav("/care");
    }}>Remove {person.name} from my circle</button>
  );
}

function NudgeSheet({ person, onClose }) {
  const toast = useToast();
  const [message, setMessage] = useState("");
  const send = async (kind) => {
    vibrate(25);
    await api("/care/nudge/", { method: "POST", body: { to: person.id, kind, message } });
    toast(`Sent to ${person.name}`);
    setMessage(""); onClose();
  };
  return (
    <Sheet open={!!person} onClose={onClose} label="Send love">
      {person && (
        <>
          <h2 style={{ marginBottom: 14 }}>Send {person.name} something</h2>
          <input className="input" placeholder="Add a short note (optional)" value={message} onChange={(e) => setMessage(e.target.value)} maxLength={200} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 14 }}>
            {NUDGES.map(({ kind, label, icon: Icon }) => (
              <button key={kind} className="sheet center" style={{ padding: 18 }} onClick={() => send(kind)}>
                <Icon size={26} color="var(--plum)" style={{ margin: "0 auto 6px" }} /><strong>{label}</strong>
              </button>
            ))}
          </div>
        </>
      )}
    </Sheet>
  );
}

function Goals() {
  const toast = useToast();
  const [goals, setGoals] = useState(null);
  const [people, setPeople] = useState([]);
  const [open, setOpen] = useState(false);
  const load = useCallback(() => api("/goals/").then(setGoals), []);
  useEffect(() => { load(); api("/care/").then((d) => setPeople(d.people)); }, [load]);
  const mark = async (g) => { vibrate(); await api(`/goals/${g.id}/`, { method: "POST", body: { value: 1 } }); load(); };
  if (!goals) return <Skeleton h={200} />;
  return (
    <div className="stack-lg">
      {goals.map((g) => (
        <section key={g.id} className="sheet">
          <div className="row between" style={{ marginBottom: 12 }}>
            <div className="row grow"><span style={{ width: 34, height: 34, borderRadius: 11, display: "grid", placeItems: "center", background: "var(--euc-soft)", color: "var(--euc)", flex: "none" }}><Target size={18} /></span><h3>{g.title}</h3></div>
            <button className="btn soft sm" onClick={() => mark(g)}><Plus size={15} /> {g.target > 1 ? `${g.today.You || 0}/${g.target}` : (g.today.You ? "Done" : "Mark")}</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: `76px repeat(7, 1fr)`, gap: 4, alignItems: "center" }}>
            <span />
            {g.week.map((w) => <span key={w.date} className="tiny faint center">{"MTWTFSS"[(new Date(`${w.date}T12:00`).getDay() + 6) % 7]}</span>)}
            {g.members.map((m) => (
              <FragmentRow key={m.id} name={m.name} week={g.week} target={g.target} />
            ))}
          </div>
          {g.mine && <button className="link" style={{ marginTop: 10, fontSize: 13 }} onClick={async () => { await api(`/goals/${g.id}/`, { method: "DELETE" }); toast("Goal ended"); load(); }}>End this goal</button>}
        </section>
      ))}
      {!goals.length && <p className="faint center">No shared goals yet. Start one together.</p>}
      <button className="btn block" onClick={() => setOpen(true)}><Plus size={18} /> New shared goal</button>
      <GoalSheet open={open} onClose={() => setOpen(false)} people={people} onDone={load} />
    </div>
  );
}

function FragmentRow({ name, week, target }) {
  return (
    <>
      <span className="small" style={{ fontWeight: 700 }}>{name}</span>
      {week.map((w) => {
        const v = w.members[name] ?? 0;
        const full = v >= target;
        return <span key={w.date} style={{ height: 26, borderRadius: 8, background: full ? "var(--euc)" : v > 0 ? "var(--euc-soft)" : "var(--sheet-2)", display: "grid", placeItems: "center" }}>{full && <Check size={13} color="var(--euc-ink)" />}</span>;
      })}
    </>
  );
}

function GoalSheet({ open, onClose, people, onDone }) {
  const [f, setF] = useState({ title: "", target: 1, unit: "times", members: [] });
  const ideas = ["Walk 20 minutes", "8 glasses of water", "Lights out by 11", "Protein at breakfast", "Stretch for 10 minutes"];
  const save = async () => {
    await api("/goals/", { method: "POST", body: f });
    setF({ title: "", target: 1, unit: "times", members: [] }); onClose(); onDone();
  };
  return (
    <Sheet open={open} onClose={onClose} label="New shared goal">
      <h2 style={{ marginBottom: 14 }}>New shared goal</h2>
      <div className="stack">
        <div className="chips">{ideas.map((i) => <button key={i} className={`chip ${f.title === i ? "on" : ""}`} onClick={() => setF({ ...f, title: i, target: i.startsWith("8") ? 8 : 1 })}>{i}</button>)}</div>
        <label className="field"><span>Goal</span><input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
        <label className="field"><span>Times a day</span><input className="input" type="number" min="1" max="20" value={f.target} onChange={(e) => setF({ ...f, target: Number(e.target.value) })} /></label>
        {people.length > 0 && (
          <div className="field"><span>Do it with</span>
            <div className="chips">{people.map((p) => { const on = f.members.includes(p.id); return <button key={p.id} className={`chip ${on ? "on" : ""}`} onClick={() => setF({ ...f, members: on ? f.members.filter((x) => x !== p.id) : [...f.members, p.id] })}>{p.name}</button>; })}</div>
          </div>
        )}
        <button className="btn block" disabled={!f.title.trim()} onClick={save}>Start goal</button>
      </div>
    </Sheet>
  );
}

const KIND_LABEL = { appointment: "Appointment", test: "Test", renewal: "Renewal", vaccine: "Vaccine", checkup: "Checkup", other: "Other", cycle: "Cycle" };

function Dates() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const load = useCallback(() => api("/care/calendar/").then((r) => setItems(r.items)), []);
  useEffect(() => { load(); }, [load]);
  if (!items) return <Skeleton h={200} />;
  const today = todayISO();
  const upcoming = items.filter((i) => i.date >= today);
  const past = items.filter((i) => i.date < today);
  const Row = (i) => (
    <div key={`${i.who_id}-${i.title}-${i.date}`} className="list-row" style={i.date < today ? { opacity: 0.6 } : undefined}>
      <div className="center" style={{ width: 46 }}>
        <div className="tiny muted">{shortDate(i.date).split(" ")[0]}</div>
        <div className="num" style={{ fontSize: 22 }}>{shortDate(i.date).split(" ")[1]}</div>
      </div>
      <div className="grow">
        <div style={{ fontWeight: 700 }}>{i.title}</div>
        <div className="small muted">{i.who}{i.time ? `, ${i.time}` : ""}{i.location ? `, ${i.location}` : ""}</div>
      </div>
      <span className={`pill ${i.kind === "cycle" ? "plum" : ""}`}>{KIND_LABEL[i.kind]}</span>
      {i.mine && i.id && <button className="icon-btn" style={{ width: 34, height: 34 }} aria-label="Delete date" onClick={async () => { await api(`/health-dates/${i.id}/`, { method: "DELETE" }); load(); }}><Trash2 size={14} /></button>}
    </div>
  );
  return (
    <div className="stack-lg">
      <p className="small muted">Your health dates plus whatever your circle shares with you.</p>
      <div className="list">{upcoming.length ? upcoming.map(Row) : <div className="list-row faint">Nothing coming up.</div>}</div>
      {past.length > 0 && <><h3>Recent</h3><div className="list">{past.map(Row)}</div></>}
      <button className="btn block" onClick={() => setOpen(true)}><CalendarPlus size={18} /> Add a health date</button>
      <DateSheet open={open} onClose={() => setOpen(false)} onDone={load} />
    </div>
  );
}

function DateSheet({ open, onClose, onDone }) {
  const [f, setF] = useState({ title: "", kind: "appointment", date: todayISO(), time: "", location: "", shared: true });
  const save = async () => {
    await api("/health-dates/", { method: "POST", body: { ...f, time: f.time || null } });
    setF({ title: "", kind: "appointment", date: todayISO(), time: "", location: "", shared: true }); onClose(); onDone();
  };
  return (
    <Sheet open={open} onClose={onClose} label="Add a health date">
      <h2 style={{ marginBottom: 14 }}>Add a health date</h2>
      <div className="stack">
        <label className="field"><span>What is it</span><input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Dentist, blood test, refill" /></label>
        <label className="field"><span>Type</span>
          <select className="select" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{Object.entries(KIND_LABEL).filter(([k]) => k !== "cycle").map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        </label>
        <div className="row">
          <label className="field grow"><span>Date</span><input className="input" type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></label>
          <label className="field grow"><span>Time</span><input className="input" type="time" value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} /></label>
        </div>
        <label className="field"><span>Where (optional)</span><input className="input" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} /></label>
        <div className="row between"><span style={{ fontWeight: 700 }}>Show to people I share dates with</span><Toggle checked={f.shared} onChange={(v) => setF({ ...f, shared: v })} label="Shared" /></div>
        <p className="faint">You get a reminder the evening before.</p>
        <button className="btn block" disabled={!f.title.trim()} onClick={save}>Save date</button>
      </div>
    </Sheet>
  );
}
