import { differenceInDays, format, parseISO } from "date-fns";
import { motion } from "framer-motion";
import { Check, Droplets, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Seg, Sheet, Skeleton, Toggle, TopBar, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { shortDate, todayISO } from "../lib/format";

const PHASE = { menstrual: "Period", follicular: "Follicular", ovulation: "Ovulation", luteal: "Luteal" };
const PHASE_COLOR = { menstrual: "var(--rose)", follicular: "var(--euc-soft)", ovulation: "var(--saffron-soft)", luteal: "var(--plum-soft)" };

export default function Cycle() {
  const { user, update } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();
  const toast = useToast();
  const [d, setD] = useState(null);
  const [log, setLog] = useState(false);
  const confirmParam = new URLSearchParams(loc.search).get("confirm");

  const load = useCallback(() => api("/cycle/").then(setD), []);
  useEffect(() => { load(); }, [load]);

  const answer = async (a) => {
    const r = await api("/cycle/confirm/", { method: "POST", body: { answer: a } });
    toast(r.message);
    nav("/cycle", { replace: true });
    load();
  };
  useEffect(() => { if (confirmParam === "yes" || confirmParam === "not_yet") answer(confirmParam); }, [confirmParam]); // eslint-disable-line

  if (!d) return <div className="page stack"><Skeleton h={50} /><Skeleton h={220} /></div>;
  const s = d.summary;

  if (!user.track_cycle && !s.has_data) {
    return (
      <div className="page">
        <TopBar title="Cycle" back="/" />
        <div className="sheet stack">
          <h2>Track your cycle</h2>
          <p className="muted">Ruvia predicts your next period, gives tips for each phase, and asks if it came on time. It stays private unless you choose to share it.</p>
          <button className="btn" onClick={async () => { await update({ track_cycle: true }); setLog(true); }}>Turn on and log my last period</button>
        </div>
        <LogSheet open={log} onClose={() => setLog(false)} onSaved={load} />
      </div>
    );
  }

  const asking = d.ask_today || confirmParam === "1";
  return (
    <div className="page">
      <TopBar title="Cycle" back="/" />
      <div className="stack-lg">
        {asking && (
          <motion.section className="panel-plum" initial={{ scale: 0.97, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
            <h2 style={{ fontSize: 24 }}>Did your period start today?</h2>
            <p className="small" style={{ opacity: 0.85, margin: "6px 0 14px" }}>It was expected around {shortDate(s.next_start)}.</p>
            <div className="row"><button className="btn light" onClick={() => answer("yes")}><Check size={18} /> Yes, it started</button>
              <button className="btn sm" style={{ color: "var(--plum-panel-ink)", border: "1.5px solid var(--plum-panel-ink)" }} onClick={() => answer("not_yet")}>Not yet</button></div>
          </motion.section>
        )}

        {s.has_data ? (
          <section className="sheet" style={{ background: "var(--rose-soft)", borderColor: "transparent", textAlign: "center", padding: 26 }}>
            <Droplets size={26} color="var(--rose)" style={{ margin: "0 auto" }} />
            {s.on_period ? (
              <><div className="small muted" style={{ marginTop: 8 }}>Period</div><div className="hero-word" style={{ color: "var(--rose)" }}>Day {s.day_in_cycle}</div></>
            ) : s.late_by > 0 ? (
              <><div className="small muted" style={{ marginTop: 8 }}>Expected {shortDate(s.next_start)}</div><div className="hero-word" style={{ fontSize: 40, color: "var(--rose)" }}>{s.late_by} days later</div>
                <p className="small muted" style={{ marginTop: 6 }}>Cycles shift for lots of reasons, like stress or travel.</p></>
            ) : (
              <><div className="small muted" style={{ marginTop: 8 }}>Next period</div>
                <div className="hero-word" style={{ color: "var(--rose)" }}>{s.days_until === 0 ? "Today" : `in ${s.days_until} day${s.days_until === 1 ? "" : "s"}`}</div>
                <div className="small muted" style={{ marginTop: 6 }}>{format(parseISO(s.window_start), "MMM d")} to {format(parseISO(s.window_end), "MMM d")}, estimated</div></>
            )}
            <PhaseBar s={s} />
          </section>
        ) : null}

        {s.has_data && (
          <section>
            <div className="section-head"><h2>{s.phase_title}</h2><span className="faint">day {s.day_in_cycle} of about {s.cycle_length}</span></div>
            <div className="list">
              {s.tips.map((t) => <div key={t} className="list-row"><span className="ico" style={{ color: "var(--rose)" }}><Check size={17} /></span><span>{t}</span></div>)}
            </div>
            <p className="small faint" style={{ marginTop: 8 }}>Gentle ideas that help many people. If periods are very painful or heavy, talk to your doctor.</p>
          </section>
        )}

        <section className="row" style={{ gap: 10 }}>
          <button className="btn grow" onClick={() => setLog(true)}>Log a period</button>
          {s.on_period && <button className="btn ghost" onClick={() => answer("ended")}>It ended today</button>}
        </section>

        {s.has_data && (
          <section className="row wrap" style={{ gap: 10 }}>
            {[["Average cycle", `${s.cycle_length} days`], ["Period length", `${s.period_length} days`], ["Cycles logged", s.logged_cycles], ["Varies by", s.variability_days != null ? `${s.variability_days} days` : "Need 3"]].map(([k, v]) => (
              <div key={k} className="sheet tight" style={{ flex: "1 1 40%" }}><div className="tiny muted">{k}</div><div className="num" style={{ fontSize: 22 }}>{v}</div></div>
            ))}
          </section>
        )}

        <section>
          <div className="section-head"><h2>History</h2></div>
          <div className="list">
            {d.entries.map((e) => (
              <div key={e.id} className="list-row">
                <div className="grow">
                  <div style={{ fontWeight: 700 }}>{shortDate(e.start_date)}{e.end_date ? ` to ${shortDate(e.end_date)}` : ""}</div>
                  <div className="small muted">{e.flow[0].toUpperCase() + e.flow.slice(1)} flow{e.pain != null ? `, pain ${e.pain}/10` : ""}{e.end_date ? `, ${differenceInDays(parseISO(e.end_date), parseISO(e.start_date)) + 1} days` : ""}</div>
                </div>
                {e.on_time === true && <span className="pill">On time</span>}
                {e.on_time === false && <span className="pill caution">Off by a few days</span>}
                <button className="icon-btn" style={{ width: 36, height: 36 }} aria-label="Delete entry" onClick={async () => { if (confirm("Delete this period entry?")) { await api(`/cycle/${e.id}/`, { method: "DELETE" }); load(); } }}><Trash2 size={15} /></button>
              </div>
            ))}
            {!d.entries.length && <div className="list-row faint">No periods logged yet.</div>}
          </div>
        </section>

        <section className="list">
          <div className="list-row"><div className="grow"><strong>Period reminders</strong><div className="small muted">Heads up 2 days before, and a check on the day.</div></div>
            <Toggle checked={user.cycle_notifications} onChange={(v) => update({ cycle_notifications: v })} label="Period reminders" /></div>
          <Link to="/care" className="list-row" style={{ textDecoration: "none", color: "inherit" }}><div className="grow"><strong>Who can see this</strong><div className="small muted">Off for everyone unless you turn it on, person by person.</div></div></Link>
        </section>
      </div>
      <LogSheet open={log} onClose={() => setLog(false)} onSaved={load} />
    </div>
  );
}

function PhaseBar({ s }) {
  const total = s.cycle_length;
  const pos = Math.min(100, (s.day_in_cycle / total) * 100);
  return (
    <div style={{ marginTop: 22 }}>
      <div style={{ position: "relative", height: 14, borderRadius: 8, overflow: "hidden", display: "flex" }}>
        {s.phases.map((p) => <div key={p.key} style={{ flex: Math.max(1, p.end - p.start + 1), background: PHASE_COLOR[p.key] }} title={PHASE[p.key]} />)}
      </div>
      <div style={{ position: "relative", height: 18 }}>
        <div style={{ position: "absolute", left: `calc(${pos}% - 7px)`, top: -18, width: 14, height: 22, borderRadius: 7, background: "var(--ink)", border: "3px solid var(--sheet)" }} aria-label={`Day ${s.day_in_cycle}`} />
      </div>
      <div className="row between tiny muted">{s.phases.map((p) => <span key={p.key}>{PHASE[p.key]}</span>)}</div>
    </div>
  );
}

function LogSheet({ open, onClose, onSaved }) {
  const toast = useToast();
  const [f, setF] = useState({ start_date: todayISO(), end_date: "", flow: "medium", pain: 3 });
  const save = async () => {
    const r = await api("/cycle/", { method: "POST", body: { ...f, end_date: f.end_date || null } });
    toast(r.on_time ? "Logged. Right on time." : "Logged");
    onClose(); onSaved();
  };
  return (
    <Sheet open={open} onClose={onClose} label="Log a period">
      <h2 style={{ marginBottom: 16 }}>Log a period</h2>
      <div className="stack">
        <label className="field"><span>Started</span><input className="input" type="date" max={todayISO()} value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></label>
        <label className="field"><span>Ended (leave empty if still going)</span><input className="input" type="date" max={todayISO()} value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></label>
        <div className="field"><span>Flow</span><Seg value={f.flow} onChange={(v) => setF({ ...f, flow: v })} options={[{ value: "light", label: "Light" }, { value: "medium", label: "Medium" }, { value: "heavy", label: "Heavy" }]} label="Flow" /></div>
        <div className="field"><span>Pain, {f.pain} of 10</span><input className="slider" type="range" min="0" max="10" value={f.pain} onChange={(e) => setF({ ...f, pain: Number(e.target.value) })} aria-label="Pain" /></div>
        <button className="btn block" onClick={save}>Save</button>
      </div>
    </Sheet>
  );
}
