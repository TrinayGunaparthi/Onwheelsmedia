import { useEffect, useState } from "react";
import api from "@/lib/api";

export default function VehiclesPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/vehicles").then(r => setRows(r.data)); }, []);
  return (
    <div data-testid="admin-vehicles" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Reg No</th><th className="text-left p-3">Vehicle</th><th className="text-left p-3">Driver</th><th className="text-left p-3">Area</th><th className="text-left p-3">Device</th><th className="text-left p-3">Status</th></tr>
        </thead>
        <tbody>
          {rows.map(v => (
            <tr key={v.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-mono">{v.reg_no}</td>
              <td className="p-3">{v.manufacturer} {v.model} <span className="text-zinc-500">({v.year})</span></td>
              <td className="p-3 text-zinc-400">{v.driver?.full_name || "—"}</td>
              <td className="p-3">{v.operating_area}</td>
              <td className="p-3 font-mono text-xs">{v.device?.device_code || <span className="text-zinc-600">unassigned</span>}</td>
              <td className="p-3"><span className={`px-2 py-1 rounded text-xs ${v.status==="Approved"?"bg-green-500/20 text-green-400":"bg-yellow-500/20 text-yellow-400"}`}>{v.status}</span></td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={6} className="p-12 text-center text-zinc-500">No vehicles yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
