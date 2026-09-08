import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function ApiKeys() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState(["read:campaigns","read:analytics"]);
  const [newKey, setNewKey] = useState(null);
  const load = () => api.get("/admin/api-keys").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    try {
      const { data } = await api.post("/admin/api-keys", { name, scopes });
      setNewKey(data.api_key); setName(""); toast.success("Key created — copy now"); load();
    } catch { toast.error("Failed"); }
  };
  const revoke = async (id) => { await api.delete(`/admin/api-keys/${id}`); load(); };
  const toggleScope = (s) => setScopes(scopes.includes(s) ? scopes.filter(x=>x!==s) : [...scopes, s]);
  const ALL_SCOPES = ["read:campaigns","read:analytics","read:devices"];
  return (
    <div data-testid="admin-apikeys" className="space-y-4">
      <div className="border border-zinc-800 p-4 space-y-3">
        <input data-testid="key-name" placeholder="Key name (e.g. Zapier prod)" value={name} onChange={e=>setName(e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded w-full" />
        <div className="flex flex-wrap gap-2">
          {ALL_SCOPES.map(s => (
            <button key={s} data-testid={`scope-${s}`} onClick={()=>toggleScope(s)} className={`text-xs px-3 py-1.5 rounded border ${scopes.includes(s)?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-700 text-zinc-300"}`}>{s}</button>
          ))}
        </div>
        <button data-testid="key-create" onClick={create} disabled={!name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded text-sm font-medium">Create key</button>
      </div>
      {newKey && (
        <div className="border border-yellow-400/40 bg-yellow-400/5 p-4" data-testid="new-key-display">
          <div className="text-xs uppercase tracking-widest text-yellow-400 mb-2">Copy this API key now — it will not be shown again</div>
          <div className="font-mono text-sm break-all bg-zinc-950 p-3 rounded border border-zinc-800">{newKey}</div>
          <button onClick={()=>{navigator.clipboard.writeText(newKey); toast.success("Copied"); setNewKey(null);}} className="mt-3 text-xs bg-yellow-400 text-zinc-950 px-3 py-1.5 rounded font-medium">Copy & dismiss</button>
        </div>
      )}
      <div className="border border-zinc-800">
        {rows.map(k => (
          <div key={k.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div>
              <div className="font-medium">{k.name}</div>
              <div className="text-xs text-zinc-500 mt-1 font-mono">{k.prefix}… · {(k.scopes||[]).join(", ")}</div>
              <div className="text-xs text-zinc-600 mt-1">Last used: {k.last_used || "never"}</div>
            </div>
            <button data-testid={`key-revoke-${k.id}`} onClick={()=>revoke(k.id)} className="text-xs text-red-400">Revoke</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No API keys yet.</div>}
      </div>
    </div>
  );
}
