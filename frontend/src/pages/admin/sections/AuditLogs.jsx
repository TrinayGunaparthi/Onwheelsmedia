import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function AuditLogs() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/audit").then(r=>setRows(r.data)); }, []);
  return (
    <div data-testid="admin-audit" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">When</th><th className="text-left p-3">User</th><th className="text-left p-3">Action</th><th className="text-left p-3">Entity</th></tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-mono text-xs">{r.at?.slice(0,19).replace("T"," ")}</td>
              <td className="p-3">{r.user_email}</td>
              <td className="p-3 text-yellow-400 text-xs">{r.action}</td>
              <td className="p-3 text-xs text-zinc-500">{r.entity} {r.entity_id?.slice(0,8)}</td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={4} className="p-12 text-center text-zinc-500">No audit logs yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
