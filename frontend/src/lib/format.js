import { format, formatDistanceToNowStrict, isToday, isYesterday, parseISO } from "date-fns";

export const d = (iso) => (typeof iso === "string" ? parseISO(iso) : iso);
export const dayLabel = (iso) => { const x = d(iso); return isToday(x) ? "Today" : isYesterday(x) ? "Yesterday" : format(x, "EEE, MMM d"); };
export const timeLabel = (iso) => format(d(iso), "h:mm a");
export const longDate = (iso) => format(d(iso), "EEEE, MMMM d");
export const shortDate = (iso) => format(d(iso), "MMM d");
export const ago = (iso) => formatDistanceToNowStrict(d(iso), { addSuffix: true });
export const todayISO = () => format(new Date(), "yyyy-MM-dd");

const PHYS = ["Running on empty", "Rough", "Rough", "Meh", "Meh", "Getting by", "Getting by", "Pretty good", "Pretty good", "Strong", "Thriving"];
const MENT = ["Heavy", "Heavy", "Foggy", "Foggy", "Wobbly", "Okay", "Okay", "Good", "Good", "Bright", "Glowing"];
export const physWord = (n) => PHYS[n] ?? "";
export const mentWord = (n) => MENT[n] ?? "";

export function scoreTone(v) {
  if (v == null) return "var(--sheet)";
  if (v < 40) return "var(--heat-0)";
  if (v < 55) return "var(--heat-1)";
  if (v < 70) return "var(--heat-2)";
  if (v < 85) return "var(--heat-3)";
  return "var(--heat-4)";
}

export function initials(name = "") { return name.trim().slice(0, 1).toUpperCase() || "R"; }
export function avatarStyle(hue = 150) {
  return { background: `hsl(${hue} 32% 82%)`, color: `hsl(${hue} 40% 24%)` };
}
export function vibrate(ms = 12) { try { navigator.vibrate?.(ms); } catch { /* ignore */ } }
