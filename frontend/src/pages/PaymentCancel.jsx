import { Link } from "react-router-dom";
export default function PaymentCancel() {
  return (
    <div className="min-h-screen grid place-items-center bg-zinc-950 text-center p-6" data-testid="payment-cancel">
      <div>
        <div className="font-display text-3xl font-bold">Payment canceled</div>
        <p className="text-zinc-500 mt-2 text-sm">No charge was made. You can try again anytime.</p>
        <Link to="/advertiser/payments" className="mt-6 inline-block text-yellow-400 hover:text-yellow-300">← Back to payments</Link>
      </div>
    </div>
  );
}
