import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
import { Download } from "lucide-react";
export default function Reports() {
  const [plays, setPlays] = useState([]);
  useEffect(() => { api.get("/admin/reports/plays?days=14").then(r=>setPlays(r.data)); }, []);
  const exportUrl = (kind, fmt) => {
    const token = localStorage.getItem("owm_token");
    const url = `${API}/admin/reports/export?kind=${kind}&fmt=${fmt}&days=30`;
    // Use fetch + blob to include Authorization header
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement("a"); const u = URL.createObjectURL(blob);
        a.href = u; a.download = `${kind}_30d.${fmt}`; a.click(); URL.revokeObjectURL(u);
      });
  };
  const kinds = [
    { k: "campaigns", label: "Campaigns" },
    { k: "devices", label: "Devices" },
    { k: "audience", label: "Audience" },
    { k: "engagement", label: "Engagement" },
  ];
  return (
    <div data-testid="admin-reports" className="space-y-6">
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Export reports</div>
        <div className="grid md:grid-cols-2 gap-3">
          {kinds.map(({k, label}) => (
            <div key={k} className="flex items-center justify-between border border-zinc-800 p-3 rounded">
              <div className="font-medium">{label}</div>
              <div className="flex gap-2">
                <button data-testid={`export-${k}-csv`} onClick={()=>exportUrl(k,"csv")} className="flex items-center gap-1 text-xs px-3 py-1.5 border border-zinc-700 hover:border-yellow-400 rounded"><Download className="w-3 h-3"/>CSV</button>
                <button data-testid={`export-${k}-pdf`} onClick={()=>exportUrl(k,"pdf")} className="flex items-center gap-1 text-xs px-3 py-1.5 border border-zinc-700 hover:border-yellow-400 rounded"><Download className="w-3 h-3"/>PDF</button>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Total Plays — last 14 days</div>
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={plays}>
              <CartesianGrid stroke="#27272a" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" stroke="#71717a" tick={{ fontSize: 11 }} />
              <YAxis stroke="#71717a" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a" }} />
              <Bar dataKey="plays" fill="#facc15" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
