import { motion } from "framer-motion";
import { Check, Frown, Meh, Smile } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { RemedyCard, SafetyCard } from "../components/Cards";
import { Skeleton, TopBar } from "../components/ui";
import { api } from "../lib/api";
import { ago, vibrate } from "../lib/format";

const ANSWERS = [
  { key: "better", label: "Feeling better", icon: Smile, bg: "var(--euc-soft)", fg: "var(--euc)" },
  { key: "same", label: "About the same", icon: Meh, bg: "var(--saffron-soft)", fg: "color-mix(in srgb, var(--saffron) 60%, var(--ink))" },
  { key: "worse", label: "Worse", icon: Frown, bg: "var(--plum-soft)", fg: "var(--plum)" },
];

export default function FollowUp() {
  const { id } = useParams();
  const loc = useLocation();
  const [fu, setFu] = useState(null);
  const [answer, setAnswer] = useState(new URLSearchParams(loc.search).get("answer"));
  const [tried, setTried] = useState([]);
  const [other, setOther] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api(`/followups/${id}/`).then((f) => { setFu(f); setTried(f.episode.tried || []); }).catch((e) => setError(e.message)); }, [id]);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api(`/followups/${id}/`, { method: "POST", body: { answer, tried: [...tried, ...(other.trim() ? [other.trim()] : [])] } });
      setResult(r.messages[1]);
      vibrate(20);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (error) return <div className="page"><TopBar title="Follow up" back="/" /><p className="error">{error}</p></div>;
  if (!fu) return <div className="page stack"><Skeleton h={60} /><Skeleton h={220} /></div>;

  if (result) {
    const p = result.payload || {};
    return (
      <div className="page">
        <TopBar title="Thanks" back="/" />
        <div className="stack">
          <motion.div className="bubble them" style={{ maxWidth: "100%" }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>{result.text}</motion.div>
          {p.resources && <SafetyCard payload={{ type: "worse", resources: p.resources }} />}
          {p.suggestions?.map((s) => <RemedyCard key={s.key} s={s} />)}
          <Link to="/" className="btn block" style={{ textDecoration: "none" }}>Back to today</Link>
        </div>
      </div>
    );
  }

  const answered = fu.status === "answered";
  return (
    <div className="page">
      <TopBar title="Checking in" back="/" />
      <p className="muted" style={{ marginBottom: 6 }}>{fu.episode.label}, started {ago(fu.episode.started_at)}</p>
      <h1 style={{ fontSize: 32, marginBottom: 22 }}>How are you feeling now?</h1>
      {answered && <p className="note" style={{ marginBottom: 18 }}>You already answered this one ({fu.answer}). You can update it.</p>}
      <div className="stack">
        {ANSWERS.map((a) => {
          const Icon = a.icon;
          const on = answer === a.key;
          return (
            <motion.button key={a.key} whileTap={{ scale: 0.98 }} onClick={() => { vibrate(); setAnswer(a.key); }}
              className="row" aria-pressed={on}
              style={{ width: "100%", padding: "18px 20px", borderRadius: 22, background: a.bg, color: "var(--ink)", border: on ? `2.5px solid ${a.fg}` : "2.5px solid transparent", fontWeight: 700, fontSize: 18 }}>
              <Icon size={28} color={a.fg} /><span className="grow" style={{ textAlign: "left" }}>{a.label}</span>{on && <Check size={22} color={a.fg} />}
            </motion.button>
          );
        })}
      </div>
      {answer && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 26 }}>
          <h2 style={{ marginBottom: 4 }}>What did you try?</h2>
          <p className="small muted" style={{ marginBottom: 12 }}>Tap all that apply. This is how I learn what works for you.</p>
          <div className="chips">
            {fu.tried_options.map((o) => {
              const on = tried.includes(o);
              return <button key={o} className={`chip ${on ? "on" : ""}`} onClick={() => setTried(on ? tried.filter((x) => x !== o) : [...tried, o])}>{on && <Check size={13} />}{o}</button>;
            })}
          </div>
          <input className="input" style={{ marginTop: 12 }} placeholder="Something else" value={other} onChange={(e) => setOther(e.target.value)} />
          <button className="btn block" style={{ marginTop: 18 }} onClick={submit} disabled={busy}>{busy ? "Saving" : "Save"}</button>
        </motion.div>
      )}
    </div>
  );
}
