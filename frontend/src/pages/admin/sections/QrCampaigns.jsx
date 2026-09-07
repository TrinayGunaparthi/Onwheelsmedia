import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function QrPage() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", target_url: "", campaign_type: "Website" });
  const load = () => api.get("/admin/qr").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    try { await api.post("/admin/qr", { ...form, device_ids: [] }); setForm({ name: "", target_url: "", campaign_type: "Website" }); toast.success("Created"); load(); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-qr" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-3 gap-3">
        <input data-testid="qr-name" placeholder="Campaign name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="qr-url" placeholder="Target URL" value={form.target_url} onChange={e=>setForm({...form, target_url:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="qr-type" value={form.campaign_type} onChange={e=>setForm({...form, campaign_type:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["Website","Product","Offer","Coupon","WhatsApp","Survey","App download","Lead form"].map(t=><option key={t}>{t}</option>)}
        </select>
        <button data-testid="qr-create" onClick={create} className="md:col-span-3 bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Create QR Campaign</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(q => (
          <div key={q.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
            <div className="flex justify-between">
              <div><div className="font-medium">{q.name}</div><div className="text-xs text-zinc-500">{q.target_url}</div></div>
              <div className="text-right text-xs">
                <div className="text-yellow-400">{q.scans || 0} scans</div>
                <div className="text-zinc-500">{q.impressions || 0} shown</div>
              </div>
            </div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No QR campaigns yet</div>}
      </div>
    </div>
  );
}
