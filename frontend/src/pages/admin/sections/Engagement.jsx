import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function Engagement() {
  const [data, setData] = useState({});
  useEffect(() => { api.get("/admin/analytics/engagement?hours=168").then(r => setData(r.data)); }, []);
  const cards = [
    { l: "QR Scans", v: data.qr_scans, tint: "text-yellow-400" },
    { l: "Game Starts", v: data.game_starts, tint: "text-cyan-400" },
    { l: "Game Completions", v: data.game_completions, tint: "text-green-400" },
    { l: "Completion Rate", v: `${data.completion_rate ?? 0}%` },
    { l: "Mirror Sessions", v: data.mirror_sessions },
    { l: "Mirror Authorized", v: data.mirror_authorized },
  ];
  return (
    <div data-testid="admin-engagement" className="space-y-6">
      <div className="text-xs text-zinc-500 uppercase tracking-widest">Last 7 days · Interactive engagement</div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-zinc-800">
        {cards.map((c, i) => (
          <div key={i} className="bg-zinc-950 p-6">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className={`font-display text-4xl font-bold mt-2 ${c.tint || "text-white"}`}>{c.v ?? 0}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
