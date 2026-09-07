import { useEffect, useState } from "react";
import Shell from "@/pages/Shell";
import { LayoutDashboard, Upload, Megaphone, BarChart3, Wallet, Bell, Sparkles } from "lucide-react";
import { Routes, Route, Navigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

const nav = [
  { key: "dash", to: "/advertiser", label: "Dashboard", icon: LayoutDashboard },
  { key: "ads", to: "/advertiser/ads", label: "My Ads", icon: Upload },
  { key: "campaigns", to: "/advertiser/campaigns", label: "Campaigns", icon: Megaphone },
  { key: "analytics", to: "/advertiser/analytics", label: "Advanced Analytics", icon: Sparkles },
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
  const [games, setGames] = useState([]);
  const [form, setForm] = useState({ name: "", ad_id: "", start_date: new Date().toISOString().slice(0,10), end_date: "", budget: 5000, objective: "Awareness", frequency: 3 });
  const [rules, setRules] = useState({}); // per campaign id: {age_groups, genders, time_slots, min_attention, interactive_type, game_id}
  const load = async () => {
    const [c, a, g] = await Promise.all([api.get("/campaigns"), api.get("/ads"), api.get("/games/list").catch(()=>({data:[]}))]);
    setRows(c.data); setAds(a.data); setGames(g.data);
  };
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { await api.post("/campaigns", { ...form, target_locations: [], target_devices: [] }); toast.success("Campaign created"); load(); }
    catch { toast.error("Failed"); }
  };
  const saveRules = async (id) => {
    const r = rules[id] || {};
    const payload = {
      targeting_rules: {
        age_groups: r.age_groups || [],
        genders: r.genders || [],
        time_slots: r.time_slots || [],
        min_attention: r.min_attention || 0,
        min_viewers: r.min_viewers || 0,
      },
      interactive: r.interactive_type ? { type: r.interactive_type, game_id: r.game_id || "", qr_id: r.qr_id || "", coupon_code: r.coupon_code || "" } : null
    };
    try { await api.patch(`/campaigns/${id}/rules`, payload); toast.success("AI targeting saved"); load(); }
    catch { toast.error("Save failed"); }
  };
  const toggleArr = (id, key, val) => {
    setRules(prev => {
      const cur = { ...(prev[id] || {}) };
      const arr = new Set(cur[key] || []);
      if (arr.has(val)) arr.delete(val); else arr.add(val);
      cur[key] = Array.from(arr);
      return { ...prev, [id]: cur };
    });
  };
  const setRuleField = (id, key, val) => setRules(prev => ({ ...prev, [id]: { ...(prev[id]||{}), [key]: val } }));
  const AGE = ["18-24","25-34","35-44","45-54","55+"];
  const SLOTS = ["morning","afternoon","evening","night"];

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
        <input data-testid="camp-budget" type="number" placeholder="Budget" value={form.budget} onChange={e=>setForm({...form, budget:parseFloat(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="camp-create" onClick={create} disabled={!form.name || !form.ad_id || !form.end_date} className="md:col-span-3 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Create campaign</button>
      </div>
      <div className="space-y-2">
        {rows.map(c => {
          const r = rules[c.id] || c.targeting_rules || {};
          const inter = c.interactive || {};
          return (
            <details key={c.id} className="border border-zinc-800 hover:bg-zinc-900/50">
              <summary className="p-4 flex justify-between cursor-pointer">
                <div><div className="font-medium">{c.name}</div><div className="text-xs text-zinc-500">{c.start_date} → {c.end_date} · {c.objective}</div></div>
                <span className={`px-2 py-1 rounded text-xs h-fit ${c.status==="Active"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{c.status}</span>
              </summary>
              <div className="p-4 border-t border-zinc-800 space-y-4">
                <div className="text-xs uppercase tracking-widest text-yellow-400">AI Audience Targeting</div>
                <div>
                  <label className="text-xs text-zinc-500 mb-2 block">Age groups (any-match)</label>
                  <div className="flex flex-wrap gap-2">
                    {AGE.map(a => (
                      <button key={a} data-testid={`rule-age-${c.id}-${a}`} onClick={()=>toggleArr(c.id, "age_groups", a)} className={`text-xs px-3 py-1.5 rounded border ${(r.age_groups||[]).includes(a)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-300"}`}>{a}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 mb-2 block">Gender</label>
                  <div className="flex gap-2">
                    {["male","female"].map(g => (
                      <button key={g} data-testid={`rule-gender-${c.id}-${g}`} onClick={()=>toggleArr(c.id, "genders", g)} className={`text-xs px-3 py-1.5 rounded border capitalize ${(r.genders||[]).includes(g)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-300"}`}>{g}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 mb-2 block">Time slots</label>
                  <div className="flex flex-wrap gap-2">
                    {SLOTS.map(s => (
                      <button key={s} data-testid={`rule-slot-${c.id}-${s}`} onClick={()=>toggleArr(c.id, "time_slots", s)} className={`text-xs px-3 py-1.5 rounded border capitalize ${(r.time_slots||[]).includes(s)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-300"}`}>{s}</button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-500 mb-1 block">Min attention (0-100)</label>
                    <input data-testid={`rule-attention-${c.id}`} type="number" min={0} max={100} value={r.min_attention || 0} onChange={e=>setRuleField(c.id, "min_attention", parseInt(e.target.value)||0)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 mb-1 block">Min viewers</label>
                    <input data-testid={`rule-viewers-${c.id}`} type="number" min={0} value={r.min_viewers || 0} onChange={e=>setRuleField(c.id, "min_viewers", parseInt(e.target.value)||0)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" />
                  </div>
                </div>
                <div className="pt-4 border-t border-zinc-800">
                  <div className="text-xs uppercase tracking-widest text-yellow-400 mb-2">Interactive layer</div>
                  <div className="flex items-center gap-3">
                    <select data-testid={`inter-type-${c.id}`} value={r.interactive_type || inter.type || ""} onChange={e=>setRuleField(c.id, "interactive_type", e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
                      <option value="">None</option>
                      <option value="game">Mini-game (QR)</option>
                      <option value="coupon">Coupon code</option>
                    </select>
                    {(r.interactive_type || inter.type) === "game" && (
                      <select data-testid={`inter-game-${c.id}`} value={r.game_id || inter.game_id || ""} onChange={e=>setRuleField(c.id, "game_id", e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded flex-1">
                        <option value="">Select game…</option>
                        {games.map(g => <option key={g.id} value={g.id}>{g.name} ({g.game_type})</option>)}
                      </select>
                    )}
                    {(r.interactive_type || inter.type) === "coupon" && (
                      <input data-testid={`inter-coupon-${c.id}`} placeholder="Coupon code" value={r.coupon_code || inter.coupon_code || ""} onChange={e=>setRuleField(c.id, "coupon_code", e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded flex-1" />
                    )}
                  </div>
                </div>
                <button data-testid={`save-rules-${c.id}`} onClick={()=>saveRules(c.id)} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Save AI rules</button>
              </div>
            </details>
          );
        })}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500 border border-zinc-800">No campaigns yet.</div>}
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
  const [amount, setAmount] = useState(50);
  const [loading, setLoading] = useState(false);
  const load = () => api.get("/payments/invoices").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const topUp = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/payments/checkout", { amount: parseFloat(amount), origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) { toast.error(e.response?.data?.detail || "Checkout failed"); setLoading(false); }
  };
  return (
    <div className="space-y-6" data-testid="adv-payments">
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">Top up campaign budget</div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-zinc-400 text-sm">$</span>
            <input data-testid="topup-amount" type="number" min="1" step="1" value={amount} onChange={e=>setAmount(e.target.value)} className="w-32 bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-3 py-2 text-sm rounded" />
          </div>
          {[25,50,100,250].map(v => (
            <button key={v} data-testid={`preset-${v}`} type="button" onClick={()=>setAmount(v)} className="text-xs px-3 py-1.5 rounded border border-zinc-800 hover:border-yellow-400 text-zinc-300">${v}</button>
          ))}
          <button data-testid="topup-checkout" onClick={topUp} disabled={loading || amount<1} className="ml-auto bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-6 py-2 text-sm rounded font-semibold">
            {loading ? "Redirecting…" : "Pay with Stripe →"}
          </button>
        </div>
        <div className="mt-3 text-xs text-zinc-500">Powered by Stripe · test card <span className="font-mono">4242 4242 4242 4242</span> · any future date, any CVC</div>
      </div>
      <div className="border border-zinc-800">
        {rows.map(i => (
          <div key={i.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div className="font-mono text-xs">{i.id}</div>
            <div className="font-medium">${i.amount}</div>
            <div><span className={`px-2 py-1 rounded text-xs ${i.status==="Paid"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{i.status}</span></div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No invoices yet.</div>}
      </div>
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
        <Route path="analytics" element={<Analytics />} />
        <Route path="reports" element={<Reports />} />
        <Route path="payments" element={<Payments />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="*" element={<Navigate to="/advertiser" replace />} />
      </Routes>
    </Shell>
  );
}

function Analytics() {
  const [d, setD] = useState({ per_campaign: [], age_distribution: {}, gender_distribution: {} });
  useEffect(() => { api.get("/advertiser/analytics").then(r => setD(r.data)); }, []);
  const cards = [
    { l: "Estimated Impressions", v: d.estimated_impressions, tint: "text-yellow-400" },
    { l: "Estimated Audience", v: d.estimated_audience, tint: "text-cyan-400" },
    { l: "Avg Attention", v: `${d.avg_attention || 0}/100`, tint: (d.avg_attention||0) > 70 ? "text-green-400" : "text-yellow-400" },
    { l: "Game Starts", v: d.game_starts },
    { l: "Game Completions", v: d.game_completions },
    { l: "Campaigns", v: d.per_campaign?.length || 0 },
  ];
  const ageData = Object.entries(d.age_distribution || {}).map(([k,v]) => ({name:k, value:v}));
  return (
    <div data-testid="adv-analytics" className="space-y-6">
      <div className="text-xs text-zinc-500 uppercase tracking-widest">Powered by AI Audience Analytics · Anonymous aggregates</div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-zinc-800">
        {cards.map((c, i) => (
          <div key={i} className="bg-zinc-950 p-6">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className={`font-display text-4xl font-bold mt-2 ${c.tint || "text-white"}`}>{c.v ?? 0}</div>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Audience age distribution</div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={ageData}>
                <CartesianGrid stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="#71717a" tick={{fontSize:11}} />
                <YAxis stroke="#71717a" tick={{fontSize:11}} />
                <Tooltip contentStyle={{background:"#18181b",border:"1px solid #27272a"}} />
                <Bar dataKey="value" fill="#06b6d4" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">By campaign</div>
          {d.per_campaign?.map(c => (
            <div key={c.id} className="flex justify-between py-2 border-b border-zinc-800 last:border-0 text-sm">
              <span>{c.name}</span>
              <span><span className="text-yellow-400 font-medium">{c.plays}</span> plays · <span className="text-cyan-400">{c.game_starts}</span> games</span>
            </div>
          ))}
          {(!d.per_campaign?.length) && <div className="text-zinc-500 text-sm">No campaigns yet.</div>}
        </div>
      </div>
    </div>
  );
}
