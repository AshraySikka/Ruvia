import { FileDown, MapPin, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Trend from "../components/Trend";
import { Seg, Skeleton, TopBar, useToast } from "../components/ui";
import { api, downloadFile } from "../lib/api";

export default function Insights() {
  const [range, setRange] = useState("week");
  const [d, setD] = useState(null);
  const toast = useToast();
  useEffect(() => { setD(null); api(`/insights/?range=${range}`).then(setD).catch(() => setD(false)); }, [range]);

  const report = async () => {
    toast("Making your summary");
    try { await downloadFile("/report.pdf?days=90", "ruvia-doctor-summary.pdf"); } catch { toast("Could not make the PDF. Try again."); }
  };

  const avg = (k) => {
    const v = (d?.series || []).map((r) => r[k]).filter((x) => x != null);
    return v.length ? Math.round(v.reduce((a, b) => a + b, 0) / v.length) : null;
  };

  return (
    <div className="page">
      <TopBar title="Insights" back="/" />
      <Seg label="Range" value={range} onChange={setRange} options={[{ value: "week", label: "This week" }, { value: "month", label: "Last 30 days" }]} />
      {d === null && <div className="stack" style={{ marginTop: 18 }}><Skeleton h={190} /><Skeleton h={140} /></div>}
      {d === false && <p className="error" style={{ marginTop: 18 }}>Could not load insights. Pull down to try again.</p>}
      {d && (
        <div className="stack-lg" style={{ marginTop: 18 }}>
          <section className="sheet">
            <div className="row" style={{ gap: 18, marginBottom: 8 }}>
              <div><div className="num" style={{ fontSize: 28, color: "var(--euc)" }}>{avg("physical") ?? "--"}</div><div className="tiny muted">avg physical</div></div>
              <div><div className="num" style={{ fontSize: 28, color: "var(--plum)" }}>{avg("mental") ?? "--"}</div><div className="tiny muted">avg mental</div></div>
              <div className="grow" />
              <div className="legend"><span><i style={{ background: "var(--euc)" }} />Body</span><span><i style={{ background: "var(--plum)" }} />Mind</span><span><i style={{ background: "var(--saffron)", borderRadius: "50%" }} />Symptom</span></div>
            </div>
            <Trend series={d.series} />
          </section>

          <section>
            <div className="section-head"><h2>What changed this week</h2></div>
            <div className="stack">
              {d.what_changed.lines.length ? d.what_changed.lines.map((l) => (
                <div key={l.text} className={`note ${l.tone}`}>
                  {l.tone === "good" ? <TrendingUp size={15} style={{ display: "inline", verticalAlign: -2, marginRight: 6 }} /> : l.tone === "watch" ? <TrendingDown size={15} style={{ display: "inline", verticalAlign: -2, marginRight: 6 }} /> : null}
                  {l.text}
                </div>
              )) : <p className="faint">Log a few more days and I will compare your weeks.</p>}
            </div>
          </section>

          <section>
            <div className="section-head"><h2>Compared with your usual</h2></div>
            {d.baseline.ready ? (
              <div className="stack">
                <div className="row wrap" style={{ gap: 10 }}>
                  {[["Physical", d.baseline.usual.physical, "%"], ["Mental", d.baseline.usual.mental, "%"], ["Water", d.baseline.usual.water, " ml"], ["Sleep", d.baseline.usual.sleep, " h"]].map(([k, v, u]) =>
                    v != null && <div key={k} className="sheet tight" style={{ flex: "1 1 40%" }}><div className="tiny muted">Your usual {k.toLowerCase()}</div><div className="num" style={{ fontSize: 22 }}>{k === "Sleep" ? v : Math.round(v)}{u}</div></div>)}
                </div>
                {d.baseline.notes.map((n) => <div key={n.text} className={`note ${n.tone}`}>{n.text}</div>)}
                {!d.baseline.notes.length && <p className="note neutral">This week looks like your usual.</p>}
              </div>
            ) : <p className="faint">I need about {d.baseline.needs_days} more days of logs to learn your usual.</p>}
          </section>

          <section>
            <div className="section-head"><h2>Patterns in your logs</h2></div>
            {d.patterns.ready ? (
              d.patterns.items.length ? (
                <div className="stack">
                  {d.patterns.items.map((p) => (
                    <div key={p.text} className="sheet tight">
                      <div className="row between" style={{ marginBottom: 6 }}>
                        <strong>{p.title}</strong>
                        <span className={`pill ${p.strength === "strong" ? "plum" : "caution"}`}>{p.strength === "strong" ? "Strong" : "Worth watching"}</span>
                      </div>
                      <p className="small muted">{p.text}</p>
                      <PatternBar a={p.hits / p.condition_days} b={p.other_hits / p.other_days} />
                    </div>
                  ))}
                  <p className="small faint">{d.patterns.note}</p>
                </div>
              ) : <p className="faint">No clear patterns yet. That can be good news.</p>
            ) : (
              <div className="sheet">
                <Sparkles size={18} color="var(--euc)" />
                <p style={{ marginTop: 6 }}>Patterns show up after about three weeks of logs. {d.patterns.needs_days} days to go.</p>
              </div>
            )}
          </section>

          {!d.has_location && (
            <Link to="/me/profile" className="sheet row" style={{ textDecoration: "none", color: "inherit" }}>
              <MapPin size={20} color="var(--water)" />
              <div className="grow"><strong>Add your city</strong><div className="small muted">So I can look for weather links, like headaches when the air pressure drops.</div></div>
            </Link>
          )}

          <button className="btn ghost block" onClick={report}><FileDown size={18} /> Doctor summary PDF</button>
        </div>
      )}
    </div>
  );
}

function PatternBar({ a, b }) {
  return (
    <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
      <div className="row" style={{ gap: 8 }}><span className="tiny" style={{ width: 64 }}>With it</span><div className="progress grow"><i style={{ width: `${Math.round(a * 100)}%`, background: "var(--plum)" }} /></div><span className="tiny num">{Math.round(a * 100)}%</span></div>
      <div className="row" style={{ gap: 8 }}><span className="tiny" style={{ width: 64 }}>Other days</span><div className="progress grow"><i style={{ width: `${Math.round(b * 100)}%`, background: "var(--ink-3)" }} /></div><span className="tiny num">{Math.round(b * 100)}%</span></div>
    </div>
  );
}
