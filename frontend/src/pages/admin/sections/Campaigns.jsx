import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const STATUSES = ["Draft", "Scheduled", "Active", "Paused", "Completed"];

export default function CampaignsPage() {
  const [rows, setRows] = useState([]);
  const [devices, setDevices] = useState([]);
  const load = async () => {
    const [c, d] = await Promise.all([api.get("/admin/campaigns"), api.get("/admin/devices")]);
    setRows(c.data); setDevices(d.data);
  };
  useEffect(() => { load(); }, []);
  const update = async (id, body) => {
    try { await api.patch(`/admin/campaigns/${id}`, body); toast.success("Updated"); load(); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-campaigns" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Campaign</th><th className="text-left p-3">Dates</th><th className="text-left p-3">Objective</th><th className="text-left p-3">Target Devices</th><th className="text-left p-3">Status</th><th className="text-left p-3">Action</th></tr>
        </thead>
        <tbody>
          {rows.map(c => (
            <tr key={c.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-medium">{c.name}<br /><span className="text-xs text-zinc-500">Budget ₹{c.budget}</span></td>
              <td className="p-3 text-xs text-zinc-400">{c.start_date} → {c.end_date}</td>
              <td className="p-3 text-xs">{c.objective}</td>
              <td className="p-3">
                <select data-testid={`campaign-devices-${c.id}`} multiple size={2} value={c.target_devices||[]} onChange={e=>update(c.id, {target_devices: Array.from(e.target.selectedOptions).map(o=>o.value)})} className="bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs rounded w-40">
                  {devices.map(d => <option key={d.id} value={d.id}>{d.device_code}</option>)}
                </select>
              </td>
              <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${c.status==="Active"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{c.status}</span></td>
              <td className="p-3">
                <select data-testid={`campaign-status-${c.id}`} value={c.status} onChange={e=>update(c.id, {status: e.target.value})} className="bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs rounded">
                  {STATUSES.map(s => <option key={s}>{s}</option>)}
                </select>
              </td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={6} className="p-12 text-center text-zinc-500">No campaigns yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
