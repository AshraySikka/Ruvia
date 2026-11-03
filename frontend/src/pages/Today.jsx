import { format } from "date-fns";
import { motion } from "framer-motion";
import { Bell, CalendarClock, ChevronRight, CloudRain, Flame, Keyboard, Sparkles, Target } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MoodCard } from "../components/Cards";
import Rings from "../components/Rings";
import { Sheet, Skeleton, useToast } from "../components/ui";
import Voice from "../components/Voice";
import Water from "../components/Water";
import { api, queued } from "../lib/api";
import { useAuth } from "../lib/auth";
import { mentWord, physWord, shortDate, timeLabel, vibrate } from "../lib/format";

export default function Today() {
  const { user } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const toast = useToast();
  const [t, setT] = useState(null);
  const [explain, setExplain] = useState(false);
  const [rate, setRate] = useState(false);
  const [voice, setVoice] = useState(false);
  const [rough, setRough] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await api("/today/");
      setT(data);
      try { localStorage.setItem("ruvia-today", JSON.stringify(data)); } catch { /* ignore */ }
    } catch {
      try { setT(JSON.parse(localStorage.getItem("ruvia-today"))); } catch { /* ignore */ }
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const addWater = useCallback(async (ml) => {
    setT((x) => x && { ...x, water: { ...x.water, total: x.water.total + ml } });
    const r = await queued("/water/", { amount_ml: ml });
    if (r?.queued) toast("Saved offline. It will sync.");
    else if (r && r.total >= r.goal && r.total - ml < r.goal) toast("Water goal reached. Nice.");
  }, [toast]);

  useEffect(() => {
    const p = new URLSearchParams(loc.search).get("water");
    if (p && p !== "1") { addWater(parseInt(p, 10) || 250); nav("/", { replace: true }); }
  }, [loc.search, addWater, nav]);

  const undoWater = async () => {
    const r = await api("/water/", { method: "DELETE" });
    setT((x) => ({ ...x, water: { ...x.water, total: r.total } }));
  };

  const saveVoice = async (text) => {
    setVoice(false);
    const r = await queued("/chat/", { text, source: "voice", client_id: crypto.randomUUID?.() || String(Date.now()) });
    if (r?.queued) { toast("Saved offline. It will sync."); return; }
    nav("/chat");
  };

  const roughDay = async () => {
    vibrate(30);
    const r = await queued("/rough-day/", {});
    setRough(r?.queued ? { queued: true } : r);
    load();
  };

  if (!t) return <div className="page stack"><Skeleton h={40} /><Skeleton h={150} /><Skeleton h={200} /><Skeleton h={150} /></div>;

  const s = t.scores || {};
  const hour = new Date().getHours();

  return (
    <div className="page">
      <header className="row between" style={{ marginBottom: 20 }}>
        <div>
          <div className="faint">{format(new Date(), "EEEE, MMMM d")}</div>
          <h1 style={{ fontSize: 27 }}>{t.greeting}</h1>
        </div>
        <Link to="/inbox" className="icon-btn" aria-label={`Inbox, ${t.unread} unread`}>
          <Bell size={20} />{t.unread > 0 && <span className="badge">{t.unread}</span>}
        </Link>
      </header>

      <div className="stack-lg">
        {voice ? (
          <Voice autoStart onConfirm={saveVoice} onCancel={() => { setVoice(false); nav("/chat"); }} />
        ) : (
          <section className="panel-plum" aria-label="Check in">
            <div className="row" style={{ alignItems: "flex-start", gap: 16 }}>
              <div className="grow">
                <h2 style={{ fontSize: 27, lineHeight: 1.1 }}>{t.has_checked_in ? "Anything new since earlier?" : hour < 12 ? "How did you wake up?" : "How are you today?"}</h2>
                <p className="small" style={{ opacity: 0.85, marginTop: 6 }}>One sentence is enough. I will tag it and remember what helps.</p>
              </div>
              <button className="orb" onClick={() => setVoice(true)} aria-label="Check in by voice"><span className="blob" />
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0 0 14 0M12 17v4" /></svg>
              </button>
            </div>
            <div className="row" style={{ marginTop: 16, gap: 8 }}>
              <Link to="/chat" className="btn light sm" style={{ textDecoration: "none" }}><Keyboard size={16} /> Type it</Link>
              <button className="btn sm" style={{ background: "transparent", color: "var(--plum-panel-ink)", border: "1.5px solid color-mix(in srgb, var(--plum-panel-ink) 45%, transparent)" }}
                onClick={roughDay} disabled={t.log?.rough_day}>
                <CloudRain size={16} /> {t.log?.rough_day ? "Rough day noted" : "Rough day"}
              </button>
            </div>
            {t.tags?.length > 0 && (
              <div className="chips" style={{ marginTop: 14 }}>
                {t.tags.map((g) => <span key={g.id} className="chip" style={{ background: "color-mix(in srgb, var(--plum-panel-ink) 16%, transparent)", color: "var(--plum-panel-ink)", borderColor: "transparent" }}>{g.label}</span>)}
              </div>
            )}
          </section>
        )}

        {t.followup && (
          <Link to={`/followup/${t.followup.id}`} className="sheet lifted row" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="grow">
              <div style={{ fontWeight: 700 }}>{t.followup.due ? `How is the ${t.followup.label.toLowerCase()} now?` : `Checking on your ${t.followup.label.toLowerCase()}`}</div>
              <div className="small muted">{t.followup.due ? "Tap to tell me if it is better, the same, or worse." : `I will ask around ${timeLabel(t.followup.due_at)}. You can answer now too.`}</div>
            </div>
            <ChevronRight size={20} />
          </Link>
        )}

        <section aria-label="Today's scores">
          <Rings scores={s} onExplain={() => setExplain(true)} />
          <div className="row" style={{ justifyContent: "center", marginTop: 14, gap: 8 }}>
            <button className="btn soft sm" onClick={() => setRate(true)}>{t.log?.physical_rating != null && t.log?.mental_rating != null ? "Change my ratings" : "Rate my day"}</button>
            <button className="btn ghost sm" onClick={() => setExplain(true)}>How scores work</button>
          </div>
        </section>

        <Water total={t.water.total} goal={t.water.goal} onAdd={addWater} onUndo={undoWater} />

        {t.mood && <MoodCard mood={t.mood} />}

        {t.cycle?.has_data && (
          <Link to="/cycle" className="sheet row" style={{ textDecoration: "none", color: "inherit", background: "var(--rose-soft)", borderColor: "transparent" }}>
            <div style={{ width: 54, textAlign: "center" }}>
              <div className="num" style={{ fontSize: 30, color: "var(--rose)" }}>{t.cycle.on_period ? `D${t.cycle.day_in_cycle}` : Math.max(0, t.cycle.days_until)}</div>
              <div className="tiny muted">{t.cycle.on_period ? "of period" : t.cycle.days_until === 1 ? "day" : "days"}</div>
            </div>
            <div className="grow">
              <div style={{ fontWeight: 700 }}>{t.cycle.on_period ? "On your period" : t.cycle.late_by > 0 ? `Period ${t.cycle.late_by} days later than expected` : `Next period around ${shortDate(t.cycle.next_start)}`}</div>
              <div className="small muted">{t.cycle.phase_title}: {t.cycle.tips[0].toLowerCase()}</div>
            </div>
            <ChevronRight size={20} />
          </Link>
        )}

        {t.insight && (
          <Link to="/insights" style={{ textDecoration: "none", color: "inherit", display: "block" }}>
            <div className="section-head"><h2>Something I noticed</h2><span className="link">Insights</span></div>
            <div className="note"><Sparkles size={15} color="var(--euc)" style={{ display: "inline", verticalAlign: -2, marginRight: 6 }} />{t.insight}</div>
          </Link>
        )}

        {t.goals?.length > 0 && (
          <section>
            <div className="section-head"><h2>Shared goals</h2><Link to="/care?tab=goals" className="link">All goals</Link></div>
            <div className="list">
              {t.goals.map((g) => (
                <GoalRow key={g.id} g={g} onDone={load} />
              ))}
            </div>
          </section>
        )}

        {t.upcoming?.length > 0 && (
          <section>
            <div className="section-head"><h2>Coming up</h2><Link to="/care?tab=dates" className="link">Health dates</Link></div>
            <div className="list">
              {t.upcoming.map((u) => (
                <div key={u.id} className="list-row">
                  <span className="ico"><CalendarClock size={18} /></span>
                  <div className="grow"><div style={{ fontWeight: 700 }}>{u.title}</div><div className="small muted">{shortDate(u.date)}{u.time ? `, ${u.time}` : ""}</div></div>
                </div>
              ))}
            </div>
          </section>
        )}

        <div className="row" style={{ justifyContent: "center", gap: 8, color: "var(--ink-2)" }}>
          <Flame size={16} color="var(--saffron)" />
          <span className="small">{t.streak.current > 1 ? `${t.streak.current} days in a row. ` : ""}{t.streak.last_30} of the last 30 days logged. Missing a day is fine.</span>
        </div>
      </div>

      <Sheet open={explain} onClose={() => setExplain(false)} label="How scores work">
        <h2 style={{ marginBottom: 12 }}>How scores work</h2>
        <div className="stack">{t.explainer.map((line) => <p key={line} className="note neutral">{line}</p>)}</div>
        <button className="btn block" style={{ marginTop: 20 }} onClick={() => setExplain(false)}>Got it</button>
      </Sheet>
      <RateSheet open={rate} onClose={() => setRate(false)} log={t.log} onSaved={load} />
      <Sheet open={!!rough} onClose={() => setRough(null)} label="Rough day">
        <div className="center" style={{ padding: "10px 0 6px" }}>
          <CloudRain size={34} color="var(--plum)" style={{ margin: "0 auto 10px" }} />
          <h2>Rough day noted</h2>
          <p className="muted" style={{ margin: "10px 0 18px" }}>No questions. Drink some water, eat something small, and go easy on yourself tonight.</p>
          {rough?.told > 0 && <p className="small" style={{ marginBottom: 16 }}>Your care circle got a gentle heads up, without any details.</p>}
          <button className="btn block" onClick={() => setRough(null)}>Okay</button>
        </div>
      </Sheet>
      <div className="sr">{user?.email}</div>
    </div>
  );
}

function GoalRow({ g, onDone }) {
  const [done, setDone] = useState(g.done);
  const hit = done >= g.target;
  const tap = async () => {
    vibrate();
    setDone((d) => d + 1);
    await queued(`/goals/${g.id}/`, { value: 1 });
    onDone?.();
  };
  return (
    <div className="list-row">
      <span className="ico" style={hit ? { background: "var(--euc)", color: "var(--euc-ink)" } : undefined}><Target size={18} /></span>
      <div className="grow">
        <div style={{ fontWeight: 700 }}>{g.title}</div>
        <div className="progress" style={{ marginTop: 6 }}><i style={{ width: `${Math.min(100, (done / g.target) * 100)}%` }} /></div>
      </div>
      <motion.button whileTap={{ scale: 0.9 }} className="btn soft sm" onClick={tap} aria-label={`Add one to ${g.title}`}>
        {g.target > 1 ? `${done}/${g.target}` : hit ? "Done" : "Mark"}
      </motion.button>
    </div>
  );
}

function RateSheet({ open, onClose, log, onSaved }) {
  const [p, setP] = useState(log?.physical_rating ?? 7);
  const [m, setM] = useState(log?.mental_rating ?? 7);
  const [sleep, setSleep] = useState(log?.sleep_hours ?? "");
  const toast = useToast();
  useEffect(() => { if (open) { setP(log?.physical_rating ?? 7); setM(log?.mental_rating ?? 7); setSleep(log?.sleep_hours ?? ""); } }, [open, log]);
  const save = async () => {
    const r = await queued("/days/today/", { physical_rating: p, mental_rating: m, sleep_hours: sleep === "" ? null : sleep }, "PATCH");
    toast(r?.queued ? "Saved offline. It will sync." : "Saved for today");
    onClose(); onSaved();
  };
  return (
    <Sheet open={open} onClose={onClose} label="Rate my day">
      <h2>Rate today</h2>
      <p className="muted small" style={{ marginBottom: 18 }}>Your own call. No right answer.</p>
      <Scale label="Body" value={p} onChange={setP} word={physWord(p)} color="var(--euc)" />
      <Scale label="Mind" value={m} onChange={setM} word={mentWord(m)} color="var(--plum)" />
      <label className="field" style={{ marginTop: 14 }}>
        <span>Hours slept last night</span>
        <input className="input" type="number" inputMode="decimal" min="0" max="16" step="0.5" value={sleep} onChange={(e) => setSleep(e.target.value)} placeholder="Optional" />
      </label>
      <button className="btn block" style={{ marginTop: 20 }} onClick={save}>Save</button>
    </Sheet>
  );
}

function Scale({ label, value, onChange, word, color }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div className="row between" style={{ marginBottom: 4 }}>
        <span style={{ fontWeight: 700 }}>{label}</span>
        <span><span className="num" style={{ fontSize: 26, color }}>{value}</span><span className="faint">/10</span> <span className="small muted">{word}</span></span>
      </div>
      <input type="range" className="slider" min="0" max="10" value={value} onChange={(e) => { vibrate(4); onChange(Number(e.target.value)); }} aria-label={`${label} rating`} />
    </div>
  );
}
