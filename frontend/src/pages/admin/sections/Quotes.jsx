import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { formatINR } from "@/lib/inr";

const STATUSES = ["pending", "quoted", "approved", "rejected"];

export default function Quotes() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ status: "quoted", admin_price_inr: 0, admin_notes: "" });
  const load = () => api.get(`/admin/quotes${filter?`?status=${filter}`:""}`).then(r=>setRows(r.data));
  useEffect(() => { load(); }, [filter]);
  const open = (q) => { setEditing(q); setForm({ status: q.status==="pending"?"quoted":q.status, admin_price_inr: q.admin_price_inr || 0, admin_notes: q.admin_notes || "" }); };
  const save = async () => {
    try { await api.patch(`/admin/quotes/${editing.id}`, form); toast.success("Quote sent"); setEditing(null); load(); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-quotes" className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="text-xs uppercase tracking-widest text-zinc-500">Filter:</div>
        {[""].concat(STATUSES).map(s => (
          <button key={s||"all"} data-testid={`quote-filter-${s||"all"}`} onClick={()=>setFilter(s)} className={`text-xs px-3 py-1.5 rounded ${filter===s?"bg-yellow-400 text-zinc-950":"border border-zinc-800 text-zinc-300"}`}>{s||"All"}</button>
        ))}
      </div>
      <div className="border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
            <tr><th className="text-left p-3">Advertiser</th><th className="text-left p-3">Autos</th><th className="text-left p-3">Duration</th><th className="text-left p-3">City</th><th className="text-right p-3">Quoted</th><th className="text-left p-3">Status</th></tr>
          </thead>
          <tbody>
            {rows.map(q => (
              <tr key={q.id} className="border-t border-zinc-800 hover:bg-zinc-900 cursor-pointer" onClick={()=>open(q)}>
                <td className="p-3">{q.advertiser_email}<div className="text-xs text-zinc-500">{q.contact_name || ""} {q.contact_phone || ""}</div></td>
                <td className="p-3">{q.autos}</td>
                <td className="p-3">{q.duration_days} days</td>
                <td className="p-3">{q.target_city || "—"}</td>
                <td className="p-3 text-right text-yellow-400 font-mono">{q.admin_price_inr ? formatINR(q.admin_price_inr) : "—"}</td>
                <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${q.status==="approved"?"bg-green-500/20 text-green-400":q.status==="rejected"?"bg-red-500/20 text-red-400":q.status==="quoted"?"bg-cyan-500/20 text-cyan-400":"bg-yellow-500/20 text-yellow-400"}`}>{q.status}</span></td>
              </tr>
            ))}
            {rows.length===0 && <tr><td colSpan={6} className="p-12 text-center text-zinc-500">No quote requests yet.</td></tr>}
          </tbody>
        </table>
      </div>
      {editing && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm grid place-items-center z-50 p-6" onClick={()=>setEditing(null)}>
          <div className="w-full max-w-lg bg-zinc-950 border border-zinc-800 rounded p-6 space-y-4" onClick={e=>e.stopPropagation()} data-testid="quote-modal">
            <div className="text-xs uppercase tracking-widest text-yellow-400">Custom quote from {editing.advertiser_email}</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><div className="text-zinc-500 text-xs">Autos</div><div>{editing.autos}</div></div>
              <div><div className="text-zinc-500 text-xs">Duration</div><div>{editing.duration_days} days</div></div>
              <div><div className="text-zinc-500 text-xs">City</div><div>{editing.target_city || "—"}</div></div>
              <div><div className="text-zinc-500 text-xs">Impressions</div><div>{(editing.estimated_views || 0).toLocaleString("en-IN")}</div></div>
              <div className="col-span-2"><div className="text-zinc-500 text-xs">Special requirements</div><div className="text-zinc-300">{editing.special_requirements || "—"}</div></div>
            </div>
            <div className="pt-4 border-t border-zinc-800 space-y-3">
              <select data-testid="quote-status" value={form.status} onChange={e=>setForm({...form, status:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full">
                {STATUSES.filter(s=>s!=="pending").map(s=><option key={s}>{s}</option>)}
              </select>
              <input data-testid="quote-price" type="number" min={0} placeholder="Quoted price ₹ INR" value={form.admin_price_inr} onChange={e=>setForm({...form, admin_price_inr:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" />
              <textarea data-testid="quote-notes" placeholder="Notes to advertiser" value={form.admin_notes} onChange={e=>setForm({...form, admin_notes:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full h-20" />
              <button data-testid="quote-send" onClick={save} className="w-full bg-yellow-400 text-zinc-950 px-4 py-3 rounded font-medium">Send quote to advertiser</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
