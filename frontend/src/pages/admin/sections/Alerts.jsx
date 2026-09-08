import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Alerts() {
  const [rows, setRows] = useState([]);
  const [showResolved, setShowResolved] = useState(false);
  const load = () => api.get(`/admin/alerts?resolved=${showResolved}`).then(r => setRows(r.data));
  useEffect(() => { load(); }, [showResolved]);
  const scan = async () => { try { const {data} = await api.post("/admin/alerts/scan-offline"); toast.success(`${data.alerts_created} alerts created`); load(); } catch { toast.error("Scan failed"); } };
  const resolve = async (id) => { await api.post(`/admin/alerts/${id}/resolve`); load(); };
  return (
    <div data-testid="admin-alerts" className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button data-testid="show-open" onClick={()=>setShowResolved(false)} className={`text-xs px-3 py-1.5 rounded ${!showResolved?"bg-yellow-400 text-zinc-950":"border border-zinc-800"}`}>Open</button>
          <button data-testid="show-resolved" onClick={()=>setShowResolved(true)} className={`text-xs px-3 py-1.5 rounded ${showResolved?"bg-yellow-400 text-zinc-950":"border border-zinc-800"}`}>Resolved</button>
        </div>
        <button data-testid="scan-offline" onClick={scan} className="text-xs bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-1.5 rounded">Scan offline devices</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(a => (
          <div key={a.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded ${a.severity==="high"?"bg-red-500/20 text-red-400":a.severity==="medium"?"bg-yellow-500/20 text-yellow-400":"bg-zinc-800 text-zinc-400"}`}>{a.severity}</span>
                <span className="text-xs text-zinc-500 font-mono">{a.kind}</span>
              </div>
              <div className="text-sm">{a.message}</div>
              <div className="text-xs text-zinc-600 mt-1">{a.at?.slice(0,19).replace("T"," ")}</div>
            </div>
            {!a.resolved && <button data-testid={`resolve-${a.id}`} onClick={()=>resolve(a.id)} className="text-xs text-green-400 h-fit">Resolve</button>}
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No {showResolved?"resolved":"open"} alerts.</div>}
      </div>
    </div>
  );
}
