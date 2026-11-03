import { AnimatePresence, motion } from "framer-motion";
import { Mic, RotateCcw, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { vibrate } from "../lib/format";

function pickMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  return types.find((t) => window.MediaRecorder?.isTypeSupported?.(t)) || "";
}

/** Records, sends to the server for transcription, then shows the text for a one tap confirm. */
export default function Voice({ onConfirm, autoStart, onCancel }) {
  const [state, setState] = useState("idle"); // idle, recording, working, confirm, error
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [secs, setSecs] = useState(0);
  const rec = useRef(null);
  const chunks = useRef([]);
  const timer = useRef();
  const speech = useRef(null);

  useEffect(() => { if (autoStart) start(); return () => stopTracks(); }, []); // eslint-disable-line

  function stopTracks() {
    clearInterval(timer.current);
    rec.current?.stream?.getTracks().forEach((t) => t.stop());
  }

  async function start() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickMime();
      const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = () => upload(new Blob(chunks.current, { type: r.mimeType || "audio/webm" }));
      r.start();
      rec.current = r;
      setSecs(0);
      timer.current = setInterval(() => setSecs((s) => (s >= 119 ? (stop(), s) : s + 1)), 1000);
      setState("recording");
      vibrate(20);
    } catch {
      setError("Microphone access is off. Allow it in your browser settings, or type instead.");
      setState("error");
    }
  }

  function stop() {
    vibrate(10);
    clearInterval(timer.current);
    if (rec.current?.state === "recording") rec.current.stop();
    rec.current?.stream?.getTracks().forEach((t) => t.stop());
    setState("working");
  }

  async function upload(blob) {
    const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
    const form = new FormData();
    form.append("audio", blob, `voice.${ext}`);
    try {
      const { text: t } = await api("/transcribe/", { method: "POST", form });
      if (!t) throw new Error("I could not hear anything. Try again a little closer to the mic.");
      setText(t);
      setState("confirm");
    } catch (e) {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (e.status === 503 && SR) return deviceSpeech(SR);
      setError(e.message || "Could not turn that into text. Try again or type instead.");
      setState("error");
    }
  }

  function deviceSpeech(SR) {
    // Fallback when the server has no voice key: the browser's own speech recognition, if it has one.
    const s = new SR();
    s.lang = "en-CA";
    s.interimResults = false;
    s.onresult = (e) => { setText(e.results[0][0].transcript); setState("confirm"); };
    s.onerror = () => { setError("Voice is not set up yet. Type your check-in instead."); setState("error"); };
    speech.current = s;
    setError("Say it once more, I am listening on this device.");
    setState("recording");
    s.start();
  }

  const mmss = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;

  return (
    <div className="panel-plum" style={{ padding: 20 }}>
      <AnimatePresence mode="wait">
        {(state === "idle" || state === "recording" || state === "working") && (
          <motion.div key="rec" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="row" style={{ gap: 16 }}>
            <button className={`orb ${state === "recording" ? "live" : ""}`} onClick={state === "recording" ? stop : start}
              disabled={state === "working"} aria-label={state === "recording" ? "Stop recording" : "Start recording"}>
              <span className="blob" />{state === "recording" && <span className="ring" />}
              {state === "recording" ? <Square size={24} fill="currentColor" /> : <Mic size={28} />}
            </button>
            <div className="grow">
              <div className="display" style={{ fontSize: 20 }}>
                {state === "recording" ? "Listening" : state === "working" ? "Writing it down" : "Tap and talk"}
              </div>
              <div className="small" style={{ opacity: 0.85 }}>
                {state === "recording" ? `${mmss}. Tap again when you are done.` : state === "working" ? "One moment." : "Say how you feel. You will see the text before it saves."}
              </div>
              {error && state === "recording" && <div className="small" style={{ marginTop: 6 }}>{error}</div>}
            </div>
          </motion.div>
        )}
        {state === "confirm" && (
          <motion.div key="ok" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
            <div className="small" style={{ fontWeight: 700, marginBottom: 8 }}>Did I get that right?</div>
            <textarea className="textarea" value={text} onChange={(e) => setText(e.target.value)} aria-label="Transcript"
              style={{ background: "var(--plum-panel-ink)", color: "var(--ink)", borderColor: "transparent" }} />
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn light grow" onClick={() => onConfirm(text.trim())} disabled={!text.trim()}>Save check-in</button>
              <button className="icon-btn" aria-label="Record again" onClick={() => { setText(""); start(); }} style={{ background: "transparent", borderColor: "var(--plum-panel-ink)", color: "var(--plum-panel-ink)" }}>
                <RotateCcw size={18} />
              </button>
            </div>
          </motion.div>
        )}
        {state === "error" && (
          <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <p style={{ marginBottom: 12 }}>{error}</p>
            <div className="row">
              <button className="btn light" onClick={start}>Try again</button>
              {onCancel && <button className="btn sm" style={{ background: "transparent", color: "var(--plum-panel-ink)" }} onClick={onCancel}>Type instead</button>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
