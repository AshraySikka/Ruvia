import { format, parseISO } from "date-fns";

/** Two line trend: physical and mental. Gaps where a day was not logged. */
export default function Trend({ series, height = 150 }) {
  const w = 340, h = height, pad = { l: 26, r: 8, t: 10, b: 22 };
  const n = series.length;
  const x = (i) => pad.l + (i * (w - pad.l - pad.r)) / Math.max(1, n - 1);
  const y = (v) => pad.t + (1 - v / 100) * (h - pad.t - pad.b);
  const path = (key) => {
    let dstr = "", pen = false;
    series.forEach((p, i) => {
      if (p[key] == null) { pen = false; return; }
      dstr += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(p[key]).toFixed(1)} `;
      pen = true;
    });
    return dstr;
  };
  const every = n > 10 ? Math.ceil(n / 6) : 1;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Physical and mental scores over time">
      {[25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={pad.l} x2={w - pad.r} y1={y(v)} y2={y(v)} stroke="var(--rule)" strokeDasharray={v === 100 ? "" : "3 4"} />
          <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize="10" fill="var(--ink-3)">{v}</text>
        </g>
      ))}
      <path d={path("physical")} fill="none" stroke="var(--euc)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d={path("mental")} fill="none" stroke="var(--plum)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      {series.map((p, i) => (
        <g key={p.date}>
          {p.physical != null && <circle cx={x(i)} cy={y(p.physical)} r={n > 14 ? 0 : 3.2} fill="var(--euc)" />}
          {p.mental != null && <circle cx={x(i)} cy={y(p.mental)} r={n > 14 ? 0 : 3.2} fill="var(--plum)" />}
          {p.symptoms?.length > 0 && <circle cx={x(i)} cy={h - pad.b + 2} r="2.4" fill="var(--saffron)" />}
          {i % every === 0 && <text x={x(i)} y={h - 4} textAnchor="middle" fontSize="10" fill="var(--ink-3)">{format(parseISO(p.date), n > 10 ? "MMM d" : "EEE")}</text>}
        </g>
      ))}
    </svg>
  );
}
