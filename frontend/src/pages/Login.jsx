import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { formatError } from "@/lib/api";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await login(email, password);
      toast.success(`Welcome, ${u.name || u.email}`);
      nav(u.role === "admin" ? "/admin" : u.role === "advertiser" ? "/advertiser" : "/driver");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-zinc-950">
      <div className="hidden md:flex items-center justify-center bg-grid p-12 border-r border-zinc-800">
        <div>
          <div className="font-display text-6xl font-bold tracking-tighter">Welcome<br /><span className="text-yellow-400">back.</span></div>
          <p className="text-zinc-500 mt-4 max-w-sm">Sign in to manage your fleet, campaigns, and playback reports.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-5">
          <Link to="/" className="text-xs text-zinc-500 hover:text-white uppercase tracking-widest">← Back home</Link>
          <h2 className="font-display text-3xl font-bold">Sign in</h2>
          <div>
            <label className="text-xs uppercase tracking-widest text-zinc-500">Email</label>
            <input data-testid="login-email" required value={email} onChange={e=>setEmail(e.target.value)} type="email" className="mt-2 w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-zinc-500">Password</label>
            <input data-testid="login-password" required value={password} onChange={e=>setPassword(e.target.value)} type="password" className="mt-2 w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          </div>
          <button data-testid="login-submit" disabled={loading} type="submit" className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-50 text-zinc-950 font-semibold py-3 rounded">
            {loading ? "Signing in…" : "Sign in →"}
          </button>
          <p className="text-sm text-zinc-500 text-center">No account? <Link to="/register" className="text-yellow-400 hover:text-yellow-300">Create one</Link></p>
        </form>
      </div>
    </div>
  );
}
