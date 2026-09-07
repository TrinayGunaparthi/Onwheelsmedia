import { useEffect, useState } from "react";
import api from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, BarChart, Bar, CartesianGrid, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#facc15", "#06b6d4", "#22c55e", "#f97316", "#a855f7", "#ec4899"];

export default function Audience() {
  const [hours, setHours] = useState(24);
  const [data, setData] = useState({});
  useEffect(() => { api.get(`/admin/audience?hours=${hours}`).then(r => setData(r.data)); }, [hours]);
  const ageData = Object.entries(data.age_distribution || {}).map(([k, v]) => ({ name: k, value: v }));
  const genderData = Object.entries(data.gender_distribution || {}).map(([k, v]) => ({ name: k, value: v }));
  return (
    <div data-testid="admin-audience" className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="text-xs text-zinc-500 uppercase tracking-widest">Privacy-first · Anonymous aggregates only</div>
        <select data-testid="audience-range" value={hours} onChange={e=>setHours(parseInt(e.target.value))} className="bg-zinc-900 border border-zinc-800 px-3 py-1 text-sm rounded">
          <option value={1}>Last hour</option>
          <option value={24}>Last 24 hours</option>
          <option value={168}>Last 7 days</option>
        </select>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-zinc-800">
        {[
          { l: "Samples", v: data.samples_count ?? 0 },
          { l: "Est. Viewers", v: data.estimated_viewers ?? 0 },
          { l: "Avg Attention", v: `${data.avg_attention ?? 0}/100`, tint: data.avg_attention > 70 ? "text-green-400" : data.avg_attention > 30 ? "text-yellow-400" : "text-red-400" },
          { l: "Peak Hour", v: (data.by_hour || []).slice(-1)[0]?.hour?.slice(11) || "—" },
        ].map((c, i) => (
          <div key={i} className="bg-zinc-950 p-5">
            <div className="text-xs uppercase tracking-widest text-zinc-500">{c.l}</div>
            <div className={`font-display text-3xl font-bold mt-2 ${c.tint || "text-white"}`}>{c.v}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Age distribution (estimated)</div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={ageData}>
                <CartesianGrid stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="#71717a" tick={{fontSize:11}} />
                <YAxis stroke="#71717a" tick={{fontSize:11}} />
                <Tooltip contentStyle={{background:"#18181b",border:"1px solid #27272a"}} />
                <Bar dataKey="value" fill="#facc15" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="border border-zinc-800 p-6">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Gender distribution (estimated)</div>
          <div className="h-56">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={genderData} dataKey="value" cx="50%" cy="50%" outerRadius={80} label>
                  {genderData.map((_, i) => <Cell key={i} fill={COLORS[i%COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{background:"#18181b",border:"1px solid #27272a"}} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">Viewers & attention over time</div>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={data.by_hour || []}>
              <XAxis dataKey="hour" stroke="#71717a" tick={{fontSize:10}} tickFormatter={h => h?.slice(11,16)} />
              <YAxis stroke="#71717a" tick={{fontSize:11}} />
              <Tooltip contentStyle={{background:"#18181b",border:"1px solid #27272a"}} />
              <Line type="monotone" dataKey="viewers" stroke="#facc15" strokeWidth={2} name="Viewers" />
              <Line type="monotone" dataKey="avg_attention" stroke="#06b6d4" strokeWidth={2} name="Attention" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
