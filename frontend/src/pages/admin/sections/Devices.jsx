import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const STATUSES = ["Pending", "Approved", "Suspended", "Maintenance", "Deactivated"];

export default function DevicesPage() {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/admin/devices").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const setStatus = async (id, status) => {
    try { await api.patch(`/admin/devices/${id}`, { status }); toast.success(status); load(); }
    catch { toast.error("Update failed"); }
  };
  const isOnline = (d) => d.last_online && (Date.now() - new Date(d.last_online).getTime()) < 5*60*1000;
  return (
    <div data-testid="admin-devices" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Device ID</th><th className="text-left p-3">Vehicle</th><th className="text-left p-3">Activation</th><th className="text-left p-3">Last Online</th><th className="text-left p-3">Live</th><th className="text-left p-3">Status</th><th className="text-left p-3">Actions</th></tr>
        </thead>
        <tbody>
          {rows.map(d => (
            <tr key={d.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-mono">{d.device_code}</td>
              <td className="p-3 font-mono text-xs">{d.vehicle?.reg_no || "—"}</td>
              <td className="p-3 font-mono text-xs text-yellow-400">{d.activation_code}</td>
              <td className="p-3 text-xs text-zinc-400">{d.last_online || "never"}</td>
              <td className="p-3">
                {isOnline(d) ? <span className="flex items-center gap-2 text-green-400 text-xs"><span className="w-2 h-2 rounded-full bg-green-400 pulse-dot" />ONLINE</span> : <span className="text-zinc-500 text-xs">offline</span>}
              </td>
              <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${d.status==="Approved"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{d.status}</span></td>
              <td className="p-3">
                <select data-testid={`device-status-${d.id}`} value={d.status} onChange={e=>setStatus(d.id, e.target.value)} className="bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs rounded">
                  {STATUSES.map(s => <option key={s}>{s}</option>)}
                </select>
              </td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={7} className="p-12 text-center text-zinc-500">No devices registered</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
