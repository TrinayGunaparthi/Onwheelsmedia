import { useEffect, useState, useCallback } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import api, { API } from "@/lib/api";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

async function downloadInvoice(sessionId) {
  const token = localStorage.getItem("owm_token");
  const r = await fetch(`${API}/invoices/${sessionId}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) return;
  const blob = await r.blob();
  const a = document.createElement("a"); const u = URL.createObjectURL(blob);
  a.href = u; a.download = `invoice-${sessionId.slice(-6)}.pdf`; a.click(); URL.revokeObjectURL(u);
}

export default function PaymentSuccess() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const sessionId = sp.get("session_id");
  const [state, setState] = useState({ status: "polling", data: null });
  const [attempts, setAttempts] = useState(0);

  const poll = useCallback(async () => {
    if (!sessionId) return setState({ status: "error", data: "Missing session id" });
    try {
      const { data } = await api.get(`/payments/status/${sessionId}`);
      if (data.payment_status === "paid") return setState({ status: "paid", data });
      if (["expired", "failed"].includes(data.payment_status)) return setState({ status: "failed", data });
      setAttempts((a) => a + 1);
    } catch (e) { setState({ status: "error", data: e.message }); }
  }, [sessionId]);

  useEffect(() => {
    if (state.status === "polling" && attempts < 20) {
      const t = setTimeout(poll, attempts === 0 ? 500 : 2500);
      return () => clearTimeout(t);
    }
    if (attempts >= 20 && state.status === "polling") setState({ status: "timeout", data: null });
  }, [attempts, poll, state.status]);

  return (
    <div className="min-h-screen grid place-items-center bg-zinc-950 p-6" data-testid="payment-success-page">
      <div className="w-full max-w-md text-center">
        {state.status === "polling" && (
          <div>
            <Loader2 className="w-16 h-16 text-yellow-400 mx-auto animate-spin" />
            <div className="mt-6 font-display text-2xl font-bold">Confirming payment…</div>
            <div className="text-sm text-zinc-500 mt-2">Attempt {attempts + 1}/20</div>
          </div>
        )}
        {state.status === "paid" && (
          <div data-testid="payment-paid">
            <CheckCircle2 className="w-16 h-16 text-green-400 mx-auto" />
            <div className="mt-6 font-display text-3xl font-bold text-green-400">Payment received</div>
            <div className="text-sm text-zinc-400 mt-2">₹{state.data?.amount} · session {sessionId?.slice(0, 12)}…</div>
            <div className="mt-8 flex gap-3 justify-center">
              <button data-testid="download-invoice" onClick={() => downloadInvoice(sessionId)} className="border border-zinc-700 hover:border-yellow-400 text-white px-5 py-3 rounded font-medium">Download Invoice PDF</button>
              <button data-testid="back-dashboard" onClick={() => nav("/advertiser/payments")} className="bg-yellow-400 hover:bg-yellow-300 text-zinc-950 px-6 py-3 rounded font-semibold">Back to dashboard</button>
            </div>
          </div>
        )}
        {(state.status === "failed" || state.status === "timeout" || state.status === "error") && (
          <div>
            <XCircle className="w-16 h-16 text-red-400 mx-auto" />
            <div className="mt-6 font-display text-2xl font-bold text-red-400">{state.status === "timeout" ? "Still confirming…" : "Payment not completed"}</div>
            <Link to="/advertiser/payments" className="mt-6 inline-block text-yellow-400 hover:text-yellow-300">Back to payments →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
