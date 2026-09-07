import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const STATUSES = ["Submitted", "Under Review", "Approved", "Rejected", "Scheduled", "Active", "Expired"];

export default function AdsPage() {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/admin/ads").then(r => setRows(r.data));
  useEffect(load, []);
  const setStatus = async (id, status) => {
    try { await api.patch(`/admin/ads/${id}`, { status }); toast.success(status); load(); }
    catch { toast.error("Update failed"); }
  };
  return (
    <div data-testid="admin-ads" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Ad</th><th className="text-left p-3">Advertiser</th><th className="text-left p-3">Type</th><th className="text-left p-3">Duration</th><th className="text-left p-3">Preview</th><th className="text-left p-3">Status</th><th className="text-left p-3">Actions</th></tr>
        </thead>
        <tbody>
          {rows.map(a => (
            <tr key={a.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-medium">{a.name}<br /><span className="text-xs text-zinc-500">{a.description}</span></td>
              <td className="p-3 text-zinc-400 text-xs">{a.advertiser_email}</td>
              <td className="p-3 uppercase text-xs">{a.file_type}</td>
              <td className="p-3">{a.duration_seconds}s</td>
              <td className="p-3">
                {a.file_type==="image" ? <img src={`${process.env.REACT_APP_BACKEND_URL}${a.file_url}`} alt="" className="w-16 h-10 object-cover rounded border border-zinc-800"/> : <span className="text-xs text-zinc-500">video</span>}
              </td>
              <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${a.status==="Approved"?"bg-green-500/20 text-green-400":a.status==="Rejected"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400"}`}>{a.status}</span></td>
              <td className="p-3">
                <select data-testid={`ad-status-${a.id}`} value={a.status} onChange={e=>setStatus(a.id, e.target.value)} className="bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs rounded">
                  {STATUSES.map(s => <option key={s}>{s}</option>)}
                </select>
              </td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={7} className="p-12 text-center text-zinc-500">No ads submitted</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
