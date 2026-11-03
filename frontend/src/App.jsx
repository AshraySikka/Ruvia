import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Nav from "./components/Nav";
import { Logo, ToastProvider, useToast } from "./components/ui";
import { flushOutbox } from "./lib/api";
import { useAuth } from "./lib/auth";
import { ForgotPage, LoginPage, SignUpPage, VerifyPage, WelcomePage } from "./pages/Auth";
import Today from "./pages/Today";

const Chat = lazy(() => import("./pages/Chat"));
const CalendarPage = lazy(() => import("./pages/Calendar"));
const Insights = lazy(() => import("./pages/Insights"));
const Cycle = lazy(() => import("./pages/Cycle"));
const Care = lazy(() => import("./pages/Care"));
const Person = lazy(() => import("./pages/Person"));
const Me = lazy(() => import("./pages/Me"));
const FollowUp = lazy(() => import("./pages/FollowUp"));
const Inbox = lazy(() => import("./pages/Inbox"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Emergency = lazy(() => import("./pages/Emergency"));
const About = lazy(() => import("./pages/About"));

function Splash() {
  return <div style={{ minHeight: "100dvh", display: "grid", placeItems: "center" }}><Logo size={52} /></div>;
}

function Shell() {
  const { user } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();
  const toast = useToast();
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const up = async () => { setOnline(true); const n = await flushOutbox(); if (n) toast(`Synced ${n} saved ${n === 1 ? "entry" : "entries"}`); };
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    flushOutbox();
    const onMsg = (e) => e.data?.type === "navigate" && nav(e.data.url);
    navigator.serviceWorker?.addEventListener("message", onMsg);
    return () => { window.removeEventListener("online", up); window.removeEventListener("offline", down); navigator.serviceWorker?.removeEventListener("message", onMsg); };
  }, [nav, toast]);

  if (user && !user.onboarded && loc.pathname !== "/welcome-setup") return <Navigate to="/welcome-setup" replace />;
  const hideNav = ["/welcome-setup", "/emergency"].includes(loc.pathname) || loc.pathname.startsWith("/followup");

  return (
    <div className="app">
      {!online && <div className="offline-bar">You are offline. Check-ins and water are saved and will sync.</div>}
      <AnimatePresence mode="wait">
        <motion.main key={loc.pathname.split("/")[1]} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }}>
          <Suspense fallback={<div className="page" />}>
            <Routes location={loc}>
              <Route path="/" element={<Today />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/cycle" element={<Cycle />} />
              <Route path="/care" element={<Care />} />
              <Route path="/care/person/:id" element={<Person />} />
              <Route path="/me/*" element={<Me />} />
              <Route path="/followup/:id" element={<FollowUp />} />
              <Route path="/inbox" element={<Inbox />} />
              <Route path="/emergency" element={<Emergency />} />
              <Route path="/about" element={<About />} />
              <Route path="/welcome-setup" element={<Onboarding />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </motion.main>
      </AnimatePresence>
      {!hideNav && <Nav />}
    </div>
  );
}

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <Splash />;
  return (
    <ToastProvider>
      {user ? <Shell /> : (
        <div className="app">
          <Routes>
            <Route path="/" element={<WelcomePage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/verify" element={<VerifyPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/forgot" element={<ForgotPage />} />
            <Route path="/about" element={<Suspense fallback={null}><About /></Suspense>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      )}
    </ToastProvider>
  );
}
