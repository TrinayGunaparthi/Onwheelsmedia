import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

const DEFAULT_QUIZ = {
  questions: [
    { question: "What powers On Wheels Media screens?", options: ["Diesel","Solar","Cloud","Steam"], correct: 2 },
    { question: "How many autos in the network?", options: ["10","500+","2","0"], correct: 1 },
  ]
};
const DEFAULT_SPIN = { segments: [{label:"10% OFF"},{label:"Free Coffee"},{label:"Try Again"},{label:"20% OFF"}] };

export default function Games() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ name: "", game_type: "quiz", config_text: JSON.stringify(DEFAULT_QUIZ, null, 2) });
  const load = () => api.get("/admin/games").then(r => setRows(r.data));
  useEffect(load, []);
  const create = async () => {
    try {
      const config = JSON.parse(form.config_text || "{}");
      await api.post("/admin/games", { name: form.name, game_type: form.game_type, config, active: true });
      toast.success("Game created");
      setForm({ name: "", game_type: "quiz", config_text: JSON.stringify(DEFAULT_QUIZ, null, 2) });
      load();
    } catch (e) { toast.error("Invalid JSON or create failed"); }
  };
  const remove = async (id) => { await api.delete(`/admin/games/${id}`); load(); };
  const switchType = (t) => {
    setForm({ ...form, game_type: t, config_text: JSON.stringify(t==="quiz"?DEFAULT_QUIZ:DEFAULT_SPIN, null, 2) });
  };
  return (
    <div data-testid="admin-games" className="space-y-6">
      <div className="border border-zinc-800 p-4 grid gap-3">
        <div className="grid md:grid-cols-2 gap-3">
          <input data-testid="game-name" placeholder="Game name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <select data-testid="game-type" value={form.game_type} onChange={e=>switchType(e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
            <option value="quiz">Quiz</option>
            <option value="spin">Spin wheel</option>
            <option value="memory">Memory</option>
            <option value="reaction">Reaction</option>
            <option value="brand">Brand game</option>
          </select>
        </div>
        <div>
          <label className="text-xs uppercase tracking-widest text-zinc-500 mb-2 block">Config (JSON)</label>
          <textarea data-testid="game-config" value={form.config_text} onChange={e=>setForm({...form, config_text:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 font-mono text-xs p-3 rounded h-56" />
        </div>
        <button data-testid="game-create" onClick={create} disabled={!form.name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded font-medium text-sm">Create game</button>
      </div>
      <div className="border border-zinc-800">
        {rows.map(g => (
          <div key={g.id} className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
            <div>
              <div className="font-medium">{g.name} <span className="text-xs text-zinc-500 ml-2 uppercase">{g.game_type}</span></div>
              <div className="text-xs text-zinc-500 mt-1">Plays: {g.plays || 0} · Completions: {g.completions || 0}</div>
              <div className="text-xs text-yellow-400 mt-1 font-mono">ID: {g.id}</div>
            </div>
            <button data-testid={`game-delete-${g.id}`} onClick={()=>remove(g.id)} className="text-xs text-red-400 hover:text-red-300 h-fit">Delete</button>
          </div>
        ))}
        {rows.length===0 && <div className="p-12 text-center text-zinc-500">No games yet. Create a quiz above.</div>}
      </div>
    </div>
  );
}
