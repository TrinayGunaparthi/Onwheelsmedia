import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const STATUSES = ["Pending", "Under Review", "Approved", "Rejected", "Suspended"];

export default function DriversPage() {
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState("");
  const load = () => api.get("/admin/drivers").then(r => setRows(r.data));
  useEffect(load, []);
  const setStatus = async (id, status) => {
    try { await api.patch(`/admin/drivers/${id}`, { status }); toast.success(`Marked ${status}`); load(); }
    catch (e) { toast.error("Update failed"); }
  };
  const filtered = rows.filter(r => (r.full_name+" "+r.email+" "+r.city).toLowerCase().includes(search.toLowerCase()));
  return (
    <div data-testid="admin-drivers">
      <div className="flex items-center justify-between mb-4">
        <input data-testid="drivers-search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search drivers…" className="bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-3 py-2 text-sm rounded w-64" />
        <div className="text-xs text-zinc-500">{filtered.length} drivers</div>
      </div>
      <div className="border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
            <tr>
              <th className="text-left p-3">Name</th><th className="text-left p-3">Contact</th><th className="text-left p-3">City</th><th className="text-left p-3">Vehicle</th><th className="text-left p-3">Status</th><th className="text-left p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(d => (
              <tr key={d.id} className="border-t border-zinc-800 hover:bg-zinc-900">
                <td className="p-3 font-medium">{d.full_name}</td>
                <td className="p-3 text-zinc-400">{d.email}<br /><span className="font-mono text-xs">{d.phone}</span></td>
                <td className="p-3">{d.city}, {d.state}</td>
                <td className="p-3 font-mono text-xs">{d.vehicle_reg_no}<br /><span className="text-zinc-500">{d.manufacturer} {d.model}</span></td>
                <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${d.status==="Approved"?"bg-green-500/20 text-green-400":d.status==="Rejected"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400"}`}>{d.status}</span></td>
                <td className="p-3">
                  <select data-testid={`driver-status-${d.id}`} value={d.status} onChange={e=>setStatus(d.id, e.target.value)} className="bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs rounded">
                    {STATUSES.map(s => <option key={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {filtered.length===0 && <tr><td colSpan={6} className="p-12 text-center text-zinc-500">No drivers yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
