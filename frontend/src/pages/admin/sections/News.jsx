import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function NewsPage() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ headline: "", description: "", location: "", duration_seconds: 10, active: true });
  const load = () => api.get("/admin/news").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { await api.post("/admin/news", form); toast.success("Published"); setForm({ headline: "", description: "", location: "", duration_seconds: 10, active: true }); load(); }
    catch { toast.error("Failed"); }
  };
  const remove = async (id) => { await api.delete(`/admin/news/${id}`); load(); };
  return (
    <div data-testid="admin-news" className="space-y-6">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-2 gap-3">
        <input data-testid="news-headline" placeholder="Headline" value={form.headline} onChange={e=>setForm({...form, headline:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="news-location" placeholder="Location (optional)" value={form.location} onChange={e=>setForm({...form, location:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <textarea data-testid="news-desc" placeholder="Description" value={form.description} onChange={e=>setForm({...form, description:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded md:col-span-2 h-20" />
        <button data-testid="news-publish" onClick={create} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 text-sm rounded font-medium md:col-span-2">Publish</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(n => (
          <div key={n.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between items-start hover:bg-zinc-900">
            <div>
              <div className="font-medium">{n.headline}</div>
              <div className="text-xs text-zinc-500">{n.description}</div>
              <div className="text-xs text-zinc-600 mt-1">{n.location} · {n.duration_seconds}s</div>
            </div>
            <button data-testid={`news-delete-${n.id}`} onClick={()=>remove(n.id)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No news yet</div>}
      </div>
    </div>
  );
}
