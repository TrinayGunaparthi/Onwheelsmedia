import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Privacy() {
  const [cfg, setCfg] = useState(null);
  useEffect(() => { api.get("/admin/privacy").then(r => setCfg(r.data)); }, []);
  const save = async () => {
    try { await api.patch("/admin/privacy", cfg); toast.success("Privacy settings saved"); }
    catch { toast.error("Save failed"); }
  };
  if (!cfg) return <div className="text-zinc-500">Loading…</div>;
  const Toggle = ({label, k, hint}) => (
    <label className="flex items-start justify-between border border-zinc-800 p-4 rounded cursor-pointer hover:bg-zinc-900">
      <div>
        <div className="font-medium">{label}</div>
        {hint && <div className="text-xs text-zinc-500 mt-1">{hint}</div>}
      </div>
      <input data-testid={`priv-${k}`} type="checkbox" checked={!!cfg[k]} onChange={e=>setCfg({...cfg, [k]:e.target.checked})} className="w-5 h-5 accent-yellow-400 mt-1" />
    </label>
  );
  return (
    <div data-testid="admin-privacy" className="max-w-2xl space-y-4">
      <div className="text-xs text-zinc-500 uppercase tracking-widest">Privacy-first AI · Local processing only</div>
      <Toggle label="Camera enabled" k="camera_enabled" hint="Allow device cameras to run local face detection." />
      <Toggle label="Face analysis enabled" k="face_analysis_enabled" hint="Estimate age/gender buckets locally on-device." />
      <Toggle label="Show camera notice to passengers" k="show_camera_notice" hint="A small privacy label appears on the player." />
      <Toggle label="Screen mirroring enabled" k="mirror_enabled" hint="Passengers can push content to the screen via QR." />
      <label className="flex items-start justify-between border border-red-500/30 p-4 rounded bg-red-500/5">
        <div>
          <div className="font-medium text-red-300">Upload raw camera footage</div>
          <div className="text-xs text-zinc-500 mt-1">Never enable unless required by a specific lawful, configured feature.</div>
        </div>
        <input data-testid="priv-upload_raw_footage" type="checkbox" checked={!!cfg.upload_raw_footage} onChange={e=>setCfg({...cfg, upload_raw_footage:e.target.checked})} className="w-5 h-5 accent-red-400 mt-1" />
      </label>
      <div className="border border-zinc-800 p-4 rounded">
        <div className="font-medium mb-2">Data retention (days)</div>
        <input data-testid="priv-retention" type="number" min={1} max={365} value={cfg.data_retention_days} onChange={e=>setCfg({...cfg, data_retention_days:parseInt(e.target.value)||30})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-32" />
        <div className="text-xs text-zinc-500 mt-2">Anonymous audience samples older than this are eligible for cleanup.</div>
      </div>
      <button data-testid="privacy-save" onClick={save} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-6 py-3 rounded font-semibold">Save settings</button>
    </div>
  );
}
