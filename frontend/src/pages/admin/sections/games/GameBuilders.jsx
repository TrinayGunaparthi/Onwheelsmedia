import { Plus, Trash2 } from "lucide-react";

export function QuizBuilder({ questions, setQuestions }) {
  const updateQ = (i, field, val) => setQuestions((qs) => qs.map((q, idx) => (idx === i ? { ...q, [field]: val } : q)));
  const updateOpt = (qi, oi, val) => setQuestions((qs) => qs.map((q, idx) => (idx === qi ? { ...q, options: q.options.map((o, j) => (j === oi ? val : o)) } : q)));
  const addQ = () => setQuestions((qs) => [...qs, { question: "", options: ["", "", "", ""], correct: 0 }]);
  const rmQ = (i) => setQuestions((qs) => qs.filter((_, idx) => idx !== i));
  return (
    <div className="space-y-4">
      {questions.map((q, i) => (
        <div key={i} className="border border-zinc-800 p-4 space-y-2">
          <div className="flex gap-2 items-center">
            <span className="text-xs text-zinc-500 font-mono">Q{i + 1}</span>
            <input data-testid={`q-text-${i}`} placeholder="Question" value={q.question} onChange={(e) => updateQ(i, "question", e.target.value)} className="flex-1 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
            {questions.length > 1 && <button onClick={() => rmQ(i)} className="text-red-400 text-xs"><Trash2 className="w-4 h-4" /></button>}
          </div>
          <div className="grid md:grid-cols-2 gap-2">
            {q.options.map((opt, oi) => (
              <label key={oi} className="flex items-center gap-2">
                <input data-testid={`q-correct-${i}-${oi}`} type="radio" name={`correct-${i}`} checked={q.correct === oi} onChange={() => updateQ(i, "correct", oi)} className="accent-yellow-400" />
                <input data-testid={`q-opt-${i}-${oi}`} placeholder={`Option ${oi + 1}`} value={opt} onChange={(e) => updateOpt(i, oi, e.target.value)} className="flex-1 bg-zinc-900 border border-zinc-800 px-2 py-1.5 text-sm rounded" />
              </label>
            ))}
          </div>
        </div>
      ))}
      <button data-testid="add-q" onClick={addQ} className="text-xs flex items-center gap-1 border border-zinc-800 hover:border-yellow-400 px-3 py-2 rounded"><Plus className="w-3 h-3" /> Add question</button>
    </div>
  );
}

export function SpinBuilder({ segments, setSegments }) {
  const addSeg = () => setSegments((s) => [...s, { label: "" }]);
  const rmSeg = (i) => setSegments((s) => s.filter((_, idx) => idx !== i));
  const updSeg = (i, val) => setSegments((s) => s.map((x, idx) => (idx === i ? { label: val } : x)));
  return (
    <div className="space-y-3">
      {segments.map((s, i) => (
        <div key={i} className="flex gap-2">
          <input data-testid={`seg-${i}`} placeholder="Segment label" value={s.label} onChange={(e) => updSeg(i, e.target.value)} className="flex-1 bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm rounded" />
          {segments.length > 2 && <button onClick={() => rmSeg(i)} className="text-red-400 text-xs px-2"><Trash2 className="w-4 h-4" /></button>}
        </div>
      ))}
      <button data-testid="add-seg" onClick={addSeg} className="text-xs flex items-center gap-1 border border-zinc-800 hover:border-yellow-400 px-3 py-2 rounded"><Plus className="w-3 h-3" /> Add segment</button>
    </div>
  );
}

export function GameRow({ g, onDelete }) {
  return (
    <div className="p-4 border-b border-zinc-800 last:border-0 flex justify-between hover:bg-zinc-900">
      <div>
        <div className="font-medium">{g.name} <span className="text-xs text-zinc-500 uppercase ml-2">{g.game_type}</span></div>
        <div className="text-xs text-zinc-500 mt-1">Plays: {g.plays || 0} · Completions: {g.completions || 0}</div>
        <div className="text-xs text-yellow-400 mt-1 font-mono">ID: {g.id}</div>
      </div>
      <button data-testid={`game-delete-${g.id}`} onClick={() => onDelete(g.id)} className="text-xs text-red-400 h-fit">Delete</button>
    </div>
  );
}
