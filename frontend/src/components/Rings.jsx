import { motion } from "framer-motion";

function Ring({ value, size, stroke, color, track, delay = 0 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }} aria-hidden>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
      <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c - (c * v) / 100 }}
        transition={{ duration: 1.1, delay, ease: [0.2, 0.8, 0.2, 1] }} />
    </svg>
  );
}

export default function Rings({ scores, onExplain }) {
  const { physical, mental, overall, physical_source: ps, mental_source: ms } = scores || {};
  const label = (src) => (src === "estimate" ? "estimated" : src === "self" ? "self-rated" : "not rated");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 6 }}>
      <Side value={physical} name="Physical" sub={label(ps)} color="var(--euc)" align="left" />
      <button onClick={onExplain} aria-label={`Overall ${overall ?? "not rated"}. How scores work`} style={{ position: "relative", width: 158, height: 158 }}>
        <div style={{ position: "absolute", inset: 0 }}><Ring value={physical} size={158} stroke={13} color="var(--euc)" track="var(--euc-soft)" /></div>
        <div style={{ position: "absolute", inset: 19 }}><Ring value={mental} size={120} stroke={13} color="var(--plum)" track="var(--plum-soft)" delay={0.15} /></div>
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
          <div>
            <div className="num" style={{ fontSize: 34, lineHeight: 1 }}>{overall ?? "--"}{overall != null && <span style={{ fontSize: 16 }}>%</span>}</div>
            <div className="tiny muted" style={{ marginTop: 3 }}>overall</div>
          </div>
        </div>
      </button>
      <Side value={mental} name="Mental" sub={label(ms)} color="var(--plum)" align="right" />
    </div>
  );
}

function Side({ value, name, sub, color, align }) {
  return (
    <div style={{ textAlign: align }}>
      <div className="num" style={{ fontSize: 28, color }}>{value ?? "--"}<span style={{ fontSize: 14 }}>{value != null ? "%" : ""}</span></div>
      <div style={{ fontWeight: 700, fontSize: 15 }}>{name}</div>
      <div className="tiny faint">{sub}</div>
    </div>
  );
}
