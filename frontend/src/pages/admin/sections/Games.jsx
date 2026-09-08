import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { QuizBuilder, SpinBuilder, GameRow } from "@/pages/admin/sections/games/GameBuilders";

export default function Games() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("quiz");
  const [questions, setQuestions] = useState([{ question: "", options: ["", "", "", ""], correct: 0 }]);
  const [segments, setSegments] = useState([{ label: "10% OFF" }, { label: "Try Again" }, { label: "Free Coffee" }, { label: "Better Luck" }]);
  const load = () => api.get("/admin/games").then((r) => setRows(r.data)).catch((e) => console.warn("games load failed", e));
  useEffect(() => { load(); }, []);
  const create = async () => {
    const config = type === "quiz" ? { questions } : { segments };
    try { await api.post("/admin/games", { name, game_type: type, config, active: true }); toast.success("Game created"); setName(""); load(); }
    catch (e) { toast.error("Failed"); console.warn("game create", e); }
  };
  const remove = async (id) => { await api.delete(`/admin/games/${id}`); load(); };

  return (
    <div data-testid="admin-games" className="space-y-6">
      <div className="border border-zinc-800 p-6 space-y-4">
        <div className="text-xs uppercase tracking-widest text-yellow-400">Game Studio · Visual builder</div>
        <div className="grid md:grid-cols-2 gap-3">
          <input data-testid="game-name" placeholder="Game name" value={name} onChange={(e) => setName(e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          <select data-testid="game-type" value={type} onChange={(e) => setType(e.target.value)} className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded">
            <option value="quiz">Quiz</option>
            <option value="spin">Spin wheel</option>
          </select>
        </div>
        {type === "quiz" && <QuizBuilder questions={questions} setQuestions={setQuestions} />}
        {type === "spin" && <SpinBuilder segments={segments} setSegments={setSegments} />}
        <button data-testid="game-create" onClick={create} disabled={!name} className="bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded font-medium text-sm">Save game</button>
      </div>

      <div className="border border-zinc-800">
        {rows.map((g) => <GameRow key={g.id} g={g} onDelete={remove} />)}
        {rows.length === 0 && <div className="p-12 text-center text-zinc-500">No games yet. Create one above.</div>}
      </div>
    </div>
  );
}
