import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Clock, Mic, PencilLine } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { HistoryCard, MoodCard, RemedyCard, SafetyCard } from "../components/Cards";
import { Logo, Seg, useToast } from "../components/ui";
import Voice from "../components/Voice";
import { api, queued } from "../lib/api";
import { dayLabel, timeLabel } from "../lib/format";

const ASK_IDEAS = ["What helped my acidity last time?", "Why have I been feeling tired lately?", "How often do I get headaches?", "What should I discuss with my doctor?"];
const LOG_IDEAS = ["Headache since lunch", "Feeling great today", "Acidity after dinner", "Stressed and can't focus"];

export default function Chat() {
  const loc = useLocation();
  const toast = useToast();
  const [msgs, setMsgs] = useState(null);
  const [status, setStatus] = useState(null);
  const [text, setText] = useState("");
  const [mode, setMode] = useState("log");
  const [busy, setBusy] = useState(false);
  const [voice, setVoice] = useState(new URLSearchParams(loc.search).get("voice") === "1");
  const end = useRef(null);
  const box = useRef(null);

  useEffect(() => {
    api("/chat/").then((r) => { setMsgs(r.messages); setStatus(r.status); }).catch(() => setMsgs([]));
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: msgs?.length > 2 ? "smooth" : "auto", block: "end" }); }, [msgs, busy]);

  const send = async (body, source = "text") => {
    const t = (body ?? text).trim();
    if (!t || busy) return;
    setText("");
    setVoice(false);
    const temp = { id: `t${Date.now()}`, role: "user", text: t, source, created_at: new Date().toISOString(), payload: {} };
    setMsgs((m) => [...(m || []), temp]);
    setBusy(true);
    try {
      const r = await queued("/chat/", { text: t, source, mode: mode === "ask" ? "ask" : "auto", client_id: crypto.randomUUID?.() || String(Date.now()) });
      if (r?.queued) {
        toast("Saved offline. I will reply once you are back online.");
        setMsgs((m) => m.map((x) => (x.id === temp.id ? { ...x, pending: true } : x)));
      } else {
        setMsgs((m) => [...m.filter((x) => x.id !== temp.id), ...r.messages]);
      }
    } catch (e) {
      toast(e.message);
      setMsgs((m) => m.filter((x) => x.id !== temp.id));
      setText(t);
    } finally { setBusy(false); }
  };

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer: fine)").matches) { e.preventDefault(); send(); } };
  useEffect(() => { const el = box.current; if (el) { el.style.height = "auto"; el.style.height = `${Math.min(140, el.scrollHeight)}px`; } }, [text]);

  let lastDay = null;
  return (
    <div className="page" style={{ paddingBottom: 0, display: "flex", flexDirection: "column", minHeight: "100dvh" }}>
      <header className="row between" style={{ marginBottom: 14 }}>
        <div className="row"><Logo size={34} /><div><h1 style={{ fontSize: 22 }}>Talk to Ruvia</h1>
          <div className="tiny faint">{status && status.providers.length === 0 ? "Running on built-in replies until API keys are added" : "Saved to your diary as you go"}</div></div></div>
      </header>
      <Seg label="What do you want to do" value={mode} onChange={setMode} options={[{ value: "log", label: "Log how I feel" }, { value: "ask", label: "Ask my history" }]} />

      <div className="chat grow" style={{ marginTop: 18 }}>
        {msgs === null && <div className="faint center">Loading your conversation</div>}
        {msgs?.length === 0 && (
          <div className="empty-state">
            <h2 style={{ marginBottom: 6 }}>Start with how you feel</h2>
            <p>Type or talk. I will pull out tags for your calendar and suggest what to try.</p>
          </div>
        )}
        {msgs?.map((m) => {
          const day = dayLabel(m.created_at);
          const showDay = day !== lastDay;
          lastDay = day;
          return (
            <Fragment key={m.id}>
              {showDay && <div className="tiny faint center" style={{ margin: "8px 0" }}>{day}</div>}
              <Message m={m} />
            </Fragment>
          );
        })}
        <AnimatePresence>
          {busy && (
            <motion.div className="bubble them typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} aria-label="Ruvia is writing">
              <span /><span /><span />
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={end} />
      </div>

      <div className="composer">
        {voice ? (
          <Voice autoStart onConfirm={(t) => send(t, "voice")} onCancel={() => setVoice(false)} />
        ) : (
          <>
            {!text && !busy && (
              <div className="chips" style={{ marginBottom: 10, flexWrap: "nowrap", overflowX: "auto", paddingBottom: 2 }}>
                {(mode === "ask" ? ASK_IDEAS : LOG_IDEAS).map((q) => (
                  <button key={q} className="chip" style={{ whiteSpace: "nowrap" }} onClick={() => (mode === "ask" ? send(q) : setText(q))}>{q}</button>
                ))}
              </div>
            )}
            <div className="composer-box">
              <textarea ref={box} rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey}
                placeholder={mode === "ask" ? "Ask about your own health history" : "How are you feeling?"} aria-label="Message" />
              {text.trim() ? (
                <button className="send" onClick={() => send()} aria-label="Send" disabled={busy}><ArrowUp size={20} /></button>
              ) : (
                <button className="send plum" onClick={() => setVoice(true)} aria-label="Record a voice check-in"><Mic size={20} /></button>
              )}
            </div>
          </>
        )}
      </div>
      <div style={{ height: "calc(80px + env(safe-area-inset-bottom, 0px))" }} aria-hidden />
    </div>
  );
}

function Message({ m }) {
  const p = m.payload || {};
  if (m.role === "user") {
    return (
      <>
        <motion.div className="bubble me" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>{m.text}</motion.div>
        <div className="bubble-meta me">{m.source === "voice" ? "Voice, " : ""}{m.pending ? "waiting to sync" : timeLabel(m.created_at)}</div>
      </>
    );
  }
  const today = m.created_at.slice(0, 10);
  return (
    <>
      <motion.div className={`bubble them ${m.kind === "safety" ? "safety" : ""}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>{m.text}</motion.div>
      {(p.type === "crisis" || p.type === "urgent" || p.resources?.length > 0) && <SafetyCard payload={p} />}
      {p.tags?.length > 0 && (
        <div className="row wrap" style={{ gap: 6 }}>
          {p.tags.map((t) => <span key={t} className="chip symptom">{t}</span>)}
          <Link to={`/calendar?day=${today}`} className="chip" style={{ textDecoration: "none" }}><PencilLine size={13} /> Edit tags</Link>
        </div>
      )}
      {p.suggestions?.map((s) => <RemedyCard key={s.key} s={s} />)}
      {p.mood && <MoodCard mood={p.mood} />}
      {p.type === "history" && <HistoryCard payload={p} />}
      {p.followup && (
        <Link to={`/followup/${p.followup.id}`} className="chip" style={{ alignSelf: "flex-start", textDecoration: "none" }}>
          <Clock size={14} /> Check-in set for {timeLabel(p.followup.due_at)}. Answer now
        </Link>
      )}
    </>
  );
}
