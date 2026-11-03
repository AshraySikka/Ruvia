import { Logo, TopBar } from "../components/ui";

export default function About() {
  return (
    <div className="page">
      <TopBar title="About Ruvia" back="/" />
      <div className="stack-lg" style={{ maxWidth: 440 }}>
        <Logo size={56} />
        <div className="hero-word" style={{ color: "var(--euc)" }}>Ruvia</div>
        <p className="display" style={{ fontSize: 22, fontWeight: 520, lineHeight: 1.3 }}>Made for one person first, my wife Grusha.</p>
        <p>The name comes from her too. Ruvia grew out of her name, softened into something that sounds like a small, warm place to check in.</p>
        <p>I wanted something that would ask how she is doing, remember what helped last time her head hurt or her stomach acted up, and let me know when she was having a rough day without making her explain it. So I built it for us, and then made it work for anyone who wants the same thing for their family.</p>
        <p className="muted">Ruvia is a diary and a gentle helper. It is not a doctor and it never replaces one. If something feels serious, call 911, or dial 811 to reach Health811 in Ontario.</p>
        <p className="faint">Built by Ashray Sikka.</p>
      </div>
    </div>
  );
}
