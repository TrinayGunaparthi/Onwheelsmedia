import { useState } from "react";
import { Link } from "react-router-dom";
import api, { formatError } from "@/lib/api";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setDone(true);
    } catch (err) { toast.error(formatError(err.response?.data?.detail) || err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-zinc-950">
      <div className="hidden md:flex items-center justify-center bg-grid p-12 border-r border-zinc-800">
        <div>
          <div className="font-display text-6xl font-bold tracking-tighter">Forgot<br /><span className="text-yellow-400">password?</span></div>
          <p className="text-zinc-500 mt-4 max-w-sm">We'll send you a one-time reset link — valid for 1 hour.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        {done ? (
          <div className="w-full max-w-sm text-center space-y-4" data-testid="forgot-done">
            <div className="font-display text-2xl font-bold">Check your inbox</div>
            <p className="text-zinc-500 text-sm">If that email is registered, a reset link has been sent. Links expire in 1 hour and can be used once.</p>
            <Link to="/login" className="inline-block text-yellow-400 hover:text-yellow-300">← Back to sign in</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="w-full max-w-sm space-y-5">
            <Link to="/login" className="text-xs text-zinc-500 hover:text-white uppercase tracking-widest">← Back to sign in</Link>
            <h2 className="font-display text-3xl font-bold">Reset password</h2>
            <div>
              <label className="text-xs uppercase tracking-widest text-zinc-500">Email</label>
              <input data-testid="forgot-email" required type="email" value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
            </div>
            <button data-testid="forgot-submit" disabled={loading} className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-50 text-zinc-950 font-semibold py-3 rounded">{loading?"Sending…":"Send reset link →"}</button>
          </form>
        )}
      </div>
    </div>
  );
}
