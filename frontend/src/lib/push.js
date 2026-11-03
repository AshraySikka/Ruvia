import { api } from "./api";

function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export function pushSupport() {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  return {
    supported: "serviceWorker" in navigator && "PushManager" in window && "Notification" in window,
    needsInstall: ios && !standalone,
    permission: "Notification" in window ? Notification.permission : "unsupported",
  };
}

export async function enablePush() {
  const { public_key, enabled } = await api("/push/key/", { auth: false });
  if (!enabled) throw new Error("Push is not set up on the server yet. Reminders still show in your inbox.");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notifications are blocked. You can allow them in your browser settings.");
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(public_key) });
  await api("/push/subscribe/", { method: "POST", body: { subscription: sub.toJSON() } });
  return true;
}

export async function disablePush() {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (sub) {
    await api("/push/subscribe/", { method: "DELETE", body: { endpoint: sub.endpoint } }).catch(() => {});
    await sub.unsubscribe();
  }
}
