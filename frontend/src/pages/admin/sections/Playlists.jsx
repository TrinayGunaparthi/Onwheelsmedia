import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function PlaylistsPage() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const load = () => api.get("/admin/playlists").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);
  const create = async () => {
    if (!name) return;
    try { await api.post("/admin/playlists", { name, device_ids: [], items: [] }); setName(""); toast.success("Created"); load(); } catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-playlists" className="space-y-4">
      <div className="flex gap-2">
        <input data-testid="playlist-name" value={name} onChange={e=>setName(e.target.value)} placeholder="New playlist name" className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded flex-1" />
        <button data-testid="playlist-create" onClick={create} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Create</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(p => (
          <div key={p.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
            <div className="font-medium">{p.name}</div>
            <div className="text-xs text-zinc-500">Devices: {p.device_ids?.length || 0} · Items: {p.items?.length || 0}</div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No playlists yet — the player uses campaign+news+weather+QR automatically.</div>}
      </div>
    </div>
  );
}
