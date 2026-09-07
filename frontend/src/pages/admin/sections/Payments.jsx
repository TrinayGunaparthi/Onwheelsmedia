import { useEffect, useState } from "react";
import api from "@/lib/api";
export default function Payments() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/payments/invoices").then(r=>setRows(r.data)); }, []);
  return (
    <div data-testid="admin-payments" className="border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs uppercase tracking-widest text-zinc-500">
          <tr><th className="text-left p-3">Invoice</th><th className="text-left p-3">Amount</th><th className="text-left p-3">Status</th><th className="text-left p-3">Date</th></tr>
        </thead>
        <tbody>
          {rows.map(i => (
            <tr key={i.id} className="border-t border-zinc-800 hover:bg-zinc-900">
              <td className="p-3 font-mono text-xs">{i.id}</td>
              <td className="p-3 font-medium">₹{i.amount}</td>
              <td className="p-3"><span className="px-2 py-1 rounded text-xs bg-yellow-500/20 text-yellow-400">{i.status}</span></td>
              <td className="p-3 text-xs text-zinc-500">{i.created_at?.slice(0,10)}</td>
            </tr>
          ))}
          {rows.length===0 && <tr><td colSpan={4} className="p-12 text-center text-zinc-500">No invoices yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
