import { Radio, Zap, MapPin, ShieldCheck, Cpu, LineChart } from "lucide-react";

export const HERO_STATS = [
  { k: "10M+", v: "Monthly impressions" },
  { k: "500+", v: "Autos in network" },
  { k: "24/7", v: "Live monitoring" },
  { k: "<3s", v: "Sync latency" },
];

export const FEATURES = [
  { key: "instant", i: Zap, t: "Instant campaign launch", d: "Approved ads reach devices within seconds via our cloud sync." },
  { key: "geo", i: MapPin, t: "Geo-targeted delivery", d: "Target autos by operating area, route, and time-of-day." },
  { key: "proof", i: LineChart, t: "Live playback proof", d: "Every play, every scan — recorded, aggregated, exported." },
  { key: "offline", i: Cpu, t: "Offline-first player", d: "Cached content keeps playing even without cellular signal." },
  { key: "safety", i: ShieldCheck, t: "Admin approvals", d: "Every ad reviewed. Every driver verified. Brand-safe by default." },
  { key: "qr", i: Radio, t: "QR + News + Weather", d: "Rich content layers between ads keep passengers engaged." },
];

export function StatCard({ stat }) {
  return (
    <div className="border border-zinc-800 p-6 hover:border-yellow-400/40 transition-colors">
      <div className="font-display text-3xl md:text-4xl font-bold text-yellow-400">{stat.k}</div>
      <div className="text-xs text-zinc-500 uppercase tracking-widest mt-2">{stat.v}</div>
    </div>
  );
}

export function FeatureCard({ f }) {
  const Icon = f.i;
  return (
    <div className="bg-zinc-950 p-8 hover:bg-zinc-900 transition-colors">
      <Icon className="w-6 h-6 text-yellow-400 mb-4" />
      <h3 className="font-display text-xl font-semibold mb-2">{f.t}</h3>
      <p className="text-sm text-zinc-400">{f.d}</p>
    </div>
  );
}
