import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Groups() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", kind: "device", description: "" });
  const load = () => api.get("/admin/groups").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    try { await api.post("/admin/groups", { ...form, member_ids: [] }); toast.success("Group created"); setForm({name:"",kind:"device",description:""}); load(); }
    catch { toast.error("Failed"); }
  };
  const del = async (id) => { await api.delete(`/admin/groups/${id}`); load(); };
  return (
    <div data-testid="admin-groups" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
        <input data-testid="grp-name" placeholder="Group name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="grp-kind" value={form.kind} onChange={e=>setForm({...form, kind:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["device","vehicle","route","city","campaign"].map(k=><option key={k}>{k}</option>)}
        </select>
        <input data-testid="grp-desc" placeholder="Description" value={form.description} onChange={e=>setForm({...form, description:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="grp-add" onClick={create} disabled={!form.name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Create</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(g => (
          <div key={g.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div>
              <div className="font-medium">{g.name} <span className="text-xs text-zinc-500 uppercase ml-2">{g.kind}</span></div>
              <div className="text-xs text-zinc-500 mt-1">{g.description || ""} · {g.member_ids?.length || 0} members</div>
            </div>
            <button data-testid={`grp-del-${g.id}`} onClick={()=>del(g.id)} className="text-xs text-red-400">Delete</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Create device/vehicle/route/city groups.</div>}
      </div>
    </div>
  );
}
