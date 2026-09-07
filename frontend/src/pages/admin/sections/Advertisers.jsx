import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function Advertisers() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/advertisers").then(r => setRows(r.data)); }, []);
  return (
    <div data-testid="admin-advertisers" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Company</th><th className="text-left p-3">Contact</th><th className="text-left p-3">Email</th><th className="text-left p-3">Phone</th><th className="text-left p-3">Joined</th></tr>
        </thead>
        <tbody>
          {rows.map(a => (
            <tr key={a.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-medium">{a.company || a.profile?.company || "—"}</td>
              <td className="p-3 text-zinc-400">{a.name}</td>
              <td className="p-3 font-mono text-xs">{a.email}</td>
              <td className="p-3 font-mono text-xs">{a.phone || "—"}</td>
              <td className="p-3 text-xs text-zinc-500">{a.created_at?.slice(0,10)}</td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={5} className="p-12 text-center text-zinc-500">No advertisers yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
