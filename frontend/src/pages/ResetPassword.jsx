import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import api, { formatError } from "@/lib/api";
import { toast } from "sonner";

export default function ResetPassword() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const token = sp.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) return toast.error("Password must be at least 6 chars");
    if (password !== confirm) return toast.error("Passwords do not match");
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      toast.success("Password updated — please sign in");
      nav("/login");
    } catch (err) { toast.error(formatError(err.response?.data?.detail) || err.message); }
    finally { setLoading(false); }
  };
  if (!token) return (
    <div className="min-h-screen grid place-items-center bg-zinc-950 text-center p-6" data-testid="reset-invalid">
      <div>
        <div className="text-2xl font-display font-bold text-red-400">Invalid reset link</div>
        <p className="text-zinc-500 mt-2">Request a new one from the sign in page.</p>
        <Link to="/forgot-password" className="text-yellow-400 hover:text-yellow-300 mt-4 inline-block">Request new link →</Link>
      </div>
    </div>
  );
  return (
    <div className="min-h-screen grid place-items-center bg-zinc-950 p-6">
      <form onSubmit={submit} className="w-full max-w-sm space-y-5" data-testid="reset-form">
        <Link to="/login" className="text-xs text-zinc-500 hover:text-white uppercase tracking-widest">← Back to sign in</Link>
        <h2 className="font-display text-3xl font-bold">Choose a new password</h2>
        <input data-testid="reset-pw" required type="password" placeholder="New password (min 6)" minLength={6} value={password} onChange={e=>setPassword(e.target.value)} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
        <input data-testid="reset-confirm" required type="password" placeholder="Confirm password" minLength={6} value={confirm} onChange={e=>setConfirm(e.target.value)} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
        <button data-testid="reset-submit" disabled={loading} className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-50 text-zinc-950 font-semibold py-3 rounded">{loading?"Updating…":"Update password →"}</button>
      </form>
    </div>
  );
}
