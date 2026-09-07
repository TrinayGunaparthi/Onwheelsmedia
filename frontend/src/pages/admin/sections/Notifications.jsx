import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function Notifications() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/notifications").then(r=>setRows(r.data)); }, []);
  return (
    <div data-testid="admin-notifications" className="border border-zinc-800">
      {rows.map(n => (
        <div key={n.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
          <div className="text-sm">{n.message}</div>
          <div className="text-xs text-zinc-500 mt-1">{n.type} · {n.at?.slice(0,16).replace("T"," ")}</div>
        </div>
      ))}
      {rows.length===0 && <div className="p-12 text-center text-zinc-500">No notifications</div>}
    </div>
  );
}
