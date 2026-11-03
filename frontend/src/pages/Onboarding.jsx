import { AnimatePresence, motion } from "framer-motion";
import { Bell, Plus, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Logo, Seg, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { enablePush, pushSupport } from "../lib/push";
import { todayISO } from "../lib/format";

export default function Onboarding() {
  const { user, update } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [p, setP] = useState({ first_name: user.first_name || "", sex: user.sex === "na" ? "" : user.sex, birth_year: user.birth_year || "", water_goal_ml: user.water_goal_ml,
    checkins_per_day: user.checkins_per_day, first_checkin_time: user.first_checkin_time?.slice(0, 5) || "10:00", checkin_interval_hours: user.checkin_interval_hours,
    quiet_start: user.quiet_start?.slice(0, 5) || "22:00", quiet_end: user.quiet_end?.slice(0, 5) || "07:30" });
  const [meds, setMeds] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [noMeds, setNoMeds] = useState(false);
  const [cycle, setCycle] = useState({ track: true, start: "", length: 28 });
  const [city, setCity] = useState("");
  const [places, setPlaces] = useState([]);
  const [place, setPlace] = useState(null);
  const female = p.sex === "female";
  const steps = ["you", "meds", "water", "reminders", ...(female ? ["cycle"] : []), "finish"];
  const id = steps[step];
  const next = () => setStep((s) => Math.min(steps.length - 1, s + 1));

  const finish = async () => {
    try {
      for (const m of meds) await api("/medications/", { method: "POST", body: { name: m, kind: "prescribed" } });
      for (const a of allergies) await api("/allergies/", { method: "POST", body: { substance: a } });
      if (female && cycle.track && cycle.start) await api("/cycle/", { method: "POST", body: { start_date: cycle.start } });
      await update({
        ...p, birth_year: p.birth_year ? Number(p.birth_year) : null, sex: p.sex || "na", track_cycle: female && cycle.track, onboarded: true,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Toronto",
        ...(place ? { city: place.name, latitude: place.latitude, longitude: place.longitude } : {}),
      });
      nav("/", { replace: true });
    } catch (e) { toast(e.message); }
  };

  const findCity = async (q) => {
    setCity(q);
    if (q.length >= 3) setPlaces(await api(`/geo/?q=${encodeURIComponent(q)}`).catch(() => []));
  };

  return (
    <div className="page" style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", paddingBottom: 30 }}>
      <div className="row between" style={{ marginBottom: 26 }}>
        <Logo size={30} />
        <div className="row" style={{ gap: 5 }}>{steps.map((s, i) => <span key={s} style={{ width: i === step ? 22 : 8, height: 8, borderRadius: 4, background: i <= step ? "var(--euc)" : "var(--rule)", transition: "width .3s" }} />)}</div>
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={id} className="grow stack" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.22 }}>
          {id === "you" && (
            <>
              <h1>Hi. Let's set up your diary.</h1>
              <p className="muted">This takes about a minute. You can change all of it later.</p>
              <label className="field"><span>What should I call you?</span><input className="input" value={p.first_name} onChange={(e) => setP({ ...p, first_name: e.target.value })} /></label>
              <div className="field"><span>Sex</span>
                <Seg value={p.sex} onChange={(v) => setP({ ...p, sex: v })} label="Sex" options={[{ value: "female", label: "Female" }, { value: "male", label: "Male" }, { value: "other", label: "Other" }]} />
                <p className="faint" style={{ marginTop: 6 }}>Used only to offer cycle tracking.</p>
              </div>
              <label className="field"><span>Year you were born (optional)</span><input className="input" inputMode="numeric" maxLength={4} value={p.birth_year} onChange={(e) => setP({ ...p, birth_year: e.target.value.replace(/\D/g, "") })} /></label>
            </>
          )}
          {id === "meds" && (
            <>
              <h1>Do you take any medicines?</h1>
              <p className="muted">I check these before suggesting anything over the counter, so I never suggest something that clashes. Include supplements.</p>
              <ListInput items={meds} setItems={setMeds} placeholder="Like Levothyroxine or Vitamin D" />
              <button className={`chip ${noMeds ? "on" : ""}`} style={{ alignSelf: "flex-start" }} onClick={() => setNoMeds(!noMeds)}>None right now</button>
              <h2 style={{ marginTop: 14 }}>Any allergies?</h2>
              <ListInput items={allergies} setItems={setAllergies} placeholder="Like Penicillin or Ibuprofen" />
              <p className="small note neutral">Always check with your doctor or pharmacist before taking something new.</p>
            </>
          )}
          {id === "water" && (
            <>
              <h1>Daily water goal</h1>
              <p className="muted">Around 2 to 2.5 litres suits many adults. Pick what feels right.</p>
              <div className="center" style={{ margin: "24px 0" }}><span className="num" style={{ fontSize: 64, color: "var(--water)" }}>{(p.water_goal_ml / 1000).toFixed(1)}</span><span className="display" style={{ fontSize: 22 }}> litres</span></div>
              <input className="slider" type="range" min="1000" max="4000" step="100" value={p.water_goal_ml} onChange={(e) => setP({ ...p, water_goal_ml: Number(e.target.value) })} aria-label="Water goal" />
            </>
          )}
          {id === "reminders" && <ReminderFields p={p} setP={setP} />}
          {id === "cycle" && (
            <>
              <h1>Track your cycle?</h1>
              <p className="muted">I will predict your next period, share tips for each phase, and ask if it came on time. Private unless you share it.</p>
              <Seg value={cycle.track ? "yes" : "no"} onChange={(v) => setCycle({ ...cycle, track: v === "yes" })} options={[{ value: "yes", label: "Yes, track it" }, { value: "no", label: "Not now" }]} label="Track cycle" />
              {cycle.track && <label className="field"><span>When did your last period start?</span><input className="input" type="date" max={todayISO()} value={cycle.start} onChange={(e) => setCycle({ ...cycle, start: e.target.value })} /></label>}
            </>
          )}
          {id === "finish" && (
            <>
              <h1>Last bits</h1>
              <label className="field"><span>Your city (optional)</span><input className="input" value={place ? place.name : city} onChange={(e) => { setPlace(null); findCity(e.target.value); }} placeholder="Toronto" /></label>
              {!place && places.length > 0 && <div className="list">{places.map((x) => <button key={x.name + x.latitude} className="list-row" onClick={() => { setPlace(x); setPlaces([]); }}>{x.name}</button>)}</div>}
              <p className="faint">Used for weather only, so I can spot things like headaches on low pressure days.</p>
              <NotifyButton />
            </>
          )}
        </motion.div>
      </AnimatePresence>
      <div className="row" style={{ marginTop: 24 }}>
        {step > 0 && <button className="btn ghost" onClick={() => setStep(step - 1)}>Back</button>}
        {id === "finish" ? <button className="btn grow" onClick={finish}>Start using Ruvia</button>
          : <button className="btn grow" onClick={next} disabled={id === "you" && !p.first_name.trim()}>Continue</button>}
      </div>
    </div>
  );
}

function ListInput({ items, setItems, placeholder }) {
  const [v, setV] = useState("");
  const add = (e) => { e.preventDefault(); if (v.trim()) { setItems([...items, v.trim()]); setV(""); } };
  return (
    <div>
      <form onSubmit={add} className="row">
        <input className="input" value={v} onChange={(e) => setV(e.target.value)} placeholder={placeholder} />
        <button className="icon-btn" aria-label="Add" style={{ background: "var(--euc)", color: "var(--euc-ink)", flex: "none" }}><Plus size={18} /></button>
      </form>
      {items.length > 0 && <div className="chips" style={{ marginTop: 10 }}>{items.map((i) => <span key={i} className="chip note">{i}<button aria-label={`Remove ${i}`} onClick={() => setItems(items.filter((x) => x !== i))}><X size={13} /></button></span>)}</div>}
    </div>
  );
}

export function ReminderFields({ p, setP }) {
  const times = [];
  const [h, m] = (p.first_checkin_time || "10:00").split(":").map(Number);
  for (let i = 0; i < p.checkins_per_day; i++) {
    const t = h + i * p.checkin_interval_hours;
    if (t < 24) times.push(`${((t + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${t < 12 ? "AM" : "PM"}`);
  }
  return (
    <>
      <h1>When should I check in?</h1>
      <p className="muted">Your reminders are yours alone. Nobody else can set them for you.</p>
      <div className="field"><span>Check-ins a day</span>
        <Seg value={p.checkins_per_day} onChange={(v) => setP({ ...p, checkins_per_day: v })} label="Check-ins a day" options={[0, 1, 2, 3, 4].map((n) => ({ value: n, label: n === 0 ? "Off" : String(n) }))} />
      </div>
      {p.checkins_per_day > 0 && (
        <div className="row">
          <label className="field grow"><span>First one at</span><input className="input" type="time" value={p.first_checkin_time} onChange={(e) => setP({ ...p, first_checkin_time: e.target.value })} /></label>
          {p.checkins_per_day > 1 && <label className="field grow"><span>Then every</span>
            <select className="select" value={p.checkin_interval_hours} onChange={(e) => setP({ ...p, checkin_interval_hours: Number(e.target.value) })}>{[2, 3, 4, 5, 6, 8, 10, 12].map((n) => <option key={n} value={n}>{n} hours</option>)}</select></label>}
        </div>
      )}
      {times.length > 0 && <p className="small muted">You will hear from me at {times.join(", ")}.</p>}
      <div className="row">
        <label className="field grow"><span>Quiet from</span><input className="input" type="time" value={p.quiet_start} onChange={(e) => setP({ ...p, quiet_start: e.target.value })} /></label>
        <label className="field grow"><span>Until</span><input className="input" type="time" value={p.quiet_end} onChange={(e) => setP({ ...p, quiet_end: e.target.value })} /></label>
      </div>
      <p className="faint">Nothing is sent during quiet hours. Urgent follow-ups wait until the morning too, unless a symptom was severe.</p>
    </>
  );
}

export function NotifyButton() {
  const toast = useToast();
  const s = pushSupport();
  const [on, setOn] = useState(s.permission === "granted");
  if (!s.supported) return <p className="small note neutral">This browser cannot show notifications. Reminders still appear in your inbox.</p>;
  if (s.needsInstall) return <p className="small note">On iPhone, tap Share, then Add to Home Screen. Open Ruvia from there to turn on reminders.</p>;
  return (
    <button className={`btn ${on ? "soft" : ""} block`} onClick={async () => { try { await enablePush(); setOn(true); toast("Reminders are on"); } catch (e) { toast(e.message); } }}>
      <Bell size={18} /> {on ? "Reminders are on" : "Turn on reminders"}
    </button>
  );
}
