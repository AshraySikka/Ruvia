import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { avatarStyle, initials } from "../lib/format";

const ToastCtx = createContext(() => {});
export function ToastProvider({ children }) {
  const [msg, setMsg] = useState(null);
  const timer = useRef();
  const show = useCallback((text) => {
    setMsg(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 2600);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <AnimatePresence>
        {msg && (
          <motion.div className="toast" role="status" initial={{ opacity: 0, y: 16, x: "-50%" }} animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: 10, x: "-50%" }}>{msg}</motion.div>
        )}
      </AnimatePresence>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

export function Sheet({ open, onClose, children, label }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div className="modal" role="dialog" aria-modal="true" aria-label={label}
            initial={{ y: "100%", x: "-50%" }} animate={{ y: 0, x: "-50%" }} exit={{ y: "100%", x: "-50%" }}
            transition={{ type: "spring", damping: 30, stiffness: 320 }}
            drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => info.offset.y > 120 && onClose()}>
            <div className="grab" />
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function Toggle({ checked, onChange, label }) {
  return <button type="button" role="switch" aria-checked={!!checked} aria-label={label} className="toggle" onClick={() => onChange(!checked)} />;
}

export function Seg({ value, options, onChange, label }) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

export function TopBar({ title, back, right }) {
  const nav = useNavigate();
  return (
    <div className="topbar">
      <div className="row">
        {back && <button className="back" aria-label="Go back" onClick={() => (window.history.length > 1 ? nav(-1) : nav(back))}><ChevronLeft size={20} /></button>}
        <h1 className="title">{title}</h1>
      </div>
      {right}
    </div>
  );
}

export function Avatar({ name, hue, size = 44 }) {
  return <div className="avatar" style={{ ...avatarStyle(hue), width: size, height: size, fontSize: size * 0.42 }} aria-hidden>{initials(name)}</div>;
}

export function Skeleton({ h = 80, style }) { return <div className="skel" style={{ height: h, ...style }} />; }

export function Logo({ size = 28 }) {
  return <img src="/icons/icon-192.png" width={size} height={size} alt="" aria-hidden style={{ borderRadius: size * 0.22, display: "block" }} />;
}

export function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <p className="faint" style={{ marginTop: 6 }}>{hint}</p>}
    </label>
  );
}
