import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { QuizScreen, SpinScreen, DoneScreen } from "@/pages/game/GameScreens";

export default function GamePlayer() {
  const [sp] = useSearchParams();
  const gameId = sp.get("game_id");
  const campaignId = sp.get("campaign_id");
  const deviceId = sp.get("device_id");
  const [state, setState] = useState({ phase: "loading" });
  const [session, setSession] = useState(null);
  const [game, setGame] = useState(null);
  const [finalScore, setFinalScore] = useState(0);

  useEffect(() => {
    if (!gameId) { setState({ phase: "error", msg: "Missing game id" }); return; }
    api.post("/games/session", { game_id: gameId, campaign_id: campaignId, device_id: deviceId })
      .then((r) => { setSession(r.data); setGame(r.data.game); setState({ phase: "playing" }); })
      .catch((e) => setState({ phase: "error", msg: e.response?.data?.detail || "Failed to start" }));
  }, [gameId, campaignId, deviceId]);

  const finish = async (score, result = {}) => {
    setFinalScore(score);
    setState({ phase: "done" });
    try { await api.post("/games/complete", { session_id: session.session_id, score, result }); }
    catch (e) { console.warn("[game] completion save failed:", e?.message || e); }
  };

  if (state.phase === "loading") return <div className="min-h-screen bg-zinc-950 text-white grid place-items-center">Loading…</div>;
  if (state.phase === "error") return <div className="min-h-screen bg-zinc-950 text-red-400 grid place-items-center p-6 text-center">{state.msg}</div>;
  if (state.phase === "playing" && game?.game_type === "quiz") return <QuizScreen game={game} session={session} onFinish={finish} />;
  if (state.phase === "playing" && game?.game_type === "spin") return <SpinScreen game={game} onFinish={finish} />;
  return <DoneScreen score={finalScore} />;
}
