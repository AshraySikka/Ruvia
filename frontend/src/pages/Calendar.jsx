import { addMonths, endOfMonth, format, getDay, isAfter, parseISO, startOfMonth } from "date-fns";
import { BarChart3, ChevronLeft, ChevronRight, CloudSun, Droplet, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { EpisodeLine } from "../components/Cards";
import { Sheet, Skeleton, TopBar } from "../components/ui";
import { api } from "../lib/api";
import { longDate, scoreTone, timeLabel } from "../lib/format";

export default function CalendarPage() {
  const loc = useLocation();
  const nav = useNavigate();
  const [month, setMonth] = useState(() => startOfMonth(new Date()));
  const [data, setData] = useState(null);
  const openDay = new URLSearchParams(loc.search).get("day");

  const load = useCallback(() => {
    setData(null);
    api(`/calendar/?month=${format(month, "yyyy-MM")}`).then(setData).catch(() => setData({ days: [], summary: {} }));
  }, [month]);
  useEffect(() => { load(); }, [load]);

  const first = startOfMonth(month);
  const lead = (getDay(first) + 6) % 7; // weeks start Monday
  const todayStr = format(new Date(), "yyyy-MM-dd");
  const canNext = !isAfter(addMonths(month, 1), endOfMonth(new Date()));

  return (
    <div className="page">
      <TopBar title="Calendar" right={<Link to="/insights" className="icon-btn" aria-label="Insights"><BarChart3 size={20} /></Link>} />
      <div className="row between" style={{ marginBottom: 14 }}>
        <button className="icon-btn" aria-label="Previous month" onClick={() => setMonth(addMonths(month, -1))}><ChevronLeft size={20} /></button>
        <div className="center">
          <h2>{format(month, "MMMM yyyy")}</h2>
          {data?.summary?.logged > 0 && <div className="small muted">{data.summary.logged} days logged, average {data.summary.average}%</div>}
        </div>
        <button className="icon-btn" aria-label="Next month" disabled={!canNext} style={{ opacity: canNext ? 1 : 0.35 }} onClick={() => setMonth(addMonths(month, 1))}><ChevronRight size={20} /></button>
      </div>

      {!data ? <Skeleton h={340} /> : (
        <div className="cal" role="grid" aria-label={format(month, "MMMM yyyy")}>
          {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <div key={i} className="dow" aria-hidden>{d}</div>)}
          {Array.from({ length: lead }).map((_, i) => <div key={`e${i}`} className="day empty" />)}
          {data.days.map((d) => {
            const future = d.date > todayStr;
            const cls = ["day", future && "future", d.date === todayStr && "today", d.period === "actual" && "period", d.period === "predicted" && "predicted"].filter(Boolean).join(" ");
            return (
              <button key={d.date} className={cls} style={!future ? { background: scoreTone(d.overall) } : undefined}
                onClick={() => nav(`/calendar?day=${d.date}`)} aria-label={`${longDate(d.date)}${d.overall != null ? `, ${d.overall}%` : ""}${d.tags.length ? `, ${d.tags.map((t) => t.label).join(", ")}` : ""}`}>
                <span>{parseISO(d.date).getDate()}</span>
                {d.overall != null && <span className="sc">{d.overall}</span>}
                <span className="dots">
                  {d.tags.filter((t) => t.kind === "symptom").slice(0, 3).map((t) => <i key={t.label} />)}
                  {d.dates.length > 0 && <i className="d" />}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="legend" style={{ marginTop: 14 }}>
        <span><i style={{ background: "var(--heat-0)" }} />Hard day</span>
        <span><i style={{ background: "var(--heat-2)" }} />Okay</span>
        <span><i style={{ background: "var(--heat-4)" }} />Good day</span>
        <span><i style={{ background: "var(--plum)", borderRadius: "50%", width: 8, height: 8 }} />Symptom</span>
        <span><i style={{ background: "var(--rose)", height: 4 }} />Period</span>
        <span><i style={{ background: "color-mix(in srgb, var(--rose) 45%, transparent)", height: 4 }} />Predicted</span>
      </div>

      {data && <TagStrip days={data.days} />}

      <DaySheet day={openDay} onClose={() => { nav("/calendar", { replace: true }); load(); }} />
    </div>
  );
}

function TagStrip({ days }) {
  const counts = {};
  days.forEach((d) => d.tags.forEach((t) => { if (t.kind === "symptom") counts[t.label] = (counts[t.label] || 0) + 1; }));
  const list = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!list.length) return null;
  return (
    <section style={{ marginTop: 26 }}>
      <div className="section-head"><h2>This month</h2></div>
      <div className="chips">{list.map(([l, n]) => <span key={l} className="chip symptom">{l} <span style={{ opacity: 0.7 }}>{n}</span></span>)}</div>
    </section>
  );
}

function DaySheet({ day, onClose }) {
  const [d, setD] = useState(null);
  const [adding, setAdding] = useState("");
  const load = useCallback(() => { if (day) api(`/days/${day}/`).then(setD).catch(() => setD(null)); }, [day]);
  useEffect(() => { setD(null); load(); }, [load]);

  const addTag = async (e) => {
    e.preventDefault();
    if (!adding.trim()) return;
    await api(`/days/${day}/tags/`, { method: "POST", body: { label: adding.trim() } });
    setAdding("");
    load();
  };
  const removeTag = async (id) => { await api(`/days/${day}/tags/${id}/`, { method: "DELETE" }); load(); };

  const s = d?.log?.scores;
  return (
    <Sheet open={!!day} onClose={onClose} label="Day details">
      {!d ? <Skeleton h={240} /> : (
        <div className="stack">
          <div className="row between">
            <h2>{longDate(d.date)}</h2>
            {s?.overall != null && <span className="num" style={{ fontSize: 30, padding: "2px 12px", borderRadius: 14, background: scoreTone(s.overall) }}>{s.overall}%</span>}
          </div>
          {s && s.overall != null && (
            <p className="small muted">
              Physical {s.physical ?? "--"}% ({s.physical_source === "estimate" ? "estimated" : "self-rated"}), mental {s.mental ?? "--"}% ({s.mental_source === "estimate" ? "estimated" : "self-rated"})
              {d.log.sleep_hours ? `, slept ${d.log.sleep_hours} h` : ""}
            </p>
          )}
          {d.period && <span className="chip" style={{ background: "var(--rose-soft)", borderColor: "transparent", alignSelf: "flex-start" }}>{d.period === "actual" ? "Period day" : "Period predicted"}</span>}

          <div>
            <h3 style={{ marginBottom: 8 }}>Tags</h3>
            <div className="chips">
              {d.tags.map((t) => (
                <span key={t.id} className={`chip ${t.kind}`}>{t.label}
                  <button aria-label={`Remove ${t.label}`} onClick={() => removeTag(t.id)}><X size={13} /></button>
                </span>
              ))}
              {!d.tags.length && <span className="faint">No tags yet.</span>}
            </div>
            <form onSubmit={addTag} className="row" style={{ marginTop: 10 }}>
              <input className="input" value={adding} onChange={(e) => setAdding(e.target.value)} placeholder="Add a tag, like Migraine" style={{ minHeight: 44 }} />
              <button className="icon-btn" aria-label="Add tag" style={{ background: "var(--euc)", color: "var(--euc-ink)", flex: "none" }}><Plus size={18} /></button>
            </form>
          </div>

          {d.episodes.length > 0 && <div><h3>Symptoms</h3>{d.episodes.map((e) => <EpisodeLine key={e.id} e={e} />)}</div>}

          {d.checkins.length > 0 && (
            <div>
              <h3 style={{ marginBottom: 8 }}>What you said</h3>
              {d.checkins.map((c) => <p key={c.id} className="note neutral small" style={{ marginBottom: 8 }}>"{c.text}" <span className="faint">{timeLabel(c.at)}{c.source === "voice" ? ", voice" : ""}</span></p>)}
            </div>
          )}

          <div className="row wrap" style={{ gap: 14, color: "var(--ink-2)" }}>
            <span className="row small" style={{ gap: 6 }}><Droplet size={16} color="var(--water)" />{d.water.total} ml of {d.water.goal}</span>
            {d.weather && <span className="row small" style={{ gap: 6 }}><CloudSun size={16} />{Math.round(d.weather.temp_max)}°C{d.weather.pressure_change != null && d.weather.pressure_change <= -4 ? ", pressure dropped" : ""}</span>}
          </div>
          {d.dates.map((h) => <p key={h.title} className="note small">{h.title}{h.time ? ` at ${h.time}` : ""}</p>)}
        </div>
      )}
    </Sheet>
  );
}
