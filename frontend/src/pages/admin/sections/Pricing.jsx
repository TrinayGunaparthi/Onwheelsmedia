import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Pricing() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", kind: "base", unit: "per_day_per_device", amount: 100, currency: "usd", active: true });
  const load = () => api.get("/admin/pricing").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    try { await api.post("/admin/pricing", { ...form, conditions: {} }); toast.success("Rule created"); load(); }
    catch { toast.error("Failed"); }
  };
  const del = async (id) => { await api.delete(`/admin/pricing/${id}`); load(); };
  return (
    <div data-testid="admin-pricing" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        <input data-testid="pr-name" placeholder="Rule name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="pr-kind" value={form.kind} onChange={e=>setForm({...form, kind:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["base","city","time","advertiser","agency"].map(k=><option key={k}>{k}</option>)}
        </select>
        <select data-testid="pr-unit" value={form.unit} onChange={e=>setForm({...form, unit:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["per_day_per_device","per_play","per_impression","flat"].map(u=><option key={u}>{u}</option>)}
        </select>
        <input data-testid="pr-amount" type="number" placeholder="Amount" value={form.amount} onChange={e=>setForm({...form, amount:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="pr-curr" value={form.currency} onChange={e=>setForm({...form, currency:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["usd","inr","eur"].map(u=><option key={u}>{u.toUpperCase()}</option>)}
        </select>
        <button data-testid="pr-add" onClick={create} disabled={!form.name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Create rule</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(r => (
          <div key={r.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div>
              <div className="font-medium">{r.name} <span className="text-xs uppercase text-zinc-500 ml-2">{r.kind}</span></div>
              <div className="text-xs text-zinc-500 mt-1">{r.unit} · <span className="text-yellow-400 font-medium">{r.currency?.toUpperCase()} {r.amount}</span></div>
            </div>
            <button data-testid={`pr-del-${r.id}`} onClick={()=>del(r.id)} className="text-xs text-red-400">Delete</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Define base and premium pricing rules.</div>}
      </div>
    </div>
  );
}
