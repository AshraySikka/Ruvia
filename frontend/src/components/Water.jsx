import { Minus, Plus } from "lucide-react";
import { vibrate } from "../lib/format";

export default function Water({ total = 0, goal = 2000, onAdd, onUndo, compact }) {
  const pct = Math.min(100, Math.round((total / goal) * 100));
  const glasses = Math.round(total / 250);
  return (
    <section className="water" aria-label={`Water ${total} of ${goal} millilitres`}>
      <div className="fill" style={{ height: `${Math.max(8, pct)}%` }}>
        <svg className="wave" viewBox="0 0 400 16" preserveAspectRatio="none" aria-hidden>
          <path d="M0 8 Q25 0 50 8 T100 8 T150 8 T200 8 T250 8 T300 8 T350 8 T400 8 V16 H0Z" fill="color-mix(in srgb, var(--water) 28%, transparent)" />
        </svg>
      </div>
      <div className="content">
        <div className="row between" style={{ alignItems: "flex-start" }}>
          <div>
            <div className="small" style={{ fontWeight: 700, color: "var(--water)" }}>Water today</div>
            <div className="num" style={{ fontSize: 40, lineHeight: 1.05, marginTop: 4 }}>{total.toLocaleString()}<span style={{ fontSize: 17, fontWeight: 600 }}> ml</span></div>
            <div className="small muted">of {goal.toLocaleString()} ml, about {glasses} glass{glasses === 1 ? "" : "es"}</div>
          </div>
          <div className="num" style={{ fontSize: 22, color: "var(--water)" }}>{pct}%</div>
        </div>
        {!compact && (
          <div className="row" style={{ marginTop: 18 }}>
            <button className="btn sm" style={{ background: "var(--water)", color: "var(--sheet)" }} onClick={() => { vibrate(); onAdd(250); }}><Plus size={16} /> Glass</button>
            <button className="btn sm" style={{ background: "var(--sheet)", color: "var(--ink)" }} onClick={() => { vibrate(); onAdd(500); }}><Plus size={16} /> Bottle</button>
            <div className="grow" />
            {total > 0 && <button className="icon-btn" aria-label="Undo last water" onClick={onUndo} style={{ width: 38, height: 38 }}><Minus size={16} /></button>}
          </div>
        )}
      </div>
    </section>
  );
}
