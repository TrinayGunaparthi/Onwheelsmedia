import { useEffect, useState } from "react";
import api from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [plays, setPlays] = useState([]);
  useEffect(() => {
    api.get("/admin/stats").then(r => setStats(r.data));
    api.get("/admin/reports/plays?days=7").then(r => setPlays(r.data));
  }, []);
  const cards = [
    { label: "Drivers", value: stats.drivers_total, hint: `${stats.drivers_pending || 0} pending` },
    { label: "Vehicles", value: stats.vehicles_total },
    { label: "Devices", value: stats.devices_total, hint: `${stats.devices_online || 0} online` },
    { label: "Advertisers", value: stats.advertisers_total },
    { label: "Ads", value: stats.ads_total, hint: `${stats.ads_pending || 0} for review` },
    { label: "Campaigns Active", value: stats.campaigns_active },
    { label: "Plays Today", value: stats.plays_today },
  ];
  return (
    <div className="space-y-8" data-testid="admin-dashboard">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-zinc-800">
        {cards.map((c, i) => (
          <div key={i} className="bg-zinc-950 p-5 hover:bg-zinc-900">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.label}</div>
            <div className="font-display text-3xl font-bold mt-2">{c.value ?? "—"}</div>
            {c.hint && <div className="text-xs text-yellow-400 mt-1">{c.hint}</div>}
          </div>
        ))}
      </div>
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Plays — last 7 days</div>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={plays}>
              <XAxis dataKey="date" stroke="#71717a" tick={{ fontSize: 11 }} />
              <YAxis stroke="#71717a" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a" }} />
              <Line type="monotone" dataKey="plays" stroke="#facc15" strokeWidth={2} dot={{ fill: "#facc15" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
