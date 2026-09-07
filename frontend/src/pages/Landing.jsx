import { Link } from "react-router-dom";
import { ArrowRight, Radio, Zap, MapPin, ShieldCheck, Cpu, LineChart } from "lucide-react";

export default function Landing() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Nav */}
      <nav className="sticky top-0 z-40 backdrop-blur-xl bg-zinc-950/70 border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-yellow-400 grid place-items-center"><Radio className="w-4 h-4 text-zinc-950" /></div>
            <span className="font-display text-lg font-bold">ON WHEELS <span className="text-yellow-400">MEDIA</span></span>
          </div>
          <div className="flex items-center gap-3">
            <Link data-testid="nav-login" to="/login" className="text-sm text-zinc-300 hover:text-white px-3 py-2">Sign in</Link>
            <Link data-testid="nav-register" to="/register" className="text-sm bg-yellow-400 hover:bg-yellow-300 text-zinc-950 font-medium px-4 py-2 rounded-full">Get started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-zinc-950/60 to-zinc-950 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 pt-24 pb-32 relative">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-400/10 border border-yellow-400/30 text-yellow-300 text-xs uppercase tracking-widest mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 pulse-dot" />
              India's first auto-rickshaw ad network
            </div>
            <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tighter leading-none">
              Ads on wheels.<br />
              <span className="text-yellow-400">Everywhere</span> your city goes.
            </h1>
            <p className="mt-6 text-lg text-zinc-400 max-w-xl">
              Digital screens inside passenger autos. Cloud-controlled campaigns.
              Real-time playback reporting. Reach commuters at eye-level, kilometre after kilometre.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link data-testid="hero-cta-advertiser" to="/register?role=advertiser" className="group inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-zinc-950 font-semibold px-6 py-3 rounded-full glow-yellow">
                Advertise with us <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link data-testid="hero-cta-driver" to="/register?role=driver" className="inline-flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-white px-6 py-3 rounded-full">
                Enroll your auto
              </Link>
            </div>
          </div>

          {/* Stats bento */}
          <div className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { k: "10M+", v: "Monthly impressions" },
              { k: "500+", v: "Autos in network" },
              { k: "24/7", v: "Live monitoring" },
              { k: "<3s", v: "Sync latency" },
            ].map((s, i) => (
              <div key={i} className="border border-zinc-800 p-6 hover:border-yellow-400/40 transition-colors">
                <div className="font-display text-3xl md:text-4xl font-bold text-yellow-400">{s.k}</div>
                <div className="text-xs text-zinc-500 uppercase tracking-widest mt-2">{s.v}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-800">
        <div className="grid md:grid-cols-3 gap-px bg-zinc-800">
          {[
            { i: Zap, t: "Instant campaign launch", d: "Approved ads reach devices within seconds via our cloud sync." },
            { i: MapPin, t: "Geo-targeted delivery", d: "Target autos by operating area, route, and time-of-day." },
            { i: LineChart, t: "Live playback proof", d: "Every play, every scan — recorded, aggregated, exported." },
            { i: Cpu, t: "Offline-first player", d: "Cached content keeps playing even without cellular signal." },
            { i: ShieldCheck, t: "Admin approvals", d: "Every ad reviewed. Every driver verified. Brand-safe by default." },
            { i: Radio, t: "QR + News + Weather", d: "Rich content layers between ads keep passengers engaged." },
          ].map((f, i) => (
            <div key={i} className="bg-zinc-950 p-8 hover:bg-zinc-900 transition-colors">
              <f.i className="w-6 h-6 text-yellow-400 mb-4" />
              <h3 className="font-display text-xl font-semibold mb-2">{f.t}</h3>
              <p className="text-sm text-zinc-400">{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-800">
        <div className="grid md:grid-cols-2 gap-6">
          <div className="border border-zinc-800 p-10 relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-yellow-400/10 blur-3xl" />
            <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3">For advertisers</div>
            <h3 className="font-display text-3xl font-bold mb-4">Reach captive audiences at eye-level.</h3>
            <p className="text-zinc-400 mb-8">Upload creative, launch campaigns, track every play.</p>
            <Link data-testid="cta-advertiser" to="/register?role=advertiser" className="inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-zinc-950 font-semibold px-6 py-3 rounded-full">Start advertising <ArrowRight className="w-4 h-4" /></Link>
          </div>
          <div className="border border-zinc-800 p-10 relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-cyan-400/10 blur-3xl" />
            <div className="text-xs uppercase tracking-widest text-cyan-400 mb-3">For drivers</div>
            <h3 className="font-display text-3xl font-bold mb-4">Earn passive income from your auto.</h3>
            <p className="text-zinc-400 mb-8">Install our device, drive as usual, get paid.</p>
            <Link data-testid="cta-driver" to="/register?role=driver" className="inline-flex items-center gap-2 border border-zinc-700 hover:border-cyan-400 text-white px-6 py-3 rounded-full">Enroll now <ArrowRight className="w-4 h-4" /></Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-zinc-800 py-8">
        <div className="max-w-7xl mx-auto px-6 text-xs text-zinc-500 flex items-center justify-between">
          <div>© 2026 On Wheels Media. All rights reserved.</div>
          <Link data-testid="footer-player" to="/player" className="hover:text-yellow-400">Device Player →</Link>
        </div>
      </footer>
    </div>
  );
}
