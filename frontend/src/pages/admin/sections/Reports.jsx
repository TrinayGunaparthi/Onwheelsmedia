import { useEffect, useState } from "react";
import api from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
export default function Reports() {
  const [plays, setPlays] = useState([]);
  useEffect(() => { api.get("/admin/reports/plays?days=14").then(r=>setPlays(r.data)); }, []);
  return (
    <div data-testid="admin-reports" className="border border-zinc-800 p-6">
      <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Total Plays — last 14 days</div>
      <div className="h-80">
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
  );
}
