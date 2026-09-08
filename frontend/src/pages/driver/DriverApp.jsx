import { useEffect, useState } from "react";
import Shell from "@/pages/Shell";
import api from "@/lib/api";
import { LayoutDashboard, User, Cpu, Wallet } from "lucide-react";
import { Routes, Route, Navigate } from "react-router-dom";
import { toast } from "sonner";

const nav = [
  { key: "dash", to: "/driver", label: "Dashboard", icon: LayoutDashboard },
  { key: "profile", to: "/driver/profile", label: "My Profile", icon: User },
  { key: "device", to: "/driver/device", label: "Device", icon: Cpu },
  { key: "earnings", to: "/driver/earnings", label: "Earnings", icon: Wallet },
];

function Dashboard() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/drivers/me").then(r => setD(r.data)); }, []);
  if (!d) return <div className="text-center text-zinc-500 py-12" data-testid="driver-dashboard">Complete your registration in the Profile tab.</div>;
  return (
    <div className="space-y-6" data-testid="driver-dashboard">
      <div className="grid md:grid-cols-3 gap-px bg-zinc-800">
        <div className="bg-zinc-950 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500">Status</div>
          <div className={`font-display text-3xl font-bold mt-2 ${d.driver?.status==="Approved"?"text-green-400":"text-yellow-400"}`}>{d.driver?.status}</div>
        </div>
        <div className="bg-zinc-950 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500">Vehicle</div>
          <div className="font-mono text-lg mt-2">{d.driver?.vehicle_reg_no}</div>
          <div className="text-xs text-zinc-500">{d.driver?.manufacturer} {d.driver?.model}</div>
        </div>
        <div className="bg-zinc-950 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500">Area</div>
          <div className="text-lg mt-2">{d.driver?.operating_area}</div>
        </div>
      </div>
    </div>
  );
}

function Profile() {
  const [existing, setExisting] = useState(null);
  const [form, setForm] = useState({
    full_name: "", phone: "", address: "", city: "", state: "",
    vehicle_reg_no: "", vehicle_type: "Auto Rickshaw", manufacturer: "Bajaj", model: "", year: 2022,
    color: "Yellow-Green", operating_area: "", preferred_routes: ""
  });
  const [documents, setDocuments] = useState([]); // {type, name, url, path}
  const [uploadingType, setUploadingType] = useState("");
  useEffect(() => {
    api.get("/drivers/me").then(r => {
      if (r.data?.driver) {
        setExisting(r.data.driver);
        setForm({...form, ...r.data.driver});
        setDocuments(r.data.driver.documents || []);
      }
    });
  }, []);
  const uploadDoc = async (docType, file) => {
    if (!file) return;
    setUploadingType(docType);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setDocuments((prev) => [...prev.filter(d => d.type !== docType), { type: docType, name: file.name, url: data.url, path: data.path }]);
      toast.success(`${docType} uploaded`);
    } catch { toast.error("Upload failed"); }
    finally { setUploadingType(""); }
  };
  const submit = async () => {
    try { await api.post("/drivers", { ...form, documents }); toast.success("Submitted for approval"); location.reload(); }
    catch (e) { toast.error("Submit failed"); }
  };
  const docTypes = [
    { key: "rc_book", label: "RC Book (vehicle registration)" },
    { key: "driver_license", label: "Driver License" },
    { key: "insurance", label: "Insurance Certificate" },
    { key: "profile_photo", label: "Profile Photo" },
  ];
  return (
    <div data-testid="driver-profile" className="max-w-3xl space-y-6">
      {existing && <div className="p-3 border border-zinc-800 bg-zinc-900 rounded text-xs">Status: <span className="text-yellow-400 font-medium">{existing.status}</span></div>}
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">Personal & Vehicle</div>
        <div className="grid md:grid-cols-2 gap-3">
          {[
            ["full_name","Full name"],["phone","Phone"],["address","Address"],["city","City"],["state","State"],
            ["vehicle_reg_no","Vehicle registration"],["manufacturer","Manufacturer"],["model","Model"],["color","Color"],["operating_area","Operating area"],["preferred_routes","Preferred routes"]
          ].map(([k,l]) => (
            <input data-testid={`d-${k}`} key={k} placeholder={l} value={form[k]||""} onChange={e=>setForm({...form, [k]:e.target.value})} className="bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-3 py-2 text-sm rounded" />
          ))}
          <input data-testid="d-year" type="number" placeholder="Year" value={form.year||""} onChange={e=>setForm({...form, year:parseInt(e.target.value)||2022})} className="bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-3 py-2 text-sm rounded" />
          <select data-testid="d-vtype" value={form.vehicle_type} onChange={e=>setForm({...form, vehicle_type:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
            {["Auto Rickshaw","E-Rickshaw","Taxi"].map(o=><option key={o}>{o}</option>)}
          </select>
        </div>
      </div>

      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">Documents</div>
        <div className="grid md:grid-cols-2 gap-3">
          {docTypes.map(dt => {
            const uploaded = documents.find(d => d.type === dt.key);
            return (
              <label key={dt.key} className={`border border-dashed rounded p-4 cursor-pointer ${uploaded?"border-green-500/40 bg-green-500/5":"border-zinc-800 hover:border-yellow-400"}`}>
                <input data-testid={`doc-${dt.key}`} type="file" accept="image/*,application/pdf" hidden onChange={e => uploadDoc(dt.key, e.target.files[0])} />
                <div className="text-xs uppercase tracking-widest text-zinc-500">{dt.label}</div>
                <div className="mt-2 text-sm">
                  {uploadingType===dt.key ? <span className="text-yellow-400">Uploading…</span>
                   : uploaded ? <span className="text-green-400">✓ {uploaded.name}</span>
                   : <span className="text-zinc-500">Click to upload</span>}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <button data-testid="d-submit" onClick={submit} className="w-full bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-3 text-sm font-medium rounded">Save & submit for approval</button>
    </div>
  );
}

function Device() {
  const [d, setD] = useState(null);
  const [devices, setDevices] = useState([]);
  const load = async () => {
    const me = await api.get("/drivers/me");
    setD(me.data);
    if (me.data?.vehicle) {
      const dev = await api.get("/devices/mine");
      setDevices(dev.data);
    }
  };
  useEffect(() => { load(); }, []);
  const register = async () => {
    try {
      const { data } = await api.post("/devices/register", { vehicle_id: d.vehicle.id, android_info: navigator.userAgent, app_version: "web-1.0", screen_info: `${window.screen.width}x${window.screen.height}` });
      toast.success(`Device ${data.device_code} pending approval`); load();
    } catch (e) { toast.error("Please complete Profile first"); }
  };
  if (!d?.vehicle) return <div className="text-center py-12 text-zinc-500" data-testid="driver-device">Complete your profile first to register a device.</div>;
  return (
    <div className="space-y-4" data-testid="driver-device">
      <button data-testid="dev-register" onClick={register} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 rounded font-medium text-sm">Register new device</button>
      {devices.map(dev => (
        <div key={dev.id} className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500">Device ID</div>
          <div className="font-mono text-3xl font-bold mt-2">{dev.device_code}</div>
          <div className="mt-4 text-xs uppercase tracking-widest text-zinc-500">Activation Code (enter in player)</div>
          <div className="font-mono text-2xl text-yellow-400 mt-2">{dev.activation_code}</div>
          <div className="mt-4"><span className={`px-2 py-1 rounded text-xs ${dev.status==="Approved"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{dev.status}</span></div>
          <div className="mt-4 text-xs text-zinc-500">Open <a className="text-yellow-400" href="/player" target="_blank" rel="noreferrer">/player</a> on the tablet and enter the activation code.</div>
        </div>
      ))}
    </div>
  );
}

export default function DriverApp() {
  return (
    <Shell nav={nav} title="Driver">
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="profile" element={<Profile />} />
        <Route path="device" element={<Device />} />
        <Route path="earnings" element={<Earnings />} />
        <Route path="*" element={<Navigate to="/driver" replace />} />
      </Routes>
    </Shell>
  );
}

function Earnings() {
  const [d, setD] = useState({});
  useEffect(() => { api.get("/driver/earnings").then(r => setD(r.data)); }, []);
  return (
    <div data-testid="driver-earnings" className="space-y-6">
      <div className="grid grid-cols-3 gap-px bg-zinc-800">
        {[{l:"Total earned",v:`$${d.earnings_total||0}`,tint:"text-yellow-400"},{l:"Paid out",v:`$${d.paid||0}`,tint:"text-green-400"},{l:"Pending",v:`$${d.pending||0}`,tint:"text-orange-400"}].map((c,i)=>(
          <div key={i} className="bg-zinc-950 p-6">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className={`font-display text-4xl font-bold mt-2 ${c.tint}`}>{c.v}</div>
          </div>
        ))}
      </div>
      <div className="text-xs text-zinc-500 uppercase tracking-widest">Rate: <span className="text-yellow-400 font-mono">${d.per_day_rate||0}</span>/day per active device</div>
      <div className="border border-zinc-800">
        <div className="p-3 bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">Payment history</div>
        {(d.payouts || []).map(p => (
          <div key={p.id} className="p-4 border-t border-zinc-800 flex justify-between hover:bg-zinc-900">
            <div><div className="font-medium text-green-400">+${p.amount}</div><div className="text-xs text-zinc-500">{p.note || "Payout"}</div></div>
            <div className="text-xs text-zinc-500">{p.at?.slice(0,16).replace("T"," ")}</div>
          </div>
        ))}
        {(d.payouts || []).length===0 && <div className="p-12 text-center text-zinc-500">No payouts yet.</div>}
      </div>
    </div>
  );
}
