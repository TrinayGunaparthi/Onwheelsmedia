import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { LogOut, Radio } from "lucide-react";

export default function Shell({ nav, children, title }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  return (
    <div className="min-h-screen flex bg-zinc-950 text-white">
      <aside className="w-64 shrink-0 border-r border-zinc-800 flex flex-col">
        <div className="p-5 border-b border-zinc-800 flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-yellow-400 grid place-items-center"><Radio className="w-3.5 h-3.5 text-zinc-950" /></div>
          <div className="font-display font-bold">On Wheels</div>
        </div>
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {nav.map(n => (
            <NavLink data-testid={`nav-${n.key}`} key={n.to} to={n.to} end className={({isActive})=>`flex items-center gap-3 px-3 py-2 rounded text-sm ${isActive ? "bg-yellow-400/10 text-yellow-400 border-l-2 border-yellow-400" : "text-zinc-400 hover:text-white hover:bg-zinc-900"}`}>
              <n.icon className="w-4 h-4" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-zinc-800">
          <div className="text-xs text-zinc-500 mb-2">{user?.email}</div>
          <button data-testid="logout-btn" onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-900 rounded">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-hidden flex flex-col">
        <header className="border-b border-zinc-800 px-8 py-4 flex items-center justify-between sticky top-0 bg-zinc-950/80 backdrop-blur z-10">
          <h1 className="font-display text-xl font-semibold">{title || "Dashboard"}</h1>
          <Link to="/" className="text-xs text-zinc-500 hover:text-white uppercase tracking-widest">Home</Link>
        </header>
        <div className="flex-1 overflow-y-auto p-8">{children}</div>
      </main>
    </div>
  );
}
