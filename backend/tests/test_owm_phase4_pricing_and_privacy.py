"""Phase 4 backend tests:
- Regression of privacy `== False` behavior (POST /player/audience when camera disabled)
- Regression of health-alert `== False` triggers (battery_low, camera_fail) + 15-min dedupe
- New INR pricing endpoints (plans CRUD, calc breakdown w/ GST, purchase w/ Stripe INR, quote flow)
- Env-var fallback: this file also relies on os.environ.get() defaults for admin creds
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@onwheelsmedia.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")

S = {}


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ============= Setup: admin + advertiser + driver + device ============
def test_p4_00_setup():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    S["admin_tok"] = r.json()["access_token"]

    a_email = f"TEST_p4adv_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": a_email, "password": "Passw0rd!", "name": "AdvP4",
        "role": "advertiser", "company": "P4"
    })
    assert r.status_code == 200
    S["adv_tok"] = r.json()["access_token"]

    d_email = f"TEST_p4drv_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": d_email, "password": "Passw0rd!", "name": "DrvP4", "role": "driver"
    })
    assert r.status_code == 200
    S["drv_tok"] = r.json()["access_token"]

    r = requests.post(f"{API}/drivers", json={
        "full_name": "DrvP4", "phone": "9", "address": "1", "city": "B",
        "state": "K", "vehicle_reg_no": f"KA-P4-{uuid.uuid4().hex[:4].upper()}",
        "vehicle_type": "Auto", "manufacturer": "Bajaj", "model": "RE",
        "year": 2023, "color": "Y", "operating_area": "HSR"
    }, headers=_auth(S["drv_tok"]))
    assert r.status_code == 200
    S["driver_id"] = r.json()["id"]
    me = requests.get(f"{API}/drivers/me", headers=_auth(S["drv_tok"])).json()
    S["vehicle_id"] = me["vehicle"]["id"]

    requests.patch(f"{API}/admin/drivers/{S['driver_id']}",
                   json={"status": "Approved"}, headers=_auth(S["admin_tok"]))

    r = requests.post(f"{API}/devices/register",
                      json={"vehicle_id": S["vehicle_id"], "app_version": "1.0"},
                      headers=_auth(S["drv_tok"]))
    assert r.status_code == 200
    S["device_id"] = r.json()["id"]
    activation = r.json()["activation_code"]

    requests.patch(f"{API}/admin/devices/{S['device_id']}",
                   json={"status": "Approved"}, headers=_auth(S["admin_tok"]))

    r = requests.post(f"{API}/player/activate", json={"activation_code": activation})
    assert r.status_code == 200 and r.json()["approved"]
    S["dev_tok"] = r.json()["device_token"]


# ============ `== False` migration: privacy ============
def test_p4_10_audience_ok_when_camera_enabled():
    # Ensure camera_enabled = True first
    r = requests.patch(f"{API}/admin/privacy",
                       json={"camera_enabled": True, "face_analysis_enabled": True,
                             "upload_raw_footage": False, "data_retention_days": 30,
                             "show_camera_notice": True, "mirror_enabled": True},
                       headers=_auth(S["admin_tok"]))
    assert r.status_code == 200 and r.json()["camera_enabled"] is True

    r = requests.post(f"{API}/player/audience",
                      json={"viewers": 1, "people_present": True, "attention_score": 50},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True


def test_p4_11_audience_returns_ok_false_when_camera_disabled():
    """Verifies `cfg.get('camera_enabled', True) == False` still blocks audience samples."""
    r = requests.patch(f"{API}/admin/privacy",
                       json={"camera_enabled": False, "face_analysis_enabled": True,
                             "upload_raw_footage": False, "data_retention_days": 30,
                             "show_camera_notice": True, "mirror_enabled": True},
                       headers=_auth(S["admin_tok"]))
    assert r.status_code == 200 and r.json()["camera_enabled"] is False

    r = requests.post(f"{API}/player/audience",
                      json={"viewers": 2, "people_present": True, "attention_score": 70},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    assert "camera" in (body.get("reason") or "").lower()

    # Restore
    requests.patch(f"{API}/admin/privacy",
                   json={"camera_enabled": True, "face_analysis_enabled": True,
                         "upload_raw_footage": False, "data_retention_days": 30,
                         "show_camera_notice": True, "mirror_enabled": True},
                   headers=_auth(S["admin_tok"]))


# ============ `== False` migration: health alerts ============
def _get_open_alert_kinds():
    r = requests.get(f"{API}/admin/alerts?resolved=false", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    return r.json()


def _resolve_alerts_for_device(device_id, kinds=None):
    alerts = _get_open_alert_kinds()
    for a in alerts:
        if a.get("device_id") == device_id and (kinds is None or a.get("kind") in kinds):
            requests.post(f"{API}/admin/alerts/{a['id']}/resolve", headers=_auth(S["admin_tok"]))


def test_p4_20_battery_low_alert_charging_false():
    """battery<15 + charging==False should raise battery_low alert."""
    # Clean slate for this device's alerts
    _resolve_alerts_for_device(S["device_id"])

    r = requests.post(f"{API}/player/health",
                      json={"battery": 5, "charging": False, "camera_ok": True},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200

    alerts = _get_open_alert_kinds()
    battery_alerts = [a for a in alerts
                      if a.get("device_id") == S["device_id"] and a.get("kind") == "battery_low"]
    assert len(battery_alerts) == 1, f"Expected 1 battery_low alert, got {len(battery_alerts)}"


def test_p4_21_battery_low_dedup_within_15min():
    """Second identical health post within 15 min should NOT create a duplicate battery_low."""
    r = requests.post(f"{API}/player/health",
                      json={"battery": 4, "charging": False, "camera_ok": True},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    alerts = _get_open_alert_kinds()
    battery_alerts = [a for a in alerts
                      if a.get("device_id") == S["device_id"] and a.get("kind") == "battery_low"]
    assert len(battery_alerts) == 1, f"Dedup broken; battery_low count = {len(battery_alerts)}"


def test_p4_22_no_battery_alert_when_charging_true():
    """battery<15 but charging=True should NOT re-alert (still deduped, and the condition is False anyway)."""
    # Resolve existing to ensure a fresh test
    _resolve_alerts_for_device(S["device_id"], kinds={"battery_low"})
    r = requests.post(f"{API}/player/health",
                      json={"battery": 3, "charging": True, "camera_ok": True},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    alerts = _get_open_alert_kinds()
    battery_alerts = [a for a in alerts
                      if a.get("device_id") == S["device_id"] and a.get("kind") == "battery_low"]
    assert len(battery_alerts) == 0, "Should not alert when charging is True"


def test_p4_23_camera_fail_alert():
    _resolve_alerts_for_device(S["device_id"], kinds={"camera_fail"})
    r = requests.post(f"{API}/player/health",
                      json={"camera_ok": False},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    alerts = _get_open_alert_kinds()
    cam_alerts = [a for a in alerts
                  if a.get("device_id") == S["device_id"] and a.get("kind") == "camera_fail"]
    assert len(cam_alerts) == 1

    # dedupe
    r = requests.post(f"{API}/player/health",
                      json={"camera_ok": False},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    alerts = _get_open_alert_kinds()
    cam_alerts = [a for a in alerts
                  if a.get("device_id") == S["device_id"] and a.get("kind") == "camera_fail"]
    assert len(cam_alerts) == 1, "camera_fail dedup broken"


# ============ INR pricing: settings ============
def test_p4_30_pricing_settings_defaults():
    r = requests.get(f"{API}/admin/pricing-settings", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["currency_code"] == "INR"
    assert cfg["gst_enabled"] is True
    assert float(cfg["gst_percentage"]) == 18.0

    # public
    r = requests.get(f"{API}/pricing-settings/public")
    assert r.status_code == 200
    assert r.json()["currency_code"] == "INR"


# ============ INR pricing: plans CRUD ============
def test_p4_31_plans_crud_and_public():
    # create per_auto plan
    r = requests.post(f"{API}/admin/plans", json={
        "name": f"TEST_p4_per_auto_{uuid.uuid4().hex[:6]}",
        "autos": 1, "duration_days": 30, "price_inr": 500.0,
        "estimated_reach": 100000, "features": ["GPS", "HD"],
        "pricing_model": "per_auto", "is_custom": False, "active": True, "sort_order": 1
    }, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["price_inr"] == 500.0
    assert plan["pricing_model"] == "per_auto"
    assert "id" in plan
    S["plan_per_auto"] = plan["id"]

    # per_day
    r = requests.post(f"{API}/admin/plans", json={
        "name": f"TEST_p4_per_day_{uuid.uuid4().hex[:6]}",
        "autos": 1, "duration_days": 1, "price_inr": 200.0,
        "pricing_model": "per_day", "active": True
    }, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    S["plan_per_day"] = r.json()["id"]

    # list admin
    r = requests.get(f"{API}/admin/plans", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert S["plan_per_auto"] in ids and S["plan_per_day"] in ids

    # list public — only active
    r = requests.get(f"{API}/plans/public")
    assert r.status_code == 200
    active_ids = [p["id"] for p in r.json()]
    assert S["plan_per_auto"] in active_ids

    # NO mongo _id leaked
    for p in r.json():
        assert "_id" not in p


# ============ INR pricing: calculate w/ GST ============
def test_p4_40_calculate_per_auto_plan_with_gst():
    r = requests.post(f"{API}/pricing/calculate", json={
        "autos": 3, "duration_days": 30, "estimated_impressions": 0,
        "pricing_model": "per_auto", "plan_id": S["plan_per_auto"]
    })
    assert r.status_code == 200, r.text
    data = r.json()
    # 500 * 3 = 1500 subtotal; GST 18% = 270; total = 1770
    assert data["currency"] == "INR"
    assert data["subtotal"] == 1500.0
    assert data["gst_amount"] == 270.0
    assert data["total"] == 1770.0
    assert data["gst_enabled"] is True
    assert data["gst_percentage"] == 18.0
    assert isinstance(data["breakdown"], list) and len(data["breakdown"]) >= 1


def test_p4_41_calculate_without_plan_id_generic_per_auto():
    r = requests.post(f"{API}/pricing/calculate", json={
        "autos": 2, "duration_days": 5,
        "pricing_model": "per_auto"
    })
    assert r.status_code == 200
    d = r.json()
    # picks first active per_auto plan (₹500/auto): 500*2*5 = 5000; +18% GST = 900; total 5900
    assert d["subtotal"] == 5000.0
    assert d["total"] == 5900.0


def test_p4_42_calculate_invalid_plan_id_404():
    # Non-existent plan id should 404
    r = requests.post(f"{API}/pricing/calculate", json={
        "autos": 1, "duration_days": 1, "pricing_model": "per_auto",
        "plan_id": "507f1f77bcf86cd799439011"
    })
    assert r.status_code == 404


# ============ INR pricing: purchase → Stripe INR checkout + campaign snapshot ============
def test_p4_50_purchase_creates_campaign_and_stripe_inr():
    r = requests.post(f"{API}/pricing/purchase", json={
        "plan_id": S["plan_per_auto"], "autos": 2, "duration_days": 7,
        "estimated_impressions": 0, "pricing_model": "per_auto",
        "campaign_name": "TEST_p4_campaign", "target_city": "Bangalore",
        "origin_url": "https://example.com"
    }, headers=_auth(S["adv_tok"]))
    assert r.status_code == 200, r.text
    d = r.json()
    assert "checkout_url" in d and d["checkout_url"].startswith("https://checkout.stripe.com/")
    assert d.get("session_id", "").startswith("cs_test_")
    assert d["amount_inr"] > 0
    assert "campaign_id" in d
    S["p4_session_id"] = d["session_id"]
    S["p4_campaign_id"] = d["campaign_id"]

    # Verify invoice / transaction retrievable and has snapshot in campaign
    inv = requests.get(f"{API}/invoices/{d['session_id']}", headers=_auth(S["adv_tok"]))
    assert inv.status_code == 200
    ijson = inv.json()
    assert ijson["transaction"]["currency"] == "inr"
    assert ijson["campaign"] is not None
    snap = ijson["campaign"].get("pricing_snapshot") or {}
    assert snap.get("currency") == "INR"
    assert snap.get("plan_id") == S["plan_per_auto"]


# ============ Quotes flow ============
def test_p4_60_quote_request_and_admin_reply():
    r = requests.post(f"{API}/quotes/request", json={
        "autos": 100, "target_city": "Mumbai", "duration_days": 60,
        "estimated_views": 5000000, "ad_format": "video",
        "special_requirements": "PAN-India rollout",
        "contact_name": "Tester", "contact_phone": "+919000000000"
    }, headers=_auth(S["adv_tok"]))
    assert r.status_code == 200, r.text
    q = r.json()
    assert "id" in q
    qid = q["id"]

    # admin list
    r = requests.get(f"{API}/admin/quotes", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert any(x["id"] == qid for x in r.json())

    # advertiser sees own
    r = requests.get(f"{API}/quotes/mine", headers=_auth(S["adv_tok"]))
    assert r.status_code == 200
    assert any(x["id"] == qid for x in r.json())

    # admin replies with quoted price
    r = requests.patch(f"{API}/admin/quotes/{qid}",
                       json={"status": "quoted", "admin_price_inr": 250000,
                             "admin_notes": "Includes GPS + priority slots"},
                       headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    upd = r.json()
    assert upd["status"] == "quoted"
    assert float(upd["admin_price_inr"]) == 250000


# ============ Cleanup (best-effort) ============
def test_p4_99_cleanup():
    # delete test plans
    for pid_key in ("plan_per_auto", "plan_per_day"):
        pid = S.get(pid_key)
        if pid:
            requests.delete(f"{API}/admin/plans/{pid}", headers=_auth(S["admin_tok"]))
