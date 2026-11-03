import { Bell, CalendarClock, Droplet, Heart, Moon, Sparkles, Stethoscope } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Skeleton, TopBar } from "../components/ui";
import { api } from "../lib/api";
import { ago } from "../lib/format";

const ICON = { water: Droplet, followup: Stethoscope, cycle: Moon, care: Heart, nudge: Heart, weekly: Sparkles, date: CalendarClock, goal: Sparkles };

export default function Inbox() {
  const nav = useNavigate();
  const [d, setD] = useState(null);
  useEffect(() => { api("/notifications/").then((r) => { setD(r); if (r.unread) api("/notifications/", { method: "POST", body: { all: true } }); }); }, []);
  return (
    <div className="page">
      <TopBar title="Inbox" back="/" />
      {!d ? <Skeleton h={300} /> : d.items.length === 0 ? (
        <div className="empty-state"><Bell size={30} style={{ margin: "0 auto 10px" }} /><p>Reminders and messages from your circle show up here, even if push is off.</p></div>
      ) : (
        <div className="list">
          {d.items.map((n) => {
            const Icon = ICON[n.kind] || Bell;
            return (
              <button key={n.id} className="list-row" onClick={() => nav(n.url)} style={!n.read ? { background: "var(--sheet-2)" } : undefined}>
                <span className="ico"><Icon size={17} /></span>
                <div className="grow"><div style={{ fontWeight: 700 }}>{n.title}</div><div className="small muted">{n.body}</div></div>
                <span className="tiny faint" style={{ whiteSpace: "nowrap" }}>{ago(n.at)}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
