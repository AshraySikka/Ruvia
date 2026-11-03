import { AlertTriangle, Check, Home, Leaf, Phone, Pill, Sparkles, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { shortDate } from "../lib/format";

const SEV = { mild: "Mild", moderate: "Moderate", severe: "Severe", extreme: "Extreme" };

export function RemedyCard({ s }) {
  const [open, setOpen] = useState(false);
  if (!s) return null;
  const helped = s.history?.helped || [];
  const home = open ? s.home : s.home.slice(0, 3);
  return (
    <div className="remedy">
      <div className="remedy-head">
        <span className="pill plum">{SEV[s.severity] || "Logged"}</span>
        <h3 className="grow">{s.label}</h3>
        {s.history?.count > 0 && <span className="tiny faint">{s.history.count} times before</span>}
      </div>
      <div className="remedy-body">
        {helped.length > 0 && (
          <div className="win">
            <div className="row" style={{ gap: 6, fontWeight: 700, marginBottom: 2 }}><ThumbsUp size={15} /> What worked for you before</div>
            {helped.slice(0, 3).map((h) => <div key={h.item}>{h.item} <span className="faint">({h.times} {h.times === 1 ? "time" : "times"})</span></div>)}
          </div>
        )}
        <h4><Home size={15} /> Home remedies first</h4>
        <ul>{home.map((h) => <li key={h}>{h}</li>)}</ul>
        {s.home.length > 3 && <button className="link" onClick={() => setOpen(!open)}>{open ? "Show less" : `${s.home.length - 3} more ideas`}</button>}
        {s.otc?.length > 0 && (
          <>
            <h4 style={{ marginTop: 14 }}><Pill size={15} /> Over the counter options</h4>
            {s.otc.map((o) => (
              <div className="otc" key={o.key}>
                <div className="grow">
                  <div style={{ fontWeight: 700 }}>{o.brands[0] || o.name} <span className="faint" style={{ fontWeight: 400 }}>{o.brands.length ? o.name.toLowerCase() : ""}</span></div>
                  {o.reasons?.map((r) => <div key={r} className="small" style={{ color: "var(--ink-2)" }}>Heads up: {r}.</div>)}
                </div>
                {o.at_home && <span className="pill">At home</span>}
                {o.level === "caution" && <span className="pill caution">Check first</span>}
              </div>
            ))}
          </>
        )}
        {s.skipped?.length > 0 && (
          <p className="small faint" style={{ marginTop: 8 }}>
            Left out: {s.skipped.map((o) => `${o.brands[0] || o.name} (${o.reasons[0]})`).join("; ")}.
          </p>
        )}
        <p className="small" style={{ marginTop: 10, color: "var(--ink-2)" }}>Get care if {s.doctor_if}.</p>
      </div>
      {s.otc?.length > 0 && <div className="doc-line">{s.doctor_line}{!s.has_meds_on_file && " Add your medicines in Me so I can check for clashes."}</div>}
    </div>
  );
}

export function MoodCard({ mood, compact }) {
  const [done, setDone] = useState(null);
  if (!mood) return null;
  const vote = async (activity) => {
    setDone(activity);
    await api("/moods/feedback/", { method: "POST", body: { mood_key: mood.key, activity, helped: true } }).catch(() => {});
  };
  return (
    <div className="panel-euc" style={{ alignSelf: "stretch" }}>
      <div className="small muted" style={{ fontWeight: 700 }}>{mood.label}</div>
      <div className="display" style={{ fontSize: 24, margin: "4px 0 6px" }}>{mood.do}</div>
      <p className="small" style={{ color: "var(--ink-2)" }}>{mood.why}</p>
      {!compact && (
        <div className="chips" style={{ marginTop: 12 }}>
          {[mood.do, ...(mood.more || [])].map((a) => (
            <button key={a} className={`chip ${done === a ? "on" : ""}`} onClick={() => vote(a)}>
              {done === a && <Check size={14} />}{a}
            </button>
          ))}
        </div>
      )}
      {done && <p className="tiny" style={{ marginTop: 8 }}>Saved. I will suggest this first next time.</p>}
    </div>
  );
}

export function SafetyCard({ payload }) {
  return (
    <div className="sheet" style={{ alignSelf: "stretch", background: "var(--plum-soft)", borderColor: "transparent" }}>
      <div className="row" style={{ marginBottom: 10 }}>
        <AlertTriangle size={18} color="var(--plum)" />
        <strong>{payload.type === "crisis" ? "Talk to someone now" : "This needs care, not home remedies"}</strong>
      </div>
      {payload.reasons?.length > 0 && <p className="small" style={{ marginBottom: 10 }}>Because you mentioned {payload.reasons.join(" and ")}.</p>}
      <div className="row wrap">
        {(payload.resources || []).map((r) => (
          <a key={r.href} href={r.href} className="btn plum sm" style={{ textDecoration: "none" }}><Phone size={15} /> {r.label}</a>
        ))}
      </div>
    </div>
  );
}

export function HistoryCard({ payload }) {
  if (!payload?.cards?.length && !payload?.patterns?.length) return null;
  return (
    <div className="sheet" style={{ alignSelf: "stretch" }}>
      <div className="row" style={{ marginBottom: 8 }}><Sparkles size={16} color="var(--euc)" /><strong>From your logs{payload.period ? `, ${payload.period}` : ""}</strong></div>
      {payload.cards?.map((c) => (
        <div key={c.label} style={{ marginBottom: 10 }}>
          <div className="row between"><span style={{ fontWeight: 700 }}>{c.label}</span><span className="num" style={{ fontSize: 20 }}>{c.count}x</span></div>
          {c.helped?.length > 0 && <div className="small muted">Helped most: {c.helped.slice(0, 3).map((h) => h.item).join(", ")}</div>}
          {c.triggers?.length > 0 && <div className="chips" style={{ marginTop: 6 }}>{c.triggers.map((t) => <span key={t} className="chip trigger">{t}</span>)}</div>}
        </div>
      ))}
      {payload.patterns?.map((p) => <div key={p} className="note small" style={{ marginTop: 8 }}>{p}</div>)}
    </div>
  );
}

export function EpisodeLine({ e }) {
  return (
    <div className="row" style={{ alignItems: "flex-start", padding: "10px 0" }}>
      <Leaf size={16} color="var(--plum)" style={{ marginTop: 3 }} />
      <div className="grow">
        <div style={{ fontWeight: 700 }}>{e.label} <span className="faint" style={{ fontWeight: 400 }}>{SEV[e.severity]}</span></div>
        {e.triggers?.length > 0 && <div className="small muted">Linked to {e.triggers.join(", ").toLowerCase()}</div>}
        {e.tried?.length > 0 && <div className="small muted">Tried {e.tried.join(", ")}</div>}
      </div>
      <span className={`pill ${e.outcome === "worse" ? "plum" : e.outcome === "same" ? "caution" : ""}`}>
        {e.outcome === "unknown" ? "Open" : e.outcome[0].toUpperCase() + e.outcome.slice(1)}
      </span>
    </div>
  );
}

export { SEV, shortDate };
