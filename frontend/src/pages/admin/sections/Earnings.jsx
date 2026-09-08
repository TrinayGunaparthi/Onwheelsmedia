import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function Earnings() {
  const [data, setData] = useState({ drivers: [] });
  const load = () => api.get("/admin/earnings").then(r => setData(r.data));
  useEffect(load, []);
  const payout = async (driver_id, amount) => {
    const amt = parseFloat(prompt(`Payout amount ($) for driver ${driver_id.slice(0,6)}…`, amount)) || 0;
    if (!amt) return;
    try { await api.post("/admin/earnings/payout", { driver_id, amount: amt, note: "Manual payout" }); toast.success("Payout recorded"); load(); }
    catch { toast.error("Payout failed"); }
  };
  return (
    <div data-testid="admin-earnings" className="space-y-4">
      <div className="text-xs text-zinc-500 uppercase tracking-widest">Daily rate: <span className="text-yellow-400 font-mono">${data.per_day_rate || 0}</span> per active device</div>
      <div className="border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
            <tr><th className="text-left p-3">Driver</th><th className="text-left p-3">Device</th><th className="text-left p-3">Days</th><th className="text-right p-3">Earned</th><th className="text-right p-3">Paid</th><th className="text-right p-3">Pending</th><th></th></tr>
          </thead>
          <tbody>
            {(data.drivers || []).map(d => (
              <tr key={d.driver_id + d.device_code} className="border-t border-zinc-800 hover:bg-zinc-900">
                <td className="p-3"><div className="font-medium">{d.driver_name}</div><div className="text-xs text-zinc-500">{d.email}</div></td>
                <td className="p-3 font-mono text-xs">{d.device_code}</td>
                <td className="p-3">{d.active_days}</td>
                <td className="p-3 text-right text-yellow-400 font-medium">${d.earnings_total}</td>
                <td className="p-3 text-right text-green-400">${d.paid}</td>
                <td className="p-3 text-right text-orange-400">${d.pending}</td>
                <td className="p-3 text-right">
                  <button data-testid={`payout-${d.driver_id}`} onClick={()=>payout(d.driver_id, d.pending)} className="text-xs px-3 py-1 bg-yellow-400 text-zinc-950 rounded font-medium">Payout</button>
                </td>
              </tr>
            ))}
            {(data.drivers || []).length===0 && <tr><td colSpan={7} className="p-12 text-center text-zinc-500">No active drivers yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
