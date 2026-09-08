import { useEffect, useRef, useState, useCallback } from "react";
import api, { BACKEND_URL } from "@/lib/api";
import { simulate, topKey } from "@/lib/audience";
import { detectSample } from "@/lib/realCamera";

const HEARTBEAT_MS = 30000;
const SYNC_MS = 60000;
const AUDIENCE_MS = 30000;

export default function KioskPlayer() {
  const [phase, setPhase] = useState("activate"); // activate | ready
  const [code, setCode] = useState(localStorage.getItem("owm_device_code") || "");
  const [deviceToken, setDeviceToken] = useState(localStorage.getItem("owm_device_token") || "");
  const [deviceCode, setDeviceCode] = useState(localStorage.getItem("owm_device_id_code") || "");
  const [playlist, setPlaylist] = useState([]);
  const [idx, setIdx] = useState(0);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(navigator.onLine);
  const [audience, setAudience] = useState(null);
  const [privacy, setPrivacy] = useState({ camera_enabled: true, show_camera_notice: true });
  const eventBuffer = useRef([]);
  const audienceRef = useRef(null);

  useEffect(() => {
    if (deviceToken) setPhase("ready");
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, [deviceToken]);

  const authHeaders = useCallback(() => ({ Authorization: `Bearer ${deviceToken}` }), [deviceToken]);

  const doActivate = async () => {
    setError("");
    try {
      const { data } = await api.post("/player/activate", { activation_code: code.trim().toUpperCase() });
      if (!data.approved) { setError(`Device status: ${data.status}. Awaiting admin approval.`); return; }
      localStorage.setItem("owm_device_token", data.device_token);
      localStorage.setItem("owm_device_id_code", data.device_code);
      localStorage.setItem("owm_device_code", code);
      setDeviceToken(data.device_token); setDeviceCode(data.device_code); setPhase("ready");
    } catch (e) { setError(e.response?.data?.detail || "Invalid activation code"); }
  };

  // Sync playlist — include audience context for AI dynamic ad selection
  const syncPlaylist = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      const a = audienceRef.current;
      if (a) {
        params.set("age_group", topKey(a.age_distribution));
        params.set("gender", topKey(a.gender_distribution));
        params.set("attention", String(a.attention_score));
        params.set("viewers", String(a.viewers));
      }
      const { data } = await api.get(`/player/playlist?${params.toString()}`, { headers: authHeaders() });
      if (data.items?.length) {
        setPlaylist(data.items);
        localStorage.setItem("owm_playlist_cache", JSON.stringify(data.items));
      }
    } catch (e) { console.warn("[player] playlist sync failed:", e?.message || e); }
  }, [authHeaders]);

  // Load cache on start
  useEffect(() => {
    if (phase !== "ready") return;
    const cached = localStorage.getItem("owm_playlist_cache");
    if (cached) { try { setPlaylist(JSON.parse(cached)); } catch (e) { console.warn("[player] cache parse failed:", e); } }
    syncPlaylist();
    const t = setInterval(syncPlaylist, SYNC_MS);
    return () => clearInterval(t);
  }, [phase, syncPlaylist]);

  // Heartbeat + event flush
  useEffect(() => {
    if (phase !== "ready") return;
    const send = async () => {
      try {
        await api.post("/player/heartbeat", { device_id: deviceCode, app_version: "web-1.0", network: online ? "online" : "offline" }, { headers: authHeaders() });
        // flush buffered events
        if (eventBuffer.current.length) {
          const batch = eventBuffer.current.splice(0);
          try { await api.post("/player/playback/batch", batch, { headers: authHeaders() }); }
          catch (e) { console.warn("[player] batch flush failed, retrying:", e?.message || e); eventBuffer.current.unshift(...batch); }
        }
      } catch (e) { console.warn("[player] heartbeat failed:", e?.message || e); }
    };
    send();
    const t = setInterval(send, HEARTBEAT_MS);
    return () => clearInterval(t);
  }, [phase, deviceCode, online, authHeaders]);

  // Fetch privacy config once (respects admin toggles)
  useEffect(() => {
    if (phase !== "ready") return;
    api.get("/player/privacy", { headers: authHeaders() }).then(r => setPrivacy(r.data)).catch((e) => console.warn("[player] privacy fetch failed:", e?.message || e));
  }, [phase, authHeaders]);

  // Audience sampler (privacy-first): tries real camera via face-api.js, falls back to simulator
  useEffect(() => {
    if (phase !== "ready") return;
    if (privacy.camera_enabled === false) return;
    const tick = async () => {
      let sample;
      try { sample = await detectSample(); } catch (e) { console.warn("[player] detectSample failed, using simulator:", e?.message || e); sample = simulate(); }
      setAudience(sample);
      audienceRef.current = sample;
      try { await api.post("/player/audience", sample, { headers: authHeaders() }); } catch (e) { console.warn("[player] audience upload failed:", e?.message || e); }
    };
    tick();
    const t = setInterval(tick, AUDIENCE_MS);
    return () => clearInterval(t);
  }, [phase, privacy.camera_enabled, authHeaders]);

  const current = playlist[idx];
  const advance = useCallback(() => {
    if (!current) return;
    // record playback
    const evt = {
      device_id: deviceCode,
      ad_id: current.type === "ad" ? current.id : null,
      campaign_id: current.type === "ad" ? current.campaign_id : null,
      news_id: current.type === "news" ? current.id : null,
      completed: true,
      duration_played: current.duration || 10,
      timestamp: new Date().toISOString()
    };
    if (online) {
      api.post("/player/playback", evt, { headers: authHeaders() }).catch(() => eventBuffer.current.push(evt));
    } else {
      eventBuffer.current.push(evt);
    }
    setIdx((i) => (playlist.length ? (i + 1) % playlist.length : 0));
  }, [current, deviceCode, online, playlist.length, authHeaders]);

  useEffect(() => {
    if (!current) return;
    const dur = (current.duration || 10) * 1000;
    const t = setTimeout(advance, dur);
    return () => clearTimeout(t);
  }, [current, advance]);

  if (phase === "activate") {
    return (
      <div className="fixed inset-0 bg-zinc-950 flex items-center justify-center p-6" data-testid="player-activate">
        <div className="w-full max-w-md text-center">
          <div className="font-display text-4xl font-bold text-yellow-400 mb-2">On Wheels Media</div>
          <p className="text-zinc-500 mb-8">Device Player · Kiosk Mode</p>
          <input data-testid="activate-code" autoFocus value={code} onChange={e=>setCode(e.target.value.toUpperCase())} placeholder="ACTIVATION CODE" className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-4 text-2xl font-mono text-center tracking-widest rounded" />
          <button data-testid="activate-submit" onClick={doActivate} className="mt-4 w-full bg-yellow-400 hover:bg-yellow-300 text-zinc-950 font-semibold py-4 rounded">Activate</button>
          {error && <div className="mt-4 text-sm text-red-400">{error}</div>}
        </div>
      </div>
    );
  }

  if (!playlist.length) {
    return <div className="fixed inset-0 bg-zinc-950 grid place-items-center text-zinc-500" data-testid="player-empty">Waiting for content… ({deviceCode})</div>;
  }

  return (
    <div className="fixed inset-0 bg-black overflow-hidden" data-testid="player-play">
      {/* Content */}
      {current?.type === "ad" && current.file_type === "image" && (
        <img src={`${BACKEND_URL}${current.file_url}`} alt="" className="w-full h-full object-cover" />
      )}
      {current?.type === "ad" && current.file_type === "video" && (
        <video src={`${BACKEND_URL}${current.file_url}`} autoPlay muted playsInline className="w-full h-full object-cover" onEnded={advance} />
      )}
      {current?.type === "news" && (
        <div className="w-full h-full bg-gradient-to-br from-zinc-900 to-black flex items-center justify-center p-16">
          <div className="max-w-4xl">
            <div className="text-xs uppercase tracking-[0.3em] text-yellow-400 mb-4">Breaking · {current.location || "News"}</div>
            <div className="font-display text-6xl font-bold leading-tight mb-6 text-white">{current.headline}</div>
            <div className="text-2xl text-zinc-300">{current.description}</div>
          </div>
        </div>
      )}
      {current?.type === "qr" && (
        <div className="w-full h-full bg-white flex flex-col items-center justify-center gap-6 text-black">
          <div className="font-display text-4xl font-bold">Scan for {current.name}</div>
          <img alt="QR" className="w-64 h-64" src={`https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(current.target_url)}`} />
          <div className="text-lg font-mono">{current.target_url}</div>
        </div>
      )}
      {current?.type === "weather" && (
        <div className="w-full h-full bg-gradient-to-br from-cyan-900 to-zinc-950 flex items-center justify-center p-16 text-white">
          <div className="text-center">
            <div className="text-xs uppercase tracking-[0.3em] text-cyan-300 mb-4">Weather · {current.data.location}</div>
            <div className="font-display text-9xl font-bold">{current.data.temp_c}°C</div>
            <div className="text-3xl mt-4">{current.data.condition}</div>
          </div>
        </div>
      )}

      {/* Overlays */}
      <div className="absolute top-4 right-4 bg-black/60 backdrop-blur px-3 py-2 rounded text-xs font-mono flex flex-col items-end gap-1" data-testid="player-overlay">
        <div><span className="text-yellow-400">{deviceCode}</span> · <span className={online?"text-green-400":"text-red-400"}>{online?"ONLINE":"OFFLINE"}</span></div>
        {audience && privacy.camera_enabled !== false && (
          <div className="text-cyan-400" data-testid="audience-indicator">
            👥 {audience.viewers} · ATT {audience.attention_score} · <span className="text-zinc-400">{audience.source === "face_api" ? "camera" : "AI sim"}</span>
          </div>
        )}
      </div>
      {/* Interactive game QR overlay when ad has interactive.type==="game" */}
      {current?.type === "ad" && current.interactive?.type === "game" && (
        <div className="absolute top-4 left-4 bg-white text-black p-3 rounded flex items-center gap-3" data-testid="game-qr-overlay">
          <img alt="Play" className="w-24 h-24" src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(`${window.location.origin}/play?game_id=${current.interactive.game_id}&campaign_id=${current.campaign_id}&device_id=${deviceCode}`)}`} />
          <div>
            <div className="font-display font-bold text-lg">Scan to play</div>
            <div className="text-xs">Win rewards!</div>
          </div>
        </div>
      )}
      {/* Privacy camera-use notice */}
      {privacy.show_camera_notice !== false && privacy.camera_enabled !== false && (
        <div className="absolute top-1/2 -translate-y-1/2 left-4 bg-black/80 border border-yellow-400/40 text-yellow-300 text-[10px] px-2 py-1 rounded font-mono" data-testid="camera-notice">
          Anonymous audience analytics active · no faces stored
        </div>
      )}
      <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur border-t border-yellow-400/30 py-2 overflow-hidden">
        <div className="marquee text-yellow-400 font-mono text-sm">
          ON WHEELS MEDIA · {playlist.filter(p=>p.type==="news").map(n=>n.headline).join(" · ") || "Ride safe. Stay tuned."}
        </div>
      </div>
    </div>
  );
}
