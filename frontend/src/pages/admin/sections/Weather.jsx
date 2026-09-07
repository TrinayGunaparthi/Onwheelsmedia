import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function WeatherPage() {
  const [rows, setRows] = useState([]);
  const [location, setLocation] = useState("");
  const load = () => api.get("/admin/weather").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    if (!location) return;
    try { await api.post("/admin/weather", { location, device_ids: [], frequency: 4, duration_seconds: 8 }); toast.success("Added"); setLocation(""); load(); }
    catch { toast.error("Failed"); }
  };
  return (
    <div data-testid="admin-weather" className="space-y-4">
      <div className="flex gap-2">
        <input data-testid="weather-location" value={location} onChange={e=>setLocation(e.target.value)} placeholder="City name (e.g. Bangalore, IN)" className="flex-1 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
        <button data-testid="weather-add" onClick={create} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-4 py-2 text-sm rounded font-medium">Add</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(w => (
          <div key={w.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div className="font-medium">{w.location}</div>
            <div className="text-xs text-zinc-500">{w.device_ids?.length ? `${w.device_ids.length} devices` : "All devices"} · every {w.frequency}/hr · {w.duration_seconds}s</div>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">Add a city — weather shows on player between ads.</div>}
      </div>
    </div>
  );
}
