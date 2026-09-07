import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { formatError } from "@/lib/api";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [role, setRole] = useState(sp.get("role") || "advertiser");
  const [form, setForm] = useState({ email: "", password: "", name: "", phone: "", company: "" });
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await register({ ...form, role });
      toast.success("Account created");
      nav(u.role === "advertiser" ? "/advertiser" : "/driver");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-zinc-950">
      <div className="hidden md:flex items-center justify-center bg-grid p-12 border-r border-zinc-800">
        <div>
          <div className="font-display text-6xl font-bold tracking-tighter">Join the<br /><span className="text-yellow-400">network.</span></div>
          <p className="text-zinc-500 mt-4 max-w-sm">Whether you drive an auto or run campaigns — get started in minutes.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4">
          <Link to="/" className="text-xs text-zinc-500 hover:text-white uppercase tracking-widest">← Back home</Link>
          <h2 className="font-display text-3xl font-bold">Create account</h2>

          <div className="grid grid-cols-2 gap-2">
            {["advertiser", "driver"].map(r => (
              <button data-testid={`role-${r}`} type="button" key={r} onClick={()=>setRole(r)} className={`px-4 py-2 rounded border text-sm font-medium ${role===r?"bg-yellow-400 text-zinc-950 border-yellow-400":"border-zinc-800 text-zinc-300 hover:border-zinc-600"}`}>
                {r === "advertiser" ? "I'm an Advertiser" : "I'm a Driver"}
              </button>
            ))}
          </div>

          <input data-testid="reg-name" required placeholder="Full name" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          <input data-testid="reg-email" required type="email" placeholder="Email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          <input data-testid="reg-phone" placeholder="Phone" value={form.phone} onChange={e=>setForm({...form, phone:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          {role === "advertiser" && (
            <input data-testid="reg-company" placeholder="Company name" value={form.company} onChange={e=>setForm({...form, company:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />
          )}
          <input data-testid="reg-password" required type="password" placeholder="Password (min 6)" minLength={6} value={form.password} onChange={e=>setForm({...form, password:e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 focus:border-yellow-400 outline-none px-4 py-3 text-sm rounded" />

          <button data-testid="reg-submit" disabled={loading} className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-50 text-zinc-950 font-semibold py-3 rounded">
            {loading ? "Creating…" : "Create account →"}
          </button>
          <p className="text-sm text-zinc-500 text-center">Have an account? <Link to="/login" className="text-yellow-400 hover:text-yellow-300">Sign in</Link></p>
        </form>
      </div>
    </div>
  );
}
