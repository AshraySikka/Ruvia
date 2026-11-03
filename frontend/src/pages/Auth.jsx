import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Logo } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD;
const qs = (loc) => new URLSearchParams(loc.search);

function AuthFrame({ title, sub, children, back = "/" }) {
  return (
    <div className="page" style={{ paddingBottom: 40 }}>
      <div className="row between" style={{ marginBottom: 40 }}>
        <Link to={back} className="row" style={{ textDecoration: "none", color: "var(--ink)" }}><Logo size={30} /><span className="display" style={{ fontSize: 22 }}>Ruvia</span></Link>
      </div>
      <h1 style={{ marginBottom: 8 }}>{title}</h1>
      {sub && <p className="muted" style={{ marginBottom: 26 }}>{sub}</p>}
      {children}
    </div>
  );
}

function useSubmit() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = async (fn) => {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e.message || "Something went wrong. Try again."); } finally { setBusy(false); }
  };
  return { busy, error, run, setError };
}

export function WelcomePage() {
  const { signIn } = useAuth();
  const { busy, error, run } = useSubmit();
  const demo = (email) => run(async () => signIn(await api("/auth/login/", { method: "POST", auth: false, body: { email, password: DEMO_PASSWORD } })));
  return (
    <div className="page" style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", paddingBottom: 32 }}>
      <div className="row" style={{ marginBottom: "auto" }}><Logo size={34} /></div>
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} style={{ margin: "48px 0 36px" }}>
        <div className="hero-word" style={{ fontSize: 76, color: "var(--euc)" }}>Ruvia</div>
        <p className="display" style={{ fontSize: 26, fontWeight: 520, marginTop: 14, lineHeight: 1.2, maxWidth: 360 }}>
          A small health diary for you and the people you love.
        </p>
        <div style={{ marginTop: 28, display: "grid", gap: 14, maxWidth: 380 }}>
          {[
            ["Say how you feel.", "A sentence or a voice note. Ruvia turns it into tags on your calendar."],
            ["Remembers what helped.", "Next time the headache comes back, the thing that worked shows up first."],
            ["Share on your terms.", "Your partner can know you had a rough day without seeing why."],
          ].map(([a, b]) => (
            <div key={a} className="note"><strong>{a}</strong> <span className="muted">{b}</span></div>
          ))}
        </div>
      </motion.div>
      <div style={{ display: "grid", gap: 10 }}>
        <Link to="/signup" className="btn block" style={{ textDecoration: "none" }}>Create an account</Link>
        <Link to="/login" className="btn ghost block" style={{ textDecoration: "none" }}>Sign in</Link>
        {DEMO_PASSWORD && (
          <div className="center" style={{ marginTop: 6 }}>
            <div className="small muted">Try the demo as</div>
            <div className="row" style={{ justifyContent: "center", gap: 20, marginTop: 4 }}>
              <button className="link" disabled={busy} onClick={() => demo("demoruvia@yopmail.com")}>Jane</button>
              <button className="link" disabled={busy} onClick={() => demo("demo1ruvia@yopmail.com")}>Joe</button>
            </div>
          </div>
        )}
        {error && <p className="error center">{error}</p>}
        <Link to="/about" className="faint center" style={{ marginTop: 8 }}>Why it is called Ruvia</Link>
      </div>
    </div>
  );
}

export function SignUpPage() {
  const nav = useNavigate();
  const loc = useLocation();
  const [form, setForm] = useState({ first_name: "", email: qs(loc).get("email") || "", password: "" });
  const { busy, error, run } = useSubmit();
  const submit = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/auth/signup/", { method: "POST", auth: false, body: form });
      nav(`/verify?email=${encodeURIComponent(form.email.trim().toLowerCase())}&purpose=signup`);
    });
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  return (
    <AuthFrame title="Make your diary" sub="We will email you a 6 digit code to confirm it is you.">
      <form onSubmit={submit} className="stack">
        <label className="field"><span>First name</span><input className="input" value={form.first_name} onChange={set("first_name")} autoComplete="given-name" required /></label>
        <label className="field"><span>Email</span><input className="input" type="email" value={form.email} onChange={set("email")} autoComplete="email" required /></label>
        <label className="field"><span>Password</span><input className="input" type="password" value={form.password} onChange={set("password")} autoComplete="new-password" minLength={8} required /></label>
        <p className="faint">At least 8 characters. Avoid common words.</p>
        {error && <p className="error">{error}</p>}
        <button className="btn block" disabled={busy}>{busy ? "Sending code" : "Send my code"}</button>
        <p className="center small muted">Have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </AuthFrame>
  );
}

export function VerifyPage() {
  const loc = useLocation();
  const email = qs(loc).get("email") || "";
  const purpose = qs(loc).get("purpose") || "signup";
  const { signIn } = useAuth();
  const [code, setCode] = useState("");
  const [note, setNote] = useState("");
  const { busy, error, run } = useSubmit();
  const verify = (c) => run(async () => {
    const path = purpose === "login" ? "/auth/login/code/verify/" : "/auth/verify/";
    signIn(await api(path, { method: "POST", auth: false, body: { email, code: c } }));
  });
  useEffect(() => { if (code.length === 6) verify(code); }, [code]); // eslint-disable-line
  const resend = () => run(async () => { const r = await api("/auth/resend/", { method: "POST", auth: false, body: { email, purpose } }); setNote(r.detail); });
  return (
    <AuthFrame title="Check your email" sub={`Enter the 6 digit code we sent to ${email}.`} back="/login">
      <div className="stack">
        <input className="input otp" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} aria-label="6 digit code" autoFocus />
        {error && <p className="error">{error}</p>}
        {note && <p className="small muted">{note}</p>}
        <button className="btn block" disabled={busy || code.length !== 6} onClick={() => verify(code)}>{busy ? "Checking" : "Confirm"}</button>
        <button className="link" onClick={resend} disabled={busy}>Send a new code</button>
      </div>
    </AuthFrame>
  );
}

export function LoginPage() {
  const nav = useNavigate();
  const { signIn } = useAuth();
  const [mode, setMode] = useState("password");
  const [form, setForm] = useState({ email: "", password: "" });
  const { busy, error, run } = useSubmit();
  const submit = (e) => {
    e.preventDefault();
    run(async () => {
      const email = form.email.trim().toLowerCase();
      if (mode === "code") {
        await api("/auth/login/code/", { method: "POST", auth: false, body: { email } });
        nav(`/verify?email=${encodeURIComponent(email)}&purpose=login`);
        return;
      }
      try {
        signIn(await api("/auth/login/", { method: "POST", auth: false, body: { email, password: form.password } }));
      } catch (err) {
        if (err.data?.needs_verification) nav(`/verify?email=${encodeURIComponent(email)}&purpose=signup`);
        else throw err;
      }
    });
  };
  return (
    <AuthFrame title="Welcome back" sub={mode === "code" ? "We will email you a code. No password needed." : null}>
      <form onSubmit={submit} className="stack">
        <label className="field"><span>Email</span><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" required /></label>
        {mode === "password" && (
          <label className="field"><span>Password</span><input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="current-password" required /></label>
        )}
        {error && <p className="error">{error}</p>}
        <button className="btn block" disabled={busy}>{busy ? "One moment" : mode === "code" ? "Email me a code" : "Sign in"}</button>
        <div className="row between">
          <button type="button" className="link" onClick={() => setMode(mode === "code" ? "password" : "code")}>{mode === "code" ? "Use my password" : "Email me a code instead"}</button>
          <Link to="/forgot" className="link">Forgot password</Link>
        </div>
        <p className="center small muted" style={{ marginTop: 16 }}>New here? <Link to="/signup">Create an account</Link></p>
      </form>
    </AuthFrame>
  );
}

export function ForgotPage() {
  const { signIn } = useAuth();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ email: "", code: "", password: "" });
  const { busy, error, run } = useSubmit();
  const send = (e) => { e.preventDefault(); run(async () => { await api("/auth/password/forgot/", { method: "POST", auth: false, body: { email: form.email } }); setStep(2); }); };
  const reset = (e) => { e.preventDefault(); run(async () => signIn(await api("/auth/password/reset/", { method: "POST", auth: false, body: form }))); };
  return (
    <AuthFrame title={step === 1 ? "Reset your password" : "Set a new password"} back="/login"
      sub={step === 1 ? "We will email you a code." : `Enter the code sent to ${form.email} and pick a new password.`}>
      {step === 1 ? (
        <form onSubmit={send} className="stack">
          <label className="field"><span>Email</span><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label>
          {error && <p className="error">{error}</p>}
          <button className="btn block" disabled={busy}>Send reset code</button>
        </form>
      ) : (
        <form onSubmit={reset} className="stack">
          <input className="input otp" inputMode="numeric" maxLength={6} value={form.code} aria-label="Code" onChange={(e) => setForm({ ...form, code: e.target.value.replace(/\D/g, "") })} />
          <label className="field"><span>New password</span><input className="input" type="password" value={form.password} minLength={8} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" required /></label>
          {error && <p className="error">{error}</p>}
          <button className="btn block" disabled={busy || form.code.length !== 6}>Save password and sign in</button>
        </form>
      )}
    </AuthFrame>
  );
}
