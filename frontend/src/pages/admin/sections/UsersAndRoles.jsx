import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const PERMS = ["ops","content","sales","finance","analytics","all"];

export default function UsersAndRoles() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "admin", permissions: ["all"] });
  const load = () => api.get("/admin/users").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { await api.post("/admin/users", form); toast.success("User created"); setForm({email:"",password:"",name:"",role:"admin",permissions:["all"]}); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const savePerms = async (uid, perms, role) => {
    try { await api.patch(`/admin/users/${uid}/permissions`, { permissions: perms, role }); toast.success("Saved"); load(); }
    catch { toast.error("Failed"); }
  };
  const toggle = (list, v) => list.includes(v) ? list.filter(x=>x!==v) : [...list, v];
  return (
    <div data-testid="admin-users" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-3 gap-3">
        <input data-testid="u-name" placeholder="Full name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="u-email" placeholder="Email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="u-password" type="password" placeholder="Password" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="u-role" value={form.role} onChange={e=>setForm({...form, role:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["admin","agency"].map(r=><option key={r}>{r}</option>)}
        </select>
        <div className="md:col-span-2 flex flex-wrap gap-2 items-center">
          {PERMS.map(p => (
            <button key={p} data-testid={`u-perm-${p}`} type="button" onClick={()=>setForm({...form, permissions: toggle(form.permissions, p)})} className={`text-xs px-3 py-1.5 rounded border ${form.permissions.includes(p)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-300"}`}>{p}</button>
          ))}
        </div>
        <button data-testid="u-create" onClick={create} disabled={!form.email || !form.password || !form.name} className="md:col-span-3 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Create user</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(u => (
          <div key={u.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
            <div className="flex justify-between mb-2">
              <div><div className="font-medium">{u.name} <span className="text-xs uppercase text-zinc-500 ml-2">{u.role}</span></div><div className="text-xs text-zinc-500">{u.email}</div></div>
            </div>
            <div className="flex flex-wrap gap-2">
              {PERMS.map(p => (
                <button key={p} data-testid={`u-toggle-${u.id}-${p}`} onClick={()=>savePerms(u.id, toggle(u.permissions||[], p), u.role)} className={`text-xs px-2 py-1 rounded border ${(u.permissions||[]).includes(p)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-400"}`}>{p}</button>
              ))}
            </div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No admin/agency users yet.</div>}
      </div>
    </div>
  );
}
