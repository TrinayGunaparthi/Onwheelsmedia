import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { formatINR } from "@/lib/inr";
import { Plus, Trash2, Copy, Pencil, X } from "lucide-react";

const MODELS = ["per_auto","per_day","per_campaign","cpm","auto_duration","auto_impressions","custom_quote"];

function Tab({ id, active, setActive, children }) {
  return <button data-testid={`tab-${id}`} onClick={()=>setActive(id)} className={`px-4 py-2 text-sm rounded-t border-b-2 ${active===id?"border-yellow-400 text-yellow-400":"border-transparent text-zinc-400 hover:text-white"}`}>{children}</button>;
}

function PlansTab() {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const empty = { name: "", autos: 1, duration_days: 7, price_inr: 0, estimated_reach: 0, features: [], pricing_model: "per_campaign", active: true, is_custom: false, sort_order: 0 };
  const [form, setForm] = useState(empty);
  const load = () => api.get("/admin/plans").then(r=>setRows(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      const payload = { ...form, features: (form.features || []).filter(Boolean) };
      if (editing) await api.patch(`/admin/plans/${editing}`, payload);
      else await api.post("/admin/plans", payload);
      toast.success("Saved"); setForm(empty); setEditing(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
  };
  const edit = (r) => { setForm({...r, features: r.features || []}); setEditing(r.id); };
  const del = async (id) => { if (!window.confirm("Delete this plan?")) return; await api.delete(`/admin/plans/${id}`); load(); };
  const dup = async (id) => { await api.post(`/admin/plans/${id}/duplicate`); toast.success("Duplicated"); load(); };
  const toggle = async (r) => { await api.patch(`/admin/plans/${r.id}`, {...r, features: r.features || [], active: !r.active}); load(); };

  return (
    <div className="space-y-4" data-testid="tab-plans-content">
      <div className="border border-zinc-800 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-yellow-400">{editing ? "Edit plan" : "Create new plan"}</div>
          {editing && <button onClick={()=>{setEditing(null); setForm(empty);}} className="text-xs text-zinc-500"><X className="w-3 h-3 inline"/> Cancel</button>}
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          <input data-testid="plan-name" placeholder="Plan name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <input data-testid="plan-autos" type="number" min={1} placeholder="Number of autos" value={form.autos} onChange={e=>setForm({...form, autos:parseInt(e.target.value)||1})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <input data-testid="plan-days" type="number" min={1} placeholder="Duration (days)" value={form.duration_days} onChange={e=>setForm({...form, duration_days:parseInt(e.target.value)||1})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <input data-testid="plan-price" type="number" min={0} placeholder="Price ₹ (INR)" value={form.price_inr} onChange={e=>setForm({...form, price_inr:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <input data-testid="plan-reach" type="number" min={0} placeholder="Estimated reach" value={form.estimated_reach} onChange={e=>setForm({...form, estimated_reach:parseInt(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <select data-testid="plan-model" value={form.pricing_model} onChange={e=>setForm({...form, pricing_model:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
            {MODELS.map(m=><option key={m}>{m}</option>)}
          </select>
          <input data-testid="plan-features" placeholder="Features (comma-separated)" value={(form.features||[]).join(", ")} onChange={e=>setForm({...form, features: e.target.value.split(",").map(s=>s.trim())})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded md:col-span-2" />
          <label className="flex items-center gap-2 text-sm"><input data-testid="plan-active" type="checkbox" checked={form.active} onChange={e=>setForm({...form, active:e.target.checked})} className="accent-yellow-400"/> Active</label>
        </div>
        <button data-testid="plan-save" onClick={save} disabled={!form.name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded font-medium text-sm">{editing?"Update plan":"Create plan"}</button>
      </div>
      <div className="border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
            <tr><th className="text-left p-3">Name</th><th className="text-left p-3">Autos</th><th className="text-left p-3">Duration</th><th className="text-left p-3">Model</th><th className="text-right p-3">Price</th><th className="text-left p-3">Status</th><th className="p-3"></th></tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="border-t border-zinc-800 hover:bg-zinc-900">
                <td className="p-3 font-medium">{r.name}</td>
                <td className="p-3">{r.autos}</td>
                <td className="p-3">{r.duration_days} days</td>
                <td className="p-3 text-xs uppercase text-zinc-500">{r.pricing_model}</td>
                <td className="p-3 text-right font-mono text-yellow-400">{formatINR(r.price_inr)}</td>
                <td className="p-3"><button onClick={()=>toggle(r)} className={`text-xs px-2 py-1 rounded ${r.active?"bg-green-500/20 text-green-400":"bg-zinc-800 text-zinc-500"}`}>{r.active?"Active":"Inactive"}</button></td>
                <td className="p-3 text-right space-x-1">
                  <button data-testid={`plan-edit-${r.id}`} onClick={()=>edit(r)} className="text-xs text-zinc-400 hover:text-yellow-400"><Pencil className="w-4 h-4 inline"/></button>
                  <button onClick={()=>dup(r.id)} className="text-xs text-zinc-400 hover:text-cyan-400"><Copy className="w-4 h-4 inline"/></button>
                  <button data-testid={`plan-del-${r.id}`} onClick={()=>del(r.id)} className="text-xs text-red-400"><Trash2 className="w-4 h-4 inline"/></button>
                </td>
              </tr>
            ))}
            {rows.length===0 && <tr><td colSpan={7} className="p-12 text-center text-zinc-500">No plans yet. Create your first plan above.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CpmTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ views: 1000, price_inr: 0, active: true });
  const load = () => api.get("/admin/cpm-tiers").then(r=>setRows(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => { try { await api.post("/admin/cpm-tiers", form); toast.success("Added"); load(); } catch { toast.error("Failed"); } };
  const del = async (id) => { await api.delete(`/admin/cpm-tiers/${id}`); load(); };
  const toggle = async (r) => { await api.patch(`/admin/cpm-tiers/${r.id}`, {...r, active:!r.active}); load(); };
  return (
    <div className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-3 gap-3">
        <input data-testid="cpm-views" type="number" min={1} placeholder="Number of views" value={form.views} onChange={e=>setForm({...form, views:parseInt(e.target.value)||1})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="cpm-price" type="number" min={0} placeholder="Price ₹" value={form.price_inr} onChange={e=>setForm({...form, price_inr:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="cpm-add" onClick={save} className="bg-yellow-400 text-zinc-950 px-4 py-2 rounded font-medium text-sm"><Plus className="w-4 h-4 inline"/> Add tier</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(r => (
          <div key={r.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium">{r.views.toLocaleString("en-IN")} views</div><div className="text-xs text-zinc-500">= {formatINR(r.price_inr/r.views*1000)} CPM</div></div>
            <div className="flex items-center gap-3">
              <div className="text-yellow-400 font-mono">{formatINR(r.price_inr)}</div>
              <button onClick={()=>toggle(r)} className={`text-xs px-2 py-1 rounded ${r.active?"bg-green-500/20 text-green-400":"bg-zinc-800 text-zinc-500"}`}>{r.active?"Active":"Inactive"}</button>
              <button data-testid={`cpm-del-${r.id}`} onClick={()=>del(r.id)} className="text-red-400 text-xs"><Trash2 className="w-4 h-4"/></button>
            </div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No CPM tiers yet. Add tiers like 1000, 10000, 100000 views.</div>}
      </div>
    </div>
  );
}

function DiscountsTab() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ code: "", kind: "percent", value: 10, description: "", min_amount_inr: 0, active: true });
  const load = () => api.get("/admin/discounts").then(r=>setRows(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => { try { await api.post("/admin/discounts", form); toast.success("Added"); setForm({code:"",kind:"percent",value:10,description:"",min_amount_inr:0,active:true}); load(); } catch(e) { toast.error(e.response?.data?.detail || "Failed"); } };
  const del = async (id) => { await api.delete(`/admin/discounts/${id}`); load(); };
  return (
    <div className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-4 gap-3">
        <input data-testid="disc-code" placeholder="Code (e.g. LAUNCH10)" value={form.code} onChange={e=>setForm({...form, code:e.target.value.toUpperCase()})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded uppercase" />
        <select data-testid="disc-kind" value={form.kind} onChange={e=>setForm({...form, kind:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded"><option value="percent">Percent (%)</option><option value="fixed">Fixed ₹</option></select>
        <input data-testid="disc-value" type="number" min={0} placeholder="Value" value={form.value} onChange={e=>setForm({...form, value:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="disc-min" type="number" min={0} placeholder="Min amount ₹" value={form.min_amount_inr} onChange={e=>setForm({...form, min_amount_inr:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="disc-desc" placeholder="Description (optional)" value={form.description} onChange={e=>setForm({...form, description:e.target.value})} className="md:col-span-3 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="disc-add" onClick={save} disabled={!form.code} className="bg-yellow-400 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded font-medium text-sm">Add discount</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(r => (
          <div key={r.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div><div className="font-mono text-yellow-400 font-medium">{r.code}</div><div className="text-xs text-zinc-500">{r.kind==="percent"?`${r.value}% off`:`${formatINR(r.value)} off`} · min {formatINR(r.min_amount_inr)}</div></div>
            <button onClick={()=>del(r.id)} className="text-red-400 text-xs"><Trash2 className="w-4 h-4"/></button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No discount codes yet.</div>}
      </div>
    </div>
  );
}

function SettingsTab() {
  const [cfg, setCfg] = useState(null);
  useEffect(() => { api.get("/admin/pricing-settings").then(r=>setCfg(r.data)); }, []);
  const save = async () => { try { await api.patch("/admin/pricing-settings", cfg); toast.success("Saved"); } catch { toast.error("Failed"); } };
  if (!cfg) return <div className="text-zinc-500">Loading…</div>;
  return (
    <div className="max-w-2xl space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-xs text-zinc-500 block mb-1">Currency code</label><input data-testid="curr-code" value={cfg.currency_code} onChange={e=>setCfg({...cfg, currency_code:e.target.value.toUpperCase()})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" /></div>
        <div><label className="text-xs text-zinc-500 block mb-1">Currency symbol</label><input data-testid="curr-sym" value={cfg.currency_symbol} onChange={e=>setCfg({...cfg, currency_symbol:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" /></div>
      </div>
      <label className="flex items-center justify-between border border-zinc-800 p-4 rounded"><div><div className="font-medium">GST enabled</div><div className="text-xs text-zinc-500">Add GST to all invoices</div></div><input data-testid="gst-on" type="checkbox" checked={cfg.gst_enabled} onChange={e=>setCfg({...cfg, gst_enabled:e.target.checked})} className="w-5 h-5 accent-yellow-400"/></label>
      <div><label className="text-xs text-zinc-500 block mb-1">GST percentage (%)</label><input data-testid="gst-pct" type="number" min={0} max={100} step="0.5" value={cfg.gst_percentage} onChange={e=>setCfg({...cfg, gst_percentage:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-32" /></div>
      <button data-testid="curr-save" onClick={save} className="bg-yellow-400 text-zinc-950 px-6 py-3 rounded font-semibold">Save currency & tax</button>
    </div>
  );
}

function HistoryTab() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/pricing-history").then(r=>setRows(r.data)); }, []);
  return (
    <div className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">When</th><th className="text-left p-3">Entity</th><th className="text-left p-3">Changed by</th><th className="text-left p-3">Old</th><th className="text-left p-3">New</th></tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-mono text-xs">{r.at?.slice(0,19).replace("T"," ")}</td>
              <td className="p-3 text-xs">{r.entity}</td>
              <td className="p-3 text-xs text-zinc-400">{r.changed_by}</td>
              <td className="p-3 text-xs font-mono text-red-400">{r.old ? JSON.stringify(r.old).slice(0,60) : "—"}</td>
              <td className="p-3 text-xs font-mono text-green-400">{r.new ? JSON.stringify(r.new).slice(0,60) : "—"}</td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={5} className="p-12 text-center text-zinc-500">No price changes recorded yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function Pricing() {
  const [active, setActive] = useState("plans");
  return (
    <div data-testid="admin-pricing" className="space-y-6">
      <div className="border-b border-zinc-800 flex gap-2 overflow-x-auto">
        <Tab id="plans" active={active} setActive={setActive}>Plans</Tab>
        <Tab id="cpm" active={active} setActive={setActive}>CPM tiers</Tab>
        <Tab id="discounts" active={active} setActive={setActive}>Discounts</Tab>
        <Tab id="settings" active={active} setActive={setActive}>Currency & GST</Tab>
        <Tab id="history" active={active} setActive={setActive}>Price history</Tab>
      </div>
      {active==="plans" && <PlansTab/>}
      {active==="cpm" && <CpmTab/>}
      {active==="discounts" && <DiscountsTab/>}
      {active==="settings" && <SettingsTab/>}
      {active==="history" && <HistoryTab/>}
    </div>
  );
}
