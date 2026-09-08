import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { formatINR } from "@/lib/inr";
import { Calculator, Sparkles } from "lucide-react";

const MODELS = [
  { id: "per_auto", label: "Per Auto" },
  { id: "per_day", label: "Per Day" },
  { id: "per_campaign", label: "Per Campaign" },
  { id: "cpm", label: "CPM (Impressions)" },
  { id: "auto_duration", label: "Autos × Duration" },
  { id: "auto_impressions", label: "Autos + Impressions" },
];

export default function AdvertiserPricing() {
  const [plans, setPlans] = useState([]);
  const [cpm, setCpm] = useState([]);
  const [settings, setSettings] = useState({ currency_symbol: "₹", gst_enabled: true, gst_percentage: 18 });
  const [quotes, setQuotes] = useState([]);
  const [ads, setAds] = useState([]);
  const [durations, setDurations] = useState([]);

  // calculator state
  const [calc, setCalc] = useState({ autos: 10, duration_days: 7, estimated_impressions: 100000, pricing_model: "per_auto", discount_code: "" });
  const [result, setResult] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [showCustom, setShowCustom] = useState(false);
  const [showBuy, setShowBuy] = useState(false);
  const [buyName, setBuyName] = useState("");
  const [buyAdId, setBuyAdId] = useState("");
  const [buyCity, setBuyCity] = useState("");
  const [customForm, setCustomForm] = useState({ autos: 25, target_city: "", duration_days: 15, estimated_views: 500000, ad_format: "video", special_requirements: "", contact_name: "", contact_phone: "" });

  useEffect(() => {
    api.get("/plans/public").then(r=>setPlans(r.data));
    api.get("/cpm-tiers/public").then(r=>setCpm(r.data));
    api.get("/pricing-settings/public").then(r=>setSettings(r.data));
    api.get("/duration-options/public").then(r=>setDurations(r.data));
    api.get("/ads").then(r=>setAds(r.data)).catch(()=>{});
    api.get("/quotes/mine").then(r=>setQuotes(r.data));
  }, []);

  // auto-recalculate whenever calc inputs change
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const { data } = await api.post("/pricing/calculate", { ...calc, plan_id: selectedPlan });
        setResult(data);
      } catch (e) { setResult(null); }
    }, 250);
    return () => clearTimeout(t);
  }, [calc, selectedPlan]);

  const submitQuote = async () => {
    try { await api.post("/quotes/request", customForm); toast.success("Quote request sent to admin"); setShowCustom(false); api.get("/quotes/mine").then(r=>setQuotes(r.data)); }
    catch { toast.error("Failed"); }
  };

  const buy = async () => {
    if (!buyName) return toast.error("Campaign name required");
    try {
      const { data } = await api.post("/pricing/purchase", { ...calc, plan_id: selectedPlan, campaign_name: buyName, ad_id: buyAdId, target_city: buyCity, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) { toast.error(e.response?.data?.detail || "Purchase failed"); }
  };

  const chooseDuration = durations.length ? durations : [{days:1,label:"1 day"},{days:3,label:"3 days"},{days:7,label:"7 days"},{days:15,label:"15 days"},{days:30,label:"30 days"}];

  return (
    <div data-testid="adv-pricing" className="space-y-8">
      {/* Plans */}
      <div>
        <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3">Choose your advertising plan</div>
        <div className="grid md:grid-cols-3 gap-4">
          {plans.map(p => (
            <div key={p.id} data-testid={`plan-card-${p.id}`} className={`border p-6 relative ${selectedPlan===p.id?"border-yellow-400 bg-yellow-400/5":"border-zinc-800 hover:border-zinc-600"}`}>
              <div className="font-display text-2xl font-bold">{p.name}</div>
              <div className="text-xs text-zinc-500 uppercase tracking-widest mt-1">{p.pricing_model.replace(/_/g," ")}</div>
              <div className="mt-4 text-4xl font-display font-bold text-yellow-400">{formatINR(p.price_inr, settings.currency_symbol)}</div>
              <div className="mt-4 space-y-1 text-sm text-zinc-400">
                <div>{p.autos} auto{p.autos>1?"s":""}</div>
                <div>{p.duration_days} days</div>
                <div>Est. reach: {(p.estimated_reach || 0).toLocaleString("en-IN")}</div>
                {(p.features || []).map((f,i)=><div key={i}>· {f}</div>)}
              </div>
              <button data-testid={`plan-select-${p.id}`} onClick={()=>{ setSelectedPlan(p.id); setCalc({...calc, autos: p.autos, duration_days: p.duration_days, pricing_model: p.pricing_model}); }} className={`mt-6 w-full py-3 rounded font-medium ${selectedPlan===p.id?"bg-yellow-400 text-zinc-950":"bg-zinc-900 border border-zinc-700 text-white hover:border-yellow-400"}`}>
                {selectedPlan===p.id ? "Selected" : "Choose plan"}
              </button>
            </div>
          ))}
          <div className="border border-dashed border-cyan-500/40 bg-cyan-500/5 p-6 flex flex-col">
            <div className="font-display text-2xl font-bold text-cyan-300">Custom</div>
            <div className="text-xs text-zinc-500 uppercase tracking-widest mt-1">Talk to us</div>
            <div className="text-sm text-zinc-400 mt-4">Choose any number of autos, cities, duration and impressions. We'll craft a custom quote for you.</div>
            <button data-testid="request-quote" onClick={()=>setShowCustom(true)} className="mt-auto w-full bg-cyan-500 hover:bg-cyan-400 text-zinc-950 py-3 rounded font-medium">Get custom quote</button>
          </div>
        </div>
        {plans.length===0 && <div className="p-12 text-center text-zinc-500 border border-zinc-800">Plans will appear here once admin publishes pricing.</div>}
      </div>

      {/* CPM display */}
      {cpm.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3">Advertising by impressions (CPM)</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {cpm.map(t => (
              <div key={t.id} className="border border-zinc-800 p-4">
                <div className="text-xs text-zinc-500 uppercase tracking-widest">Estimated impressions</div>
                <div className="font-display text-2xl font-bold mt-1">{t.views.toLocaleString("en-IN")}</div>
                <div className="text-yellow-400 font-mono mt-2">{formatINR(t.price_inr, settings.currency_symbol)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Calculator */}
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-yellow-400 mb-4 flex items-center gap-2"><Calculator className="w-3 h-3"/> Price calculator</div>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-widest">Number of autos</label>
              <input data-testid="calc-autos" type="number" min={1} value={calc.autos} onChange={e=>{setSelectedPlan(null); setCalc({...calc, autos:parseInt(e.target.value)||1});}} className="mt-1 w-full bg-zinc-900 border border-zinc-800 px-3 py-2 rounded text-sm" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-widest">Duration</label>
              <select data-testid="calc-duration" value={calc.duration_days} onChange={e=>{setSelectedPlan(null); setCalc({...calc, duration_days:parseInt(e.target.value)});}} className="mt-1 w-full bg-zinc-900 border border-zinc-800 px-3 py-2 rounded text-sm">
                {chooseDuration.map(d=><option key={d.days} value={d.days}>{d.label || `${d.days} days`}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-widest">Estimated impressions</label>
              <input data-testid="calc-imp" type="number" min={0} step={1000} value={calc.estimated_impressions} onChange={e=>setCalc({...calc, estimated_impressions:parseInt(e.target.value)||0})} className="mt-1 w-full bg-zinc-900 border border-zinc-800 px-3 py-2 rounded text-sm" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-widest">Pricing model</label>
              <select data-testid="calc-model" value={calc.pricing_model} onChange={e=>{setSelectedPlan(null); setCalc({...calc, pricing_model:e.target.value});}} className="mt-1 w-full bg-zinc-900 border border-zinc-800 px-3 py-2 rounded text-sm">
                {MODELS.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-widest">Discount code (optional)</label>
              <input data-testid="calc-code" placeholder="e.g. LAUNCH10" value={calc.discount_code} onChange={e=>setCalc({...calc, discount_code:e.target.value.toUpperCase()})} className="mt-1 w-full bg-zinc-900 border border-zinc-800 px-3 py-2 rounded text-sm font-mono" />
            </div>
          </div>
          <div className="bg-zinc-900 p-6 rounded space-y-3" data-testid="calc-result">
            <div className="text-xs uppercase tracking-widest text-zinc-500">Estimated campaign cost</div>
            {result ? (
              <>
                <div className="space-y-1">
                  {(result.breakdown || []).map((b,i)=>(
                    <div key={i} className="flex justify-between text-sm"><span className="text-zinc-400">{b.label}</span><span>{formatINR(b.amount, result.symbol)}</span></div>
                  ))}
                </div>
                <div className="border-t border-zinc-800 pt-3 space-y-1 text-sm">
                  <div className="flex justify-between"><span>Subtotal</span><span>{formatINR(result.subtotal, result.symbol)}</span></div>
                  {result.discount > 0 && <div className="flex justify-between text-green-400"><span>Discount {result.discount_info?.code && `(${result.discount_info.code})`}</span><span>-{formatINR(result.discount, result.symbol)}</span></div>}
                  {result.gst_enabled && <div className="flex justify-between text-zinc-400"><span>GST ({result.gst_percentage}%)</span><span>{formatINR(result.gst_amount, result.symbol)}</span></div>}
                </div>
                <div className="border-t border-zinc-800 pt-3 flex justify-between items-center">
                  <span className="text-xs uppercase tracking-widest text-zinc-500">Total</span>
                  <span className="font-display text-4xl font-bold text-yellow-400" data-testid="calc-total">{formatINR(result.total, result.symbol)}</span>
                </div>
                <button data-testid="proceed-buy" onClick={()=>setShowBuy(true)} disabled={result.total<=0} className="w-full mt-4 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 py-3 rounded font-semibold flex items-center justify-center gap-2"><Sparkles className="w-4 h-4"/> Proceed to payment</button>
              </>
            ) : <div className="text-zinc-500 text-sm">Configure pricing rules in Admin → Pricing to calculate.</div>}
          </div>
        </div>
      </div>

      {/* My custom quote requests */}
      {quotes.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-widest text-yellow-400 mb-3">My quote requests</div>
          <div className="border border-zinc-800">
            {quotes.map(q => (
              <div key={q.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
                <div><div className="font-medium">{q.autos} autos · {q.duration_days} days · {q.target_city || "—"}</div><div className="text-xs text-zinc-500">{q.admin_notes || "Awaiting reply"}</div></div>
                <div className="text-right">
                  {q.admin_price_inr ? <div className="text-yellow-400 font-mono">{formatINR(q.admin_price_inr, settings.currency_symbol)}</div> : null}
                  <span className={`text-xs px-2 py-1 rounded ${q.status==="approved"?"bg-green-500/20 text-green-400":q.status==="rejected"?"bg-red-500/20 text-red-400":q.status==="quoted"?"bg-cyan-500/20 text-cyan-400":"bg-yellow-500/20 text-yellow-400"}`}>{q.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Custom quote modal */}
      {showCustom && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm grid place-items-center z-50 p-6" onClick={()=>setShowCustom(false)}>
          <div className="w-full max-w-lg bg-zinc-950 border border-zinc-800 rounded p-6 space-y-3" onClick={e=>e.stopPropagation()} data-testid="custom-quote-modal">
            <div className="font-display text-xl font-bold">Request custom quote</div>
            <div className="grid grid-cols-2 gap-3">
              <input data-testid="cq-autos" type="number" min={1} placeholder="Number of autos" value={customForm.autos} onChange={e=>setCustomForm({...customForm, autos:parseInt(e.target.value)||1})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-days" type="number" min={1} placeholder="Duration (days)" value={customForm.duration_days} onChange={e=>setCustomForm({...customForm, duration_days:parseInt(e.target.value)||1})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-city" placeholder="Target city" value={customForm.target_city} onChange={e=>setCustomForm({...customForm, target_city:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-views" type="number" placeholder="Estimated views" value={customForm.estimated_views} onChange={e=>setCustomForm({...customForm, estimated_views:parseInt(e.target.value)||0})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-format" placeholder="Ad format (video/image)" value={customForm.ad_format} onChange={e=>setCustomForm({...customForm, ad_format:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-name" placeholder="Contact name" value={customForm.contact_name} onChange={e=>setCustomForm({...customForm, contact_name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <input data-testid="cq-phone" placeholder="Phone" value={customForm.contact_phone} onChange={e=>setCustomForm({...customForm, contact_phone:e.target.value})} className="col-span-2 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
              <textarea data-testid="cq-notes" placeholder="Special requirements" value={customForm.special_requirements} onChange={e=>setCustomForm({...customForm, special_requirements:e.target.value})} className="col-span-2 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded h-20" />
            </div>
            <button data-testid="cq-submit" onClick={submitQuote} className="w-full bg-cyan-500 text-zinc-950 py-3 rounded font-semibold">Submit quote request</button>
          </div>
        </div>
      )}

      {/* Buy modal */}
      {showBuy && result && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm grid place-items-center z-50 p-6" onClick={()=>setShowBuy(false)}>
          <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded p-6 space-y-3" onClick={e=>e.stopPropagation()} data-testid="buy-modal">
            <div className="font-display text-xl font-bold">Confirm campaign</div>
            <input data-testid="buy-name" placeholder="Campaign name" value={buyName} onChange={e=>setBuyName(e.target.value)} className="w-full bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
            <input data-testid="buy-city" placeholder="Target city (optional)" value={buyCity} onChange={e=>setBuyCity(e.target.value)} className="w-full bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
            <select data-testid="buy-ad" value={buyAdId} onChange={e=>setBuyAdId(e.target.value)} className="w-full bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
              <option value="">(no ad linked — attach later)</option>
              {ads.map(a=><option key={a.id} value={a.id}>{a.name} · {a.status}</option>)}
            </select>
            <div className="bg-zinc-900 p-4 rounded flex justify-between items-center">
              <div><div className="text-xs text-zinc-500 uppercase tracking-widest">You'll be charged</div><div className="text-xs text-zinc-400 mt-1">in Indian Rupees (INR)</div></div>
              <div className="font-display text-3xl font-bold text-yellow-400">{formatINR(result.total, result.symbol)}</div>
            </div>
            <button data-testid="buy-checkout" onClick={buy} disabled={!buyName} className="w-full bg-yellow-400 disabled:opacity-40 text-zinc-950 py-3 rounded font-semibold">Pay with Stripe →</button>
            <div className="text-xs text-zinc-500 text-center">Test card 4242 4242 4242 4242 · any future date, any CVC</div>
          </div>
        </div>
      )}
    </div>
  );
}
