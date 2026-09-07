# ON WHEELS MEDIA — Product Requirements Document

## Original Problem Statement
Build a functional, production-ready MVP for ON WHEELS MEDIA, a digital advertising platform
that places screens inside passenger autos/tuk-tuks. Phase 1 covers driver/vehicle/device
management, advertiser dashboard, campaign lifecycle, kiosk player with offline cache, and
admin control plane.

## User Choices (locked in)
- **Android Player**: Web-based PWA/kiosk player running in Chrome kiosk mode
- **Auth**: Custom JWT (email + password) for Admin/Advertiser/Driver
- **Weather**: OpenWeatherMap (mocked fallback active until `OPENWEATHER_API_KEY` is set)
- **Payments**: Stripe (records + invoice architecture in place; checkout wiring deferred)
- **File storage**: Emergent-managed Object Storage

## Architecture
- **Backend** — FastAPI, MongoDB (motor), single `server.py` with `/api` prefix
- **Frontend** — React 19 + Tailwind + shadcn, dark-mode design (auto-yellow + electric-cyan)
- **Auth** — bcrypt + PyJWT, httpOnly cookies + Bearer fallback for kiosk devices
- **Storage** — Emergent Object Storage via `EMERGENT_LLM_KEY`; DB is source of truth (`files` coll.)
- **Kiosk player** — Web app at `/player`, activation-code pairing, JWT device token, 30s
  heartbeat, 60s playlist sync, offline event buffer, local-storage cached playlist

## User Personas
- **Super Admin** (seeded: `admin@onwheelsmedia.com` / `Admin@12345`)
- **Advertiser** — self-registers, uploads ads, creates campaigns
- **Driver / Vehicle Owner** — self-registers, submits vehicle+documents, pairs device
- **Passenger** — no account; interacts via QR scan

## What's Implemented (Feb 2026)
- **Auth**: register/login/logout/me, seeded admin, JWT (12h access + 7d refresh)
- **Drivers**: registration form + vehicle creation, admin list/search/approve
- **Vehicles**: admin list with driver+device joined view
- **Devices**: auto-generated `OWM-AUTO-000001` codes, activation code, approval flow, live
  status detection (5-min online cutoff), heartbeat updates
- **Advertisements**: upload (image/video via object storage), review workflow with 7 statuses
- **Campaigns**: creation with targeting, admin can assign devices + change status
- **Playlist engine**: cloud-composed from active campaigns + news + QR + weather
- **News/Weather/QR** admin sections + player rendering
- **Player**: activation page, kiosk playback (image/video/news/weather/QR), offline cache,
  buffered playback events, live marquee ticker, online/offline indicator
- **Reports**: admin stats + 14-day plays chart; advertiser per-campaign + by-day
- **Notifications**: entity notifications (registration, approvals, campaign events)
- **Audit logs**: writes for status changes and reviews
- **Payments (records only)**: invoice CRUD, admin & advertiser views; Stripe checkout deferred

## Test Results (backend, 21/21 passing)
- All Phase 1 acceptance criteria (1-21) covered by pytest suite at
  `/app/backend/tests/test_owm_backend.py`
- End-to-end: driver → vehicle → device → activation → advertiser → ad → approval → campaign →
  device assignment → playlist → heartbeat → playback → reports

## Backlog / Phase 2

**P0 (next up)**
- Full Stripe checkout wiring (invoice → checkout session → webhook → invoice paid)
- Frontend E2E tests (currently only smoke-tested via screenshots)
- Password reset (forgot-password + reset-password flow) — auth playbook items

**P1**
- Manual playlist editor (drag-drop ordering, per-slot duration override)
- Per-device frequency scheduling (`frequency` field is captured but not enforced yet)
- Driver document uploads (currently only vehicle metadata captured)
- Real-time device map / live event stream via WebSocket
- Native Android player APK (bare kiosk mode, MDM lock-down)

**P2**
- Multi-tenant support (agencies with sub-advertisers)
- ML-driven campaign optimisation (best time / best route)
- Passenger interaction analytics (QR conversion funnel)
- Route replay / heatmap
