import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PaymentCancel from "@/pages/PaymentCancel";
import AdminApp from "@/pages/admin/AdminApp";
import AdvertiserApp from "@/pages/advertiser/AdvertiserApp";
import DriverApp from "@/pages/driver/DriverApp";
import KioskPlayer from "@/pages/player/KioskPlayer";

function Protected({ role, children }) {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-400">Loading…</div>;
  if (user === false) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Toaster theme="dark" richColors position="top-right" />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/payment/success" element={<PaymentSuccess />} />
            <Route path="/payment/cancel" element={<PaymentCancel />} />
            <Route path="/player" element={<KioskPlayer />} />
            <Route path="/admin/*" element={<Protected role="admin"><AdminApp /></Protected>} />
            <Route path="/advertiser/*" element={<Protected role="advertiser"><AdvertiserApp /></Protected>} />
            <Route path="/driver/*" element={<Protected role="driver"><DriverApp /></Protected>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
