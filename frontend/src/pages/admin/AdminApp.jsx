import { Routes, Route, Navigate } from "react-router-dom";
import Shell from "@/pages/Shell";
import { LayoutDashboard, Users, Car, Cpu, Building2, FileImage, Megaphone, ListOrdered, Newspaper, Cloud, QrCode, BarChart3, Wallet, Bell, ScrollText, Eye, Gamepad2, Shield, Upload } from "lucide-react";
import Dashboard from "@/pages/admin/sections/Dashboard";
import DriversPage from "@/pages/admin/sections/Drivers";
import VehiclesPage from "@/pages/admin/sections/Vehicles";
import DevicesPage from "@/pages/admin/sections/Devices";
import Advertisers from "@/pages/admin/sections/Advertisers";
import AdsPage from "@/pages/admin/sections/Ads";
import CampaignsPage from "@/pages/admin/sections/Campaigns";
import PlaylistsPage from "@/pages/admin/sections/Playlists";
import NewsPage from "@/pages/admin/sections/News";
import WeatherPage from "@/pages/admin/sections/Weather";
import QrPage from "@/pages/admin/sections/QrCampaigns";
import Reports from "@/pages/admin/sections/Reports";
import Payments from "@/pages/admin/sections/Payments";
import Notifications from "@/pages/admin/sections/Notifications";
import AuditLogs from "@/pages/admin/sections/AuditLogs";
import Audience from "@/pages/admin/sections/Audience";
import Engagement from "@/pages/admin/sections/Engagement";
import Games from "@/pages/admin/sections/Games";
import Privacy from "@/pages/admin/sections/Privacy";
import BulkImport from "@/pages/admin/sections/BulkImport";

const nav = [
  { key: "dashboard", to: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { key: "drivers", to: "/admin/drivers", label: "Drivers", icon: Users },
  { key: "bulk", to: "/admin/bulk-import", label: "Bulk Import", icon: Upload },
  { key: "vehicles", to: "/admin/vehicles", label: "Vehicles", icon: Car },
  { key: "devices", to: "/admin/devices", label: "Devices", icon: Cpu },
  { key: "advertisers", to: "/admin/advertisers", label: "Advertisers", icon: Building2 },
  { key: "ads", to: "/admin/ads", label: "Advertisements", icon: FileImage },
  { key: "campaigns", to: "/admin/campaigns", label: "Campaigns", icon: Megaphone },
  { key: "games", to: "/admin/games", label: "Mini-Games", icon: Gamepad2 },
  { key: "audience", to: "/admin/audience", label: "AI Audience", icon: Eye },
  { key: "engagement", to: "/admin/engagement", label: "Engagement", icon: BarChart3 },
  { key: "playlists", to: "/admin/playlists", label: "Playlists", icon: ListOrdered },
  { key: "news", to: "/admin/news", label: "News", icon: Newspaper },
  { key: "weather", to: "/admin/weather", label: "Weather", icon: Cloud },
  { key: "qr", to: "/admin/qr", label: "QR Campaigns", icon: QrCode },
  { key: "reports", to: "/admin/reports", label: "Reports", icon: BarChart3 },
  { key: "payments", to: "/admin/payments", label: "Payments", icon: Wallet },
  { key: "privacy", to: "/admin/privacy", label: "Privacy", icon: Shield },
  { key: "notifications", to: "/admin/notifications", label: "Notifications", icon: Bell },
  { key: "audit", to: "/admin/audit", label: "Audit Logs", icon: ScrollText },
];

export default function AdminApp() {
  return (
    <Shell nav={nav} title="Admin">
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="drivers" element={<DriversPage />} />
        <Route path="vehicles" element={<VehiclesPage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="advertisers" element={<Advertisers />} />
        <Route path="ads" element={<AdsPage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="playlists" element={<PlaylistsPage />} />
        <Route path="news" element={<NewsPage />} />
        <Route path="weather" element={<WeatherPage />} />
        <Route path="qr" element={<QrPage />} />
        <Route path="games" element={<Games />} />
        <Route path="audience" element={<Audience />} />
        <Route path="engagement" element={<Engagement />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="bulk-import" element={<BulkImport />} />
        <Route path="reports" element={<Reports />} />
        <Route path="payments" element={<Payments />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="audit" element={<AuditLogs />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </Shell>
  );
}
