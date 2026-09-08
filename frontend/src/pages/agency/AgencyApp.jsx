import { useEffect, useState } from "react";
import Shell from "@/pages/Shell";
import { LayoutDashboard, Building2, Link as LinkIcon } from "lucide-react";
import { Routes, Route, Navigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";

const nav = [
  { key: "dash", to: "/agency", label: "Dashboard", icon: LayoutDashboard },
  { key: "advertisers", to: "/agency/advertisers", label: "Advertisers", icon: Building2 },
];

function Dashboard() {
  const [s, setS] = useState({});
  useEffect(() => { api.get("/agency/summary").then(r => setS(r.data)); }, []);
  return (
    <div data-testid="agency-dash" className="grid grid-cols-3 gap-px bg-zinc-800">
      {[{l:"Advertisers",v:s.advertisers},{l:"Campaigns",v:s.campaigns},{l:"Total Spend",v:`$${s.total_spend||0}`,tint:"text-green-400"}].map((c,i)=>(
        <div key={i} className="bg-zinc-950 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
          <div className={`font-display text-4xl font-bold mt-2 ${c.tint||"text-yellow-400"}`}>{c.v ?? 0}</div>
        </div>
      ))}
    </div>
  );
}

function Advertisers() {
  const [rows, setRows] = useState([]);
  const [advId, setAdvId] = useState("");
  const load = () => api.get("/agency/advertisers").then(r => setRows(r.data));
  useEffect(load, []);
  const link = async () => {
    try { await api.post("/agency/link", { advertiser_id: advId }); toast.success("Linked"); setAdvId(""); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  return (
    <div data-testid="agency-advertisers" className="space-y-4">
      <div className="border border-zinc-800 p-4 flex gap-2">
        <input data-testid="link-id" placeholder="Advertiser user_id" value={advId} onChange={e=>setAdvId(e.target.value)} className="flex-1 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded font-mono" />
        <button data-testid="link-btn" onClick={link} className="bg-yellow-400 text-zinc-950 px-4 py-2 rounded font-medium text-sm flex items-center gap-1"><LinkIcon className="w-4 h-4"/> Link</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(a => (
          <div key={a.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium">{a.name || a.company}</div><div className="text-xs text-zinc-500">{a.email}</div></div>
            <div className="text-right"><div className="text-yellow-400">{a.campaigns} campaigns</div><div className="text-xs text-green-400">${a.spend}</div></div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Link advertisers by pasting their user id from the admin panel.</div>}
      </div>
    </div>
  );
}

export default function AgencyApp() {
  return (
    <Shell nav={nav} title="Agency">
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="advertisers" element={<Advertisers />} />
        <Route path="*" element={<Navigate to="/agency" replace />} />
      </Routes>
    </Shell>
  );
}
