import { useEffect, useState } from "react";
import Shell from "@/pages/Shell";
import { LayoutDashboard, Upload, Megaphone, BarChart3, Wallet, Bell } from "lucide-react";
import { Routes, Route, Navigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";

const nav = [
  { key: "dash", to: "/advertiser", label: "Dashboard", icon: LayoutDashboard },
  { key: "ads", to: "/advertiser/ads", label: "My Ads", icon: Upload },
  { key: "campaigns", to: "/advertiser/campaigns", label: "Campaigns", icon: Megaphone },
  { key: "reports", to: "/advertiser/reports", label: "Reports", icon: BarChart3 },
  { key: "payments", to: "/advertiser/payments", label: "Payments", icon: Wallet },
  { key: "notif", to: "/advertiser/notifications", label: "Notifications", icon: Bell },
];

function Dashboard() {
  const [r, setR] = useState({});
  useEffect(() => { api.get("/advertiser/reports").then(x => setR(x.data)); }, []);
  const cards = [
    { l: "Total Plays", v: r.total_plays },
    { l: "Ads", v: r.ads_count },
    { l: "Campaigns", v: r.campaigns_count },
  ];
  return (
    <div className="space-y-6" data-testid="adv-dashboard">
      <div className="grid grid-cols-3 gap-px bg-zinc-800">
        {cards.map((c,i)=>(
          <div key={i} className="bg-zinc-950 p-6">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className="font-display text-4xl font-bold mt-2 text-yellow-400">{c.v ?? 0}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MyAds() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", duration_seconds: 15, file_url: "", file_type: "", file_path: "" });
  const [uploading, setUploading] = useState(false);
  const load = () => api.get("/ads").then(r => setRows(r.data));
  useEffect(load, []);
  const upload = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", f);
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm({ ...form, file_url: data.url, file_type: data.file_type, file_path: data.path });
      toast.success("Uploaded");
    } catch { toast.error("Upload failed"); } finally { setUploading(false); }
  };
  const submit = async () => {
    try {
      await api.post("/ads", { ...form, start_date: null, end_date: null });
      toast.success("Ad submitted for review");
      setForm({ name: "", description: "", duration_seconds: 15, file_url: "", file_type: "", file_path: "" });
      load();
    } catch (e) { toast.error("Submit failed"); }
  };
  return (
    <div data-testid="adv-ads" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-2 gap-3">
        <input data-testid="ad-name" placeholder="Ad name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="ad-duration" type="number" placeholder="Duration (s)" value={form.duration_seconds} onChange={e=>setForm({...form, duration_seconds:parseInt(e.target.value)||15})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <textarea data-testid="ad-desc" placeholder="Description" value={form.description} onChange={e=>setForm({...form, description:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded md:col-span-2 h-20" />
        <label className="md:col-span-2 border-2 border-dashed border-zinc-800 hover:border-yellow-400 rounded p-4 text-center cursor-pointer">
          <input data-testid="ad-file" type="file" accept="image/*,video/*" hidden onChange={upload} />
          {uploading ? "Uploading…" : form.file_url ? "✓ File uploaded — click to replace" : "Click to upload image or video"}
        </label>
        {form.file_url && form.file_type === "image" && <img src={`${process.env.REACT_APP_BACKEND_URL}${form.file_url}`} alt="preview" className="md:col-span-2 max-h-48 rounded border border-zinc-800 object-contain" />}
        <button data-testid="ad-submit" onClick={submit} disabled={!form.name || !form.file_url} className="md:col-span-2 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Submit for review</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(a => (
          <div key={a.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium">{a.name}</div><div className="text-xs text-zinc-500">{a.description}</div></div>
            <span className={`px-2 py-1 rounded text-xs h-fit ${a.status==="Approved"?"bg-green-500/20 text-green-400":a.status==="Rejected"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400"}`}>{a.status}</span>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Upload your first ad above.</div>}
      </div>
    </div>
  );
}

function Campaigns() {
  const [rows, setRows] = useState([]);
  const [ads, setAds] = useState([]);
  const [form, setForm] = useState({ name: "", ad_id: "", start_date: new Date().toISOString().slice(0,10), end_date: "", budget: 5000, objective: "Awareness", frequency: 3 });
  const load = async () => {
    const [c, a] = await Promise.all([api.get("/campaigns"), api.get("/ads")]);
    setRows(c.data); setAds(a.data);
  };
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { await api.post("/campaigns", { ...form, target_locations: [], target_devices: [] }); toast.success("Campaign created"); load(); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="adv-campaigns" className="space-y-4">
      <div className="border border-zinc-800 p-4 grid md:grid-cols-3 gap-3">
        <input data-testid="camp-name" placeholder="Campaign name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <select data-testid="camp-ad" value={form.ad_id} onChange={e=>setForm({...form, ad_id:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          <option value="">Select ad…</option>
          {ads.map(a => <option key={a.id} value={a.id}>{a.name} — {a.status}</option>)}
        </select>
        <select data-testid="camp-obj" value={form.objective} onChange={e=>setForm({...form, objective:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
          {["Awareness","Reach","Engagement","QR scans","Promotion"].map(o=><option key={o}>{o}</option>)}
        </select>
        <input data-testid="camp-start" type="date" value={form.start_date} onChange={e=>setForm({...form, start_date:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="camp-end" type="date" value={form.end_date} onChange={e=>setForm({...form, end_date:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <input data-testid="camp-budget" type="number" placeholder="Budget ₹" value={form.budget} onChange={e=>setForm({...form, budget:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="camp-create" onClick={create} disabled={!form.name || !form.ad_id || !form.end_date} className="md:col-span-3 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Create campaign</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(c => (
          <div key={c.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
            <div className="flex justify-between">
              <div><div className="font-medium">{c.name}</div><div className="text-xs text-zinc-500">{c.start_date} → {c.end_date} · {c.objective}</div></div>
              <span className={`px-2 py-1 rounded text-xs h-fit ${c.status==="Active"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{c.status}</span>
            </div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No campaigns yet.</div>}
      </div>
    </div>
  );
}

function Reports() {
  const [r, setR] = useState({ by_day: [], per_campaign: [] });
  useEffect(() => { api.get("/advertiser/reports").then(x => setR(x.data)); }, []);
  return (
    <div className="grid md:grid-cols-2 gap-6" data-testid="adv-reports">
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">Plays by day</div>
        {r.by_day?.map(d => (
          <div key={d.date} className="flex justify-between text-sm py-1"><span className="font-mono text-xs text-zinc-400">{d.date}</span><span className="text-yellow-400 font-medium">{d.plays}</span></div>
        ))}
      </div>
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">By campaign</div>
        {r.per_campaign?.map(c => (
          <div key={c.id} className="flex justify-between text-sm py-1"><span>{c.name}</span><span className="text-yellow-400 font-medium">{c.plays}</span></div>
        ))}
        {(!r.per_campaign?.length) && <div className="text-zinc-500 text-sm">No campaigns yet.</div>}
      </div>
    </div>
  );
}

function Payments() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/payments/invoices").then(r => setRows(r.data)); }, []);
  return (
    <div className="border border-zinc-800" data-testid="adv-payments">
      <div className="p-4 bg-yellow-400/10 text-yellow-300 text-xs border-b border-zinc-800">Stripe checkout coming online — invoices are being drafted for review.</div>
      {rows.map(i => (
        <div key={i.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
          <div className="font-mono text-xs">{i.id}</div>
          <div className="font-medium">₹{i.amount}</div>
          <div><span className="px-2 py-1 rounded text-xs bg-yellow-500/20 text-yellow-400">{i.status}</span></div>
        </div>
      ))}
      {rows.length===0 && <div className="p-12 text-center text-zinc-500">No invoices yet.</div>}
    </div>
  );
}

function Notifications() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/notifications").then(r=>setRows(r.data)); }, []);
  return (
    <div className="border border-zinc-800" data-testid="adv-notifications">
      {rows.map(n => (
        <div key={n.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
          <div className="text-sm">{n.message}</div>
          <div className="text-xs text-zinc-500 mt-1">{n.at?.slice(0,16).replace("T"," ")}</div>
        </div>
      ))}
      {rows.length===0 && <div className="p-12 text-center text-zinc-500">All caught up.</div>}
    </div>
  );
}

export default function AdvertiserApp() {
  return (
    <Shell nav={nav} title="Advertiser">
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="ads" element={<MyAds />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="reports" element={<Reports />} />
        <Route path="payments" element={<Payments />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="*" element={<Navigate to="/advertiser" replace />} />
      </Routes>
    </Shell>
  );
}
