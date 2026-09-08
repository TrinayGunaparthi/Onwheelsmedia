import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Cities() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", state: "", lat: 0, lng: 0 });
  const load = () => api.get("/admin/cities").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => { try { await api.post("/admin/cities", form); toast.success("Added"); setForm({name:"",state:"",lat:0,lng:0}); load(); } catch { toast.error("Failed"); } };
  const del = async (id) => { await api.delete(`/admin/cities/${id}`); load(); };
  return (
    <div data-testid="admin-cities" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid grid-cols-2 md:grid-cols-5 gap-3">
        <input data-testid="city-name" placeholder="City" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="city-state" placeholder="State" value={form.state} onChange={e=>setForm({...form, state:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="city-lat" type="number" step="0.0001" placeholder="Latitude" value={form.lat} onChange={e=>setForm({...form, lat:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="city-lng" type="number" step="0.0001" placeholder="Longitude" value={form.lng} onChange={e=>setForm({...form, lng:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="city-add" onClick={create} disabled={!form.name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Add city</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(c => (
          <div key={c.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium">{c.name}, {c.state}</div><div className="text-xs text-zinc-500 font-mono">{c.lat}, {c.lng}</div></div>
            <button data-testid={`city-del-${c.id}`} onClick={()=>del(c.id)} className="text-xs text-red-400">Delete</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Add your first city.</div>}
      </div>
    </div>
  );
}
