import { useState } from "react";

export function QuizScreen({ game, session, onFinish }) {
  const [score, setScore] = useState(0);
  const [step, setStep] = useState(0);
  const [choice, setChoice] = useState(null);
  const questions = game.config?.questions || [];
  const q = questions[step];
  if (!q) { onFinish(score); return <div className="min-h-screen bg-zinc-950 text-white grid place-items-center">Wrapping up…</div>; }
  const submit = () => {
    const isCorrect = choice === q.correct;
    const newScore = score + (isCorrect ? 10 : 0);
    setScore(newScore); setChoice(null);
    if (step + 1 >= questions.length) onFinish(newScore, { total: questions.length });
    else setStep(step + 1);
  };
  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-500 to-orange-600 text-zinc-950 p-6 flex flex-col" data-testid="game-quiz">
      <div className="flex justify-between text-sm font-mono"><span>Q {step + 1} / {questions.length}</span><span>Score: {score}</span></div>
      <div className="flex-1 flex flex-col justify-center max-w-lg mx-auto w-full">
        <div className="font-display text-3xl font-bold mb-6">{q.question}</div>
        <div className="grid gap-3">
          {(q.options || []).map((opt, i) => (
            <button key={`${step}-${i}`} data-testid={`opt-${i}`} onClick={() => setChoice(i)} className={`text-left px-4 py-4 rounded border-2 font-medium transition-colors ${choice === i ? "bg-zinc-950 text-yellow-400 border-zinc-950" : "bg-white/70 border-white/70 hover:bg-white"}`}>{opt}</button>
          ))}
        </div>
        <button data-testid="quiz-submit" disabled={choice === null} onClick={submit} className="mt-6 bg-zinc-950 text-yellow-400 disabled:opacity-40 py-4 rounded font-semibold">{step + 1 >= questions.length ? "Finish" : "Next →"}</button>
      </div>
    </div>
  );
}

export function SpinScreen({ game, onFinish }) {
  const segments = game.config?.segments || [{ label: "10% OFF" }, { label: "Try again" }, { label: "Free coffee" }, { label: "Better luck" }];
  const spin = () => {
    const idx = Math.floor(Math.random() * segments.length);
    onFinish(idx === 0 ? 100 : 20, { won: segments[idx].label });
  };
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-700 to-pink-600 text-white p-6 grid place-items-center" data-testid="game-spin">
      <div className="text-center">
        <div className="font-display text-4xl font-bold mb-6">Spin & Win</div>
        <button data-testid="spin-btn" onClick={spin} className="bg-yellow-400 text-zinc-950 font-bold px-8 py-6 rounded-full text-2xl hover:bg-yellow-300">SPIN 🎰</button>
        <div className="mt-6 text-sm opacity-70">{segments.map((s) => s.label).join(" · ")}</div>
      </div>
    </div>
  );
}

export function DoneScreen({ score }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-600 to-emerald-800 text-white grid place-items-center p-6" data-testid="game-done">
      <div className="text-center">
        <div className="text-8xl mb-4">🎉</div>
        <div className="font-display text-4xl font-bold">Thanks for playing!</div>
        <div className="text-xl mt-2 opacity-90">Score: {score}</div>
        <div className="mt-8 text-sm opacity-70">Enjoy the ride with On Wheels Media.</div>
      </div>
    </div>
  );
}
