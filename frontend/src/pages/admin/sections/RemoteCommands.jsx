import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const COMMANDS = [
  { c: "restart_player", label: "Restart Player" },
  { c: "refresh_playlist", label: "Refresh Playlist" },
  { c: "clear_cache", label: "Clear Cache" },
  { c: "reload_config", label: "Reload Config" },
];
const BULK_ACTIONS = [
  { a: "suspend", label: "Suspend" },
  { a: "activate", label: "Activate" },
  { a: "sync", label: "Force Sync" },
];

export default function RemoteCommands() {
  const [devices, setDevices] = useState([]);
  const [selected, setSelected] = useState([]);
  const load = () => api.get("/admin/devices").then(r => setDevices(r.data));
  useEffect(() => { load(); }, []);
  const toggle = (id) => setSelected(selected.includes(id) ? selected.filter(x=>x!==id) : [...selected, id]);
  const toggleAll = () => setSelected(selected.length===devices.length ? [] : devices.map(d=>d.id));
  const runBulk = async (action) => {
    if (!selected.length) return toast.error("Select devices first");
    try { const {data} = await api.post("/admin/devices/bulk-op", { device_ids: selected, action, payload: {} }); toast.success(`${data.affected} devices affected`); setSelected([]); load(); }
    catch { toast.error("Failed"); }
  };
  const runCommand = async (command) => {
    if (!selected.length) return toast.error("Select devices first");
    try { const {data} = await api.post("/admin/devices/bulk-op", { device_ids: selected, action: "remote_command", payload: { command } }); toast.success(`Command queued for ${data.affected} devices`); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-remote" className="space-y-4">
      <div className="border border-zinc-800 p-4 flex flex-wrap gap-2 items-center">
        <div className="text-xs uppercase tracking-widest text-zinc-500">Bulk actions</div>
        {BULK_ACTIONS.map(({a,label}) => <button key={a} data-testid={`bulk-${a}`} onClick={()=>runBulk(a)} className="text-xs px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded">{label}</button>)}
        <div className="text-xs uppercase tracking-widest text-zinc-500 ml-6">Remote commands</div>
        {COMMANDS.map(({c,label}) => <button key={c} data-testid={`cmd-${c}`} onClick={()=>runCommand(c)} className="text-xs px-3 py-1.5 bg-yellow-400/20 hover:bg-yellow-400/30 text-yellow-400 rounded">{label}</button>)}
        <div className="ml-auto text-xs text-zinc-500">{selected.length} selected</div>
      </div>
      <div className="border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
            <tr>
              <th className="p-3"><input data-testid="sel-all" type="checkbox" checked={selected.length===devices.length && devices.length>0} onChange={toggleAll} /></th>
              <th className="text-left p-3">Device</th><th className="text-left p-3">Status</th><th className="text-left p-3">Last online</th><th className="text-left p-3">Storage</th>
            </tr>
          </thead>
          <tbody>
            {devices.map(d => (
              <tr key={d.id} className="border-t border-zinc-800 hover:bg-zinc-900">
                <td className="p-3"><input data-testid={`sel-${d.id}`} type="checkbox" checked={selected.includes(d.id)} onChange={()=>toggle(d.id)} /></td>
                <td className="p-3 font-mono text-xs">{d.device_code}</td>
                <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${d.status==="Online"?"bg-green-500/20 text-green-400":d.status==="Suspended"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400"}`}>{d.status}</span></td>
                <td className="p-3 text-xs text-zinc-400">{d.last_online?.slice(0,16).replace("T"," ") || "never"}</td>
                <td className="p-3 text-xs">{d.storage_pct != null ? `${d.storage_pct}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
