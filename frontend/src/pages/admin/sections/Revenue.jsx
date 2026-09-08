import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function Revenue() {
  const [s, setS] = useState({});
  const [byAdv, setByAdv] = useState([]);
  useEffect(() => {
    api.get("/admin/revenue/summary").then(r => setS(r.data));
    api.get("/admin/revenue/by-advertiser").then(r => setByAdv(r.data));
  }, []);
  const cards = [
    { l: "Total Revenue", v: `$${s.total_revenue ?? 0}`, tint: "text-green-400" },
    { l: "Today", v: `$${s.today_revenue ?? 0}` },
    { l: "This Month", v: `$${s.month_revenue ?? 0}` },
    { l: "Pending", v: `$${s.pending_payments ?? 0}`, tint: "text-yellow-400" },
    { l: "Advertisers", v: s.advertisers_count },
    { l: "Active Campaigns", v: s.campaigns_active },
  ];
  return (
    <div data-testid="admin-revenue" className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-zinc-800">
        {cards.map((c,i)=>(
          <div key={i} className="bg-zinc-950 p-6">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className={`font-display text-3xl font-bold mt-2 ${c.tint || "text-white"}`}>{c.v ?? 0}</div>
          </div>
        ))}
      </div>
      <div className="border border-zinc-800">
        <div className="p-3 bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">Top advertisers</div>
        {byAdv.map(a => (
          <div key={a.advertiser_id} className="p-4 border-t border-zinc-800 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium">{a.name || a.email}</div><div className="text-xs text-zinc-500">{a.email}</div></div>
            <div className="text-right"><div className="text-green-400 font-medium">${a.spend}</div><div className="text-xs text-zinc-500">{a.count} payments</div></div>
          </div>
        ))}
        {byAdv.length===0 && <div className="p-12 text-center text-zinc-500">No paid transactions yet.</div>}
      </div>
    </div>
  );
}
