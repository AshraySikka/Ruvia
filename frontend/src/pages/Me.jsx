import { AlertCircle, Bell, ChevronRight, Download, FileDown, HeartPulse, Info, LogOut, MapPin, Package, Palette, Pill, Shield, Trash2, UserRound } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import { Avatar, Field, Seg, Sheet, Skeleton, Toggle, TopBar, useToast } from "../components/ui";
import { api, downloadFile } from "../lib/api";
import { useAuth } from "../lib/auth";
import { NotifyButton, ReminderFields } from "./Onboarding";

export default function Me() {
  return (
    <Routes>
      <Route index element={<Menu />} />
      <Route path="profile" element={<Profile />} />
      <Route path="medicines" element={<Medicines />} />
      <Route path="reminders" element={<Reminders />} />
      <Route path="emergency" element={<EmergencyEdit />} />
      <Route path="privacy" element={<Privacy />} />
    </Routes>
  );
}

function Row({ to, icon: Icon, title, sub, onClick }) {
  const inner = (<><span className="ico"><Icon size={18} /></span><div className="grow"><div style={{ fontWeight: 700 }}>{title}</div>{sub && <div className="small muted">{sub}</div>}</div><ChevronRight size={18} color="var(--ink-3)" /></>);
  return to ? <Link to={to} className="list-row" style={{ textDecoration: "none", color: "inherit" }}>{inner}</Link> : <button className="list-row" onClick={onClick}>{inner}</button>;
}

function Menu() {
  const { user, update, signOut } = useAuth();
  const toast = useToast();
  const [meds, setMeds] = useState(null);
  useEffect(() => { api("/medications/").then(setMeds).catch(() => {}); }, []);
  const report = async () => { toast("Making your summary"); try { await downloadFile("/report.pdf?days=90", "ruvia-doctor-summary.pdf"); } catch { toast("Could not make the PDF. Try again."); } };
  const activeMeds = meds?.filter((m) => m.active) || [];
  return (
    <div className="page">
      <TopBar title="Me" />
      <div className="row" style={{ gap: 14, marginBottom: 24 }}>
        <Avatar name={user.display_name} hue={user.avatar_hue} size={64} />
        <div className="grow"><h2>{user.display_name}</h2><div className="small muted">{user.email}</div></div>
      </div>
      <div className="stack-lg">
        <Link to="/emergency" className="panel-plum row" style={{ textDecoration: "none", gap: 14, padding: 18 }}>
          <HeartPulse size={26} />
          <div className="grow"><strong>Emergency card</strong><div className="small" style={{ opacity: 0.85 }}>Show this to a paramedic or nurse. Works offline.</div></div>
          <ChevronRight size={20} />
        </Link>
        <div className="list">
          <Row to="/me/medicines" icon={Pill} title="Medicines, allergies and home cabinet" sub={meds ? (activeMeds.length ? `Taking ${activeMeds.map((m) => m.name).join(", ")}` : "Taking none") : " "} />
          <Row to="/me/reminders" icon={Bell} title="Reminders and quiet hours" sub={`${user.checkins_per_day ? `${user.checkins_per_day} check-ins a day` : "Check-ins off"}, quiet ${user.quiet_start.slice(0, 5)} to ${user.quiet_end.slice(0, 5)}`} />
          <Row to="/me/profile" icon={UserRound} title="Profile" sub={user.city || "Name, water goal, city"} />
          <Row to="/me/emergency" icon={AlertCircle} title="Edit emergency card" />
          {user.track_cycle && <Row to="/cycle" icon={HeartPulse} title="Cycle" />}
        </div>
        <div className="list">
          <div className="list-row"><span className="ico"><Palette size={18} /></span><div className="grow" style={{ fontWeight: 700 }}>Appearance</div></div>
          <div style={{ padding: "0 16px 14px" }}>
            <Seg value={user.theme} onChange={(v) => update({ theme: v })} label="Appearance" options={[{ value: "auto", label: "Auto" }, { value: "light", label: "Light" }, { value: "dark", label: "Dark" }]} />
          </div>
        </div>
        <div className="list">
          <Row onClick={report} icon={FileDown} title="Doctor summary PDF" sub="Last 90 days of symptoms, what helped, and questions to ask" />
          <Row to="/me/privacy" icon={Shield} title="Privacy and your data" sub="Export or delete everything" />
          <Row to="/about" icon={Info} title="About Ruvia" sub="Why it exists and where the name comes from" />
        </div>
        <button className="btn ghost block" onClick={signOut}><LogOut size={17} /> Sign out</button>
      </div>
    </div>
  );
}

function Profile() {
  const { user, update } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ first_name: user.first_name, birth_year: user.birth_year || "", water_goal_ml: user.water_goal_ml, sex: user.sex, track_cycle: user.track_cycle });
  const [q, setQ] = useState("");
  const [places, setPlaces] = useState([]);
  const save = async (extra = {}) => { await update({ ...f, birth_year: f.birth_year ? Number(f.birth_year) : null, ...extra }); toast("Saved"); };
  return (
    <div className="page">
      <TopBar title="Profile" back="/me" />
      <div className="stack">
        <Field label="Name"><input className="input" value={f.first_name} onChange={(e) => setF({ ...f, first_name: e.target.value })} /></Field>
        <Field label="Year born"><input className="input" inputMode="numeric" value={f.birth_year} onChange={(e) => setF({ ...f, birth_year: e.target.value.replace(/\D/g, "") })} /></Field>
        <div className="field"><span>Sex</span><Seg value={f.sex} onChange={(v) => setF({ ...f, sex: v })} label="Sex" options={[{ value: "female", label: "Female" }, { value: "male", label: "Male" }, { value: "other", label: "Other" }, { value: "na", label: "Skip" }]} /></div>
        <div className="row between"><span style={{ fontWeight: 700 }}>Track my cycle</span><Toggle checked={f.track_cycle} onChange={(v) => setF({ ...f, track_cycle: v })} label="Track cycle" /></div>
        <Field label={`Water goal: ${(f.water_goal_ml / 1000).toFixed(1)} litres`}><input className="slider" type="range" min="1000" max="4000" step="100" value={f.water_goal_ml} onChange={(e) => setF({ ...f, water_goal_ml: Number(e.target.value) })} /></Field>
        <button className="btn block" onClick={() => save()}>Save profile</button>
        <div className="divider" />
        <Field label="City for weather" hint={user.city ? `Now: ${user.city}` : "Not set"}>
          <div className="row"><MapPin size={18} color="var(--water)" /><input className="input" value={q} placeholder="Search a city" onChange={async (e) => { setQ(e.target.value); if (e.target.value.length >= 3) setPlaces(await api(`/geo/?q=${encodeURIComponent(e.target.value)}`).catch(() => [])); }} /></div>
        </Field>
        {places.length > 0 && <div className="list">{places.map((p) => <button key={p.name + p.latitude} className="list-row" onClick={async () => { await save({ city: p.name, latitude: p.latitude, longitude: p.longitude }); setPlaces([]); setQ(""); }}>{p.name}</button>)}</div>}
      </div>
    </div>
  );
}

function CrudList({ path, title, fields, render, empty }) {
  const [items, setItems] = useState(null);
  const [edit, setEdit] = useState(null);
  const load = useCallback(() => api(path).then(setItems), [path]);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    const body = { ...edit };
    Object.keys(body).forEach((k) => body[k] === "" && (body[k] = null));
    if (edit.id) await api(`${path}${edit.id}/`, { method: "PATCH", body }); else await api(path, { method: "POST", body });
    setEdit(null); load();
  };
  const remove = async () => { await api(`${path}${edit.id}/`, { method: "DELETE" }); setEdit(null); load(); };
  return (
    <section>
      <div className="section-head"><h2>{title}</h2><button className="link" onClick={() => setEdit(Object.fromEntries(fields.map((f) => [f.key, f.default ?? ""])))}>Add</button></div>
      {!items ? <Skeleton h={70} /> : (
        <div className="list">
          {items.map((i) => <button key={i.id} className="list-row" onClick={() => setEdit(i)}>{render(i)}</button>)}
          {!items.length && <div className="list-row faint">{empty}</div>}
        </div>
      )}
      <Sheet open={!!edit} onClose={() => setEdit(null)} label={title}>
        {edit && (
          <div className="stack">
            <h2>{edit.id ? "Edit" : "Add"}</h2>
            {fields.map((f) => f.type === "toggle" ? (
              <div key={f.key} className="row between"><span style={{ fontWeight: 700 }}>{f.label}</span><Toggle checked={!!edit[f.key]} onChange={(v) => setEdit({ ...edit, [f.key]: v })} label={f.label} /></div>
            ) : f.options ? (
              <div key={f.key} className="field"><span>{f.label}</span><Seg value={edit[f.key]} onChange={(v) => setEdit({ ...edit, [f.key]: v })} options={f.options} label={f.label} /></div>
            ) : (
              <Field key={f.key} label={f.label}><input className="input" type={f.type || "text"} value={edit[f.key] ?? ""} placeholder={f.placeholder} onChange={(e) => setEdit({ ...edit, [f.key]: e.target.value })} /></Field>
            ))}
            <button className="btn block" onClick={save} disabled={!edit[fields[0].key]}>Save</button>
            {edit.id && <button className="btn danger block" onClick={remove}><Trash2 size={16} /> Remove</button>}
          </div>
        )}
      </Sheet>
    </section>
  );
}

function Medicines() {
  const toast = useToast();
  const [flags, setFlags] = useState(null);
  const refresh = () => api("/interactions/").then(setFlags);
  useEffect(() => { refresh(); }, []);
  const took = async (m) => { await api(`/medications/${m.id}/taken/`, { method: "POST" }); toast(`Logged ${m.name}`); };
  return (
    <div className="page">
      <TopBar title="Medicines" back="/me" />
      <div className="stack-lg">
        <p className="note">I use this list to rule out over the counter options that could clash with what you take. Always check with your doctor or pharmacist before taking anything new.</p>
        <CrudList path="/medications/" title="What I take" empty="Nothing added yet."
          fields={[{ key: "name", label: "Name", placeholder: "Levothyroxine" }, { key: "kind", label: "Type", default: "prescribed", options: [{ value: "prescribed", label: "Prescribed" }, { value: "otc", label: "Pharmacy" }, { value: "supplement", label: "Supplement" }] },
            { key: "dose_text", label: "Dose, as on your label", placeholder: "Optional" }, { key: "frequency", label: "How often", placeholder: "Every morning" }, { key: "start_date", label: "Started", type: "date" }, { key: "active", label: "Still taking it", type: "toggle", default: true }]}
          render={(m) => (<><span className="ico"><Pill size={17} /></span><div className="grow"><div style={{ fontWeight: 700, opacity: m.active ? 1 : 0.5 }}>{m.name}</div><div className="small muted">{[m.kind === "supplement" ? "Supplement" : m.kind === "otc" ? "Pharmacy" : "Prescribed", m.frequency].filter(Boolean).join(", ")}{!m.active ? ", stopped" : ""}</div></div>
            {m.active && <span className="chip" role="button" onClick={(e) => { e.stopPropagation(); took(m); }}>Took it</span>}</>)} />
        <CrudList path="/allergies/" title="Allergies" empty="No allergies added."
          fields={[{ key: "substance", label: "Allergic to", placeholder: "Penicillin" }, { key: "reaction", label: "What happens", placeholder: "Hives" }]}
          render={(a) => (<><span className="ico" style={{ color: "var(--plum)" }}><AlertCircle size={17} /></span><div className="grow"><div style={{ fontWeight: 700 }}>{a.substance}</div><div className="small muted">{a.reaction}</div></div></>)} />
        <CrudList path="/cabinet/" title="At home" empty="Add what is in your medicine cabinet so suggestions match what you have."
          fields={[{ key: "name", label: "Item", placeholder: "Tylenol" }, { key: "note", label: "Where or note", placeholder: "Bathroom" }, { key: "expires_on", label: "Expires", type: "date" }, { key: "running_low", label: "Running low", type: "toggle" }]}
          render={(c) => (<><span className="ico"><Package size={17} /></span><div className="grow"><div style={{ fontWeight: 700 }}>{c.name}</div><div className="small muted">{[c.note, c.expires_on && `expires ${c.expires_on}`].filter(Boolean).join(", ")}</div></div>{c.running_low && <span className="pill caution">Low</span>}</>)} />
        {flags && (
          <section>
            <div className="section-head"><h2>Checked against your list</h2><button className="link" onClick={refresh}>Refresh</button></div>
            {flags.flags.length ? (
              <div className="stack">{flags.flags.map((f) => <div key={f.key} className={`note ${f.level === "avoid" ? "" : "watch"}`} style={f.level === "avoid" ? { borderColor: "var(--plum)" } : undefined}>
                <strong>{f.brands[0] || f.name}</strong> {f.level === "avoid" ? "is left out of suggestions" : "comes with a heads up"}: {f.reasons.join("; ")}.</div>)}</div>
            ) : <p className="faint">Nothing in the over the counter list clashes with what you entered.</p>}
          </section>
        )}
      </div>
    </div>
  );
}

function Reminders() {
  const { user, update } = useAuth();
  const toast = useToast();
  const [p, setP] = useState({ checkins_per_day: user.checkins_per_day, first_checkin_time: user.first_checkin_time.slice(0, 5), checkin_interval_hours: user.checkin_interval_hours,
    quiet_start: user.quiet_start.slice(0, 5), quiet_end: user.quiet_end.slice(0, 5) });
  const flip = (k) => (v) => update({ [k]: v });
  return (
    <div className="page">
      <TopBar title="Reminders" back="/me" />
      <div className="stack-lg">
        <div className="stack"><ReminderFields p={p} setP={setP} /><button className="btn block" onClick={async () => { await update(p); toast("Reminders saved"); }}>Save times</button></div>
        <div className="list">
          {[["water_reminders", "Water nudges", "Only when you are behind for the time of day"], ["followups_enabled", "Symptom follow-ups", "I check back after you log a symptom"], ["cycle_notifications", "Period reminders", "Heads up and on the day"], ["weekly_summary", "Weekly summary", "Sunday evening"]].map(([k, t, s]) => (
            <div key={k} className="list-row"><div className="grow"><div style={{ fontWeight: 700 }}>{t}</div><div className="small muted">{s}</div></div><Toggle checked={user[k]} onChange={flip(k)} label={t} /></div>
          ))}
          {user.water_reminders && (
            <div className="list-row"><div className="grow" style={{ fontWeight: 700 }}>Water nudge every</div>
              <select className="select" style={{ width: 130 }} value={user.water_interval_hours} onChange={(e) => update({ water_interval_hours: Number(e.target.value) })}>{[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n} hour{n > 1 ? "s" : ""}</option>)}</select></div>
          )}
        </div>
        <NotifyButton />
        <button className="btn ghost block" onClick={async () => { const r = await api("/push/test/", { method: "POST" }); toast(r.sent ? "Test sent" : "Push is not set up on this device yet"); }}>Send a test reminder</button>
      </div>
    </div>
  );
}

function EmergencyEdit() {
  const toast = useToast();
  const nav = useNavigate();
  const [c, setC] = useState(null);
  useEffect(() => { api("/emergency-card/").then(setC); }, []);
  if (!c) return <div className="page"><Skeleton h={300} /></div>;
  const set = (k) => (e) => setC({ ...c, [k]: e.target.value });
  const contact = (i, k, v) => setC({ ...c, contacts: c.contacts.map((x, j) => (j === i ? { ...x, [k]: v } : x)) });
  return (
    <div className="page">
      <TopBar title="Emergency card" back="/me" />
      <div className="stack">
        <p className="note">Allergies and medicines come from your Medicines list automatically.</p>
        <Field label="Full name"><input className="input" value={c.full_name || ""} onChange={set("full_name")} /></Field>
        <div className="row">
          <Field label="Date of birth"><input className="input" type="date" value={c.date_of_birth || ""} onChange={set("date_of_birth")} /></Field>
          <Field label="Blood type"><select className="select" value={c.blood_type || ""} onChange={set("blood_type")}><option value="">Not sure</option>{["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"].map((b) => <option key={b}>{b}</option>)}</select></Field>
        </div>
        <Field label="Conditions"><textarea className="textarea" value={c.conditions || ""} onChange={set("conditions")} /></Field>
        <Field label="Doctor"><input className="input" value={c.doctor || ""} onChange={set("doctor")} placeholder="Name, clinic, phone" /></Field>
        <Field label="Health card note"><input className="input" value={c.health_card_note || ""} onChange={set("health_card_note")} placeholder="Where to find it. Not the number." /></Field>
        <Field label="Other notes"><textarea className="textarea" value={c.notes || ""} onChange={set("notes")} /></Field>
        <h3>Emergency contacts</h3>
        {c.contacts.map((p, i) => (
          <div key={i} className="sheet tight stack">
            <div className="row"><input className="input" placeholder="Name" value={p.name} onChange={(e) => contact(i, "name", e.target.value)} /><input className="input" placeholder="Relation" value={p.relation} onChange={(e) => contact(i, "relation", e.target.value)} /></div>
            <div className="row"><input className="input" type="tel" placeholder="Phone" value={p.phone} onChange={(e) => contact(i, "phone", e.target.value)} />
              <button className="icon-btn" aria-label="Remove contact" onClick={() => setC({ ...c, contacts: c.contacts.filter((_, j) => j !== i) })}><Trash2 size={15} /></button></div>
          </div>
        ))}
        {c.contacts.length < 4 && <button className="btn soft" onClick={() => setC({ ...c, contacts: [...c.contacts, { name: "", relation: "", phone: "" }] })}>Add a contact</button>}
        <button className="btn block" onClick={async () => { await api("/emergency-card/", { method: "PUT", body: c }); toast("Card saved"); nav("/emergency"); }}>Save card</button>
      </div>
    </div>
  );
}

function Privacy() {
  const { signOut } = useAuth();
  const toast = useToast();
  const [del, setDel] = useState(false);
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  return (
    <div className="page">
      <TopBar title="Privacy" back="/me" />
      <div className="stack-lg">
        <section className="stack">
          <h2>What happens to your data</h2>
          <p>Your diary lives in a private database. Check-in text and notes are encrypted at rest. Nothing is shared with your circle unless you turn it on, person by person.</p>
          <p>When you check in, the text (and voice recordings, for transcription) is sent to OpenAI, with Google Gemini and Anthropic Claude as backups if the first one is down. They receive the words you wrote and the facts needed to reply, never your name or email.</p>
          <p>Weather comes from Open-Meteo using only your city's coordinates. Emails are sent through SendGrid.</p>
          <p className="muted">Ruvia is a personal diary, not a medical service. Suggestions are general and never replace your doctor or pharmacist.</p>
        </section>
        <div className="list">
          <Row icon={Download} title="Export everything" sub="A JSON file with all your entries" onClick={async () => { await downloadFile("/export/", "ruvia-export.json"); toast("Export downloaded"); }} />
        </div>
        <button className="btn danger block" onClick={() => setDel(true)}><Trash2 size={17} /> Delete my account and data</button>
      </div>
      <Sheet open={del} onClose={() => setDel(false)} label="Delete account">
        <h2>Delete everything?</h2>
        <p className="muted" style={{ margin: "8px 0 14px" }}>This permanently removes your diary, check-ins, cycle data and sharing. It cannot be undone.</p>
        <Field label="Your password"><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        {err && <p className="error" style={{ marginTop: 8 }}>{err}</p>}
        <button className="btn danger block" style={{ marginTop: 16 }} onClick={async () => { try { await api("/me/", { method: "DELETE", body: { password: pw } }); await signOut(); } catch (e) { setErr(e.message); } }}>Delete permanently</button>
      </Sheet>
    </div>
  );
}
