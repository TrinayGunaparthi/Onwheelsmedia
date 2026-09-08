import { useEffect, useState } from "react";
import api from "@/lib/api";
import { TrendingUp, Radio, Zap, AlertTriangle, DollarSign, Users } from "lucide-react";

export default function BiDashboard() {
  const [d, setD] = useState({});
  const [heat, setHeat] = useState([]);
  useEffect(() => {
    api.get("/admin/bi/summary").then(r => setD(r.data));
    api.get("/admin/bi/heatmap").then(r => setHeat(r.data)).catch(()=>setHeat([]));
  }, []);
  const Card = ({ label, value, sub, tint, icon: Icon }) => (
    <div className="bg-zinc-950 p-5 border border-zinc-800 hover:border-yellow-400/40 transition-colors">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-widest text-zinc-500">{label}</div>
        {Icon && <Icon className={`w-4 h-4 ${tint || "text-yellow-400"}`} />}
      </div>
      <div className={`font-display text-3xl font-bold mt-2 ${tint || "text-white"}`}>{value ?? 0}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
  return (
    <div data-testid="admin-bi" className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3 flex items-center gap-2"><TrendingUp className="w-3 h-3"/> Executive · Network at a glance</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card label="Cities" value={d.network?.cities} icon={Radio} />
          <Card label="Devices Online" value={d.network?.devices_online} sub={`of ${d.network?.devices_total || 0} total`} tint="text-green-400" icon={Zap} />
          <Card label="Offline" value={d.network?.devices_offline} tint="text-red-400" />
          <Card label="Alerts Open" value={d.alerts_open} tint="text-orange-400" icon={AlertTriangle} />
        </div>
      </div>
      <div>
        <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3">Advertising & Revenue</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card label="Active Campaigns" value={d.advertising?.campaigns_active} />
          <Card label="Ads Playing" value={d.advertising?.plays} tint="text-cyan-400" />
          <Card label="Est. Audience" value={d.advertising?.estimated_audience} tint="text-cyan-400" icon={Users} />
          <Card label="Ads in library" value={d.advertising?.ads_total} />
          <Card label="Revenue Today" value={`$${d.revenue?.today ?? 0}`} tint="text-green-400" icon={DollarSign} />
          <Card label="Revenue Month" value={`$${d.revenue?.month ?? 0}`} tint="text-green-400" />
          <Card label="Pending" value={`$${d.revenue?.pending ?? 0}`} tint="text-yellow-400" />
          <Card label="Vehicles" value={d.network?.vehicles} />
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Top Campaigns</div>
          {(d.top_campaigns || []).map(c => (
            <div key={c.id} className="flex justify-between py-2 border-b border-zinc-800 last:border-0 text-sm">
              <span className="font-medium">{c.name}</span>
              <span className="text-yellow-400 font-medium">{c.plays} plays</span>
            </div>
          ))}
          {(d.top_campaigns || []).length===0 && <div className="text-zinc-500 text-sm py-4">No campaign data yet.</div>}
        </div>
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Top Devices</div>
          {(d.top_devices || []).map(c => (
            <div key={c.id} className="flex justify-between py-2 border-b border-zinc-800 last:border-0 text-sm">
              <span className="font-mono text-xs">{c.device_code}</span>
              <span className="text-cyan-400 font-medium">{c.plays} plays</span>
            </div>
          ))}
          {(d.top_devices || []).length===0 && <div className="text-zinc-500 text-sm py-4">No plays yet.</div>}
        </div>
      </div>
      {heat.length > 0 && (
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">City heatmap</div>
          <div className="grid md:grid-cols-3 gap-3">
            {heat.map(h => (
              <div key={h.city} className="border border-zinc-800 p-4" style={{background: `linear-gradient(180deg, rgba(250,204,21,${Math.min(0.4, h.devices/20)}) 0%, transparent 100%)`}}>
                <div className="font-display text-xl font-bold">{h.city}</div>
                <div className="text-xs text-zinc-500">{h.state}</div>
                <div className="mt-3 flex justify-between text-sm"><span>Devices</span><span className="text-yellow-400 font-medium">{h.devices}</span></div>
                <div className="flex justify-between text-sm"><span>Plays</span><span className="text-cyan-400 font-medium">{h.plays}</span></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
