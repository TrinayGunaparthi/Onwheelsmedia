"""End-to-end backend tests for On Wheels Media Phase 1 MVP."""
import os
import io
import time
import uuid
import requests
import pytest
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to reading frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@onwheelsmedia.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")

# Shared state across tests in this file
STATE = {}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Auth ----------------
def test_admin_login_and_me():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "admin"
    assert "access_token" in data
    STATE["admin_token"] = data["access_token"]

    me = requests.get(f"{API}/auth/me", headers=_auth(STATE["admin_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL


def test_register_advertiser():
    email = f"TEST_adv_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Test Advertiser",
        "role": "advertiser", "phone": "9999", "company": "TestCo"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "advertiser"
    STATE["adv_token"] = data["access_token"]
    STATE["adv_email"] = email
    STATE["adv_id"] = data["id"]


def test_register_driver():
    email = f"TEST_drv_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Test Driver",
        "role": "driver", "phone": "8888"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "driver"
    STATE["drv_token"] = data["access_token"]
    STATE["drv_email"] = email


# ---------------- Driver + Vehicle ----------------
def test_create_driver_profile():
    payload = {
        "full_name": "Test Driver",
        "phone": "8888888888",
        "address": "1 Rd",
        "city": "Blr",
        "state": "KA",
        "vehicle_reg_no": f"KA-01-{uuid.uuid4().hex[:4].upper()}",
        "vehicle_type": "Auto",
        "manufacturer": "Bajaj",
        "model": "RE",
        "year": 2022,
        "color": "Yellow",
        "operating_area": "Koramangala",
    }
    r = requests.post(f"{API}/drivers", json=payload, headers=_auth(STATE["drv_token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "Pending"
    STATE["driver_id"] = data["id"]

    # Verify vehicle was created
    me = requests.get(f"{API}/drivers/me", headers=_auth(STATE["drv_token"]))
    assert me.status_code == 200
    j = me.json()
    assert j["driver"]["status"] == "Pending"
    assert j["vehicle"]["status"] == "Pending"
    STATE["vehicle_id"] = j["vehicle"]["id"]


def test_admin_approve_driver():
    lst = requests.get(f"{API}/admin/drivers", headers=_auth(STATE["admin_token"]))
    assert lst.status_code == 200
    assert any(d["id"] == STATE["driver_id"] for d in lst.json())

    r = requests.patch(f"{API}/admin/drivers/{STATE['driver_id']}",
                       json={"status": "Approved"}, headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200
    assert r.json()["status"] == "Approved"

    # Verify vehicle also approved
    me = requests.get(f"{API}/drivers/me", headers=_auth(STATE["drv_token"]))
    assert me.json()["vehicle"]["status"] == "Approved"


# ---------------- Device ----------------
def test_device_register():
    r = requests.post(f"{API}/devices/register",
                      json={"vehicle_id": STATE["vehicle_id"], "app_version": "1.0"},
                      headers=_auth(STATE["drv_token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "Pending"
    assert data["device_code"].startswith("OWM-AUTO-")
    assert data["activation_code"]
    STATE["device_id"] = data["id"]
    STATE["activation_code"] = data["activation_code"]


def test_admin_approve_device():
    r = requests.patch(f"{API}/admin/devices/{STATE['device_id']}",
                       json={"status": "Approved"}, headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200
    assert r.json()["status"] == "Approved"


def test_player_activate():
    r = requests.post(f"{API}/player/activate", json={"activation_code": STATE["activation_code"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["approved"] is True
    assert "device_token" in data
    STATE["device_token"] = data["device_token"]


# ---------------- Uploads + Ads ----------------
def test_upload_image():
    # tiny valid PNG bytes
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
           b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
           b"\xc0\x00\x00\x00\x03\x00\x01\x5b\xf9\xe1\x0b\x00\x00\x00\x00IEND\xaeB`\x82")
    files = {"file": ("test.png", io.BytesIO(png), "image/png")}
    r = requests.post(f"{API}/uploads", files=files, headers=_auth(STATE["adv_token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["url"].startswith("/api/files/")
    assert data["content_type"] == "image/png"
    STATE["file_url"] = data["url"]


def test_create_ad_and_admin_approve():
    r = requests.post(f"{API}/ads", json={
        "name": "TEST_ad", "duration_seconds": 15,
        "file_url": STATE["file_url"], "file_type": "image",
    }, headers=_auth(STATE["adv_token"]))
    assert r.status_code == 200
    ad = r.json()
    assert ad["status"] == "Submitted"
    STATE["ad_id"] = ad["id"]

    lst = requests.get(f"{API}/ads", headers=_auth(STATE["adv_token"]))
    assert lst.status_code == 200
    assert any(a["id"] == STATE["ad_id"] for a in lst.json())

    ap = requests.patch(f"{API}/admin/ads/{STATE['ad_id']}",
                        json={"status": "Approved"}, headers=_auth(STATE["admin_token"]))
    assert ap.status_code == 200
    assert ap.json()["status"] == "Approved"


# ---------------- Campaign ----------------
def test_create_and_activate_campaign():
    today = datetime.now(timezone.utc).date()
    r = requests.post(f"{API}/campaigns", json={
        "name": "TEST_campaign", "ad_id": STATE["ad_id"],
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=5)).isoformat(),
    }, headers=_auth(STATE["adv_token"]))
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "Scheduled"
    STATE["campaign_id"] = c["id"]

    up = requests.patch(f"{API}/admin/campaigns/{STATE['campaign_id']}",
                        json={"status": "Active", "target_devices": [STATE["device_id"]]},
                        headers=_auth(STATE["admin_token"]))
    assert up.status_code == 200
    assert up.json()["status"] == "Active"


# ---------------- News / Weather / QR ----------------
def test_admin_create_news():
    r = requests.post(f"{API}/admin/news", json={
        "headline": "TEST_headline", "description": "desc", "active": True
    }, headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200
    STATE["news_id"] = r.json()["id"]


def test_admin_create_weather():
    r = requests.post(f"{API}/admin/weather", json={
        "location": "Bangalore", "device_ids": [STATE["device_id"]]
    }, headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200


def test_admin_create_qr():
    r = requests.post(f"{API}/admin/qr", json={
        "name": "TEST_qr", "target_url": "https://example.com",
        "device_ids": [STATE["device_id"]]
    }, headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200
    STATE["qr_id"] = r.json()["id"]


# ---------------- Player playlist / heartbeat / playback ----------------
def test_player_playlist():
    r = requests.get(f"{API}/player/playlist", headers=_auth(STATE["device_token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    items = data["items"]
    types = {i["type"] for i in items}
    assert "ad" in types, f"ad missing in playlist: {items}"
    assert "news" in types
    assert "qr" in types
    assert "weather" in types
    w = next(i for i in items if i["type"] == "weather")
    assert w["data"].get("mocked") is True


def test_player_heartbeat():
    r = requests.post(f"{API}/player/heartbeat", json={
        "device_id": STATE["device_id"], "battery": 80, "storage_mb": 2048, "network": "wifi"
    }, headers=_auth(STATE["device_token"]))
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_playback_single_and_batch():
    r = requests.post(f"{API}/player/playback", json={
        "device_id": STATE["device_id"], "ad_id": STATE["ad_id"],
        "campaign_id": STATE["campaign_id"], "completed": True, "duration_played": 15
    }, headers=_auth(STATE["device_token"]))
    assert r.status_code == 200

    r2 = requests.post(f"{API}/player/playback/batch", json=[
        {"device_id": STATE["device_id"], "ad_id": STATE["ad_id"],
         "campaign_id": STATE["campaign_id"], "duration_played": 15},
        {"device_id": STATE["device_id"], "ad_id": STATE["ad_id"],
         "campaign_id": STATE["campaign_id"], "duration_played": 15},
    ], headers=_auth(STATE["device_token"]))
    assert r2.status_code == 200
    assert r2.json()["count"] == 2


# ---------------- Reports ----------------
def test_advertiser_reports():
    time.sleep(0.5)
    r = requests.get(f"{API}/advertiser/reports", headers=_auth(STATE["adv_token"]))
    assert r.status_code == 200
    data = r.json()
    assert data["total_plays"] >= 3
    assert any(pc["id"] == STATE["campaign_id"] and pc["plays"] >= 3 for pc in data["per_campaign"])


def test_admin_stats_and_plays_report():
    r = requests.get(f"{API}/admin/stats", headers=_auth(STATE["admin_token"]))
    assert r.status_code == 200
    data = r.json()
    for key in ("drivers_total", "devices_total", "ads_total", "plays_today"):
        assert key in data

    rp = requests.get(f"{API}/admin/reports/plays?days=7", headers=_auth(STATE["admin_token"]))
    assert rp.status_code == 200
    series = rp.json()
    assert isinstance(series, list) and len(series) == 7


# ---------------- Role/auth guards ----------------
def test_advertiser_cannot_hit_admin():
    r = requests.get(f"{API}/admin/stats", headers=_auth(STATE["adv_token"]))
    assert r.status_code == 403


def test_unauthenticated_401():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401
    r2 = requests.get(f"{API}/admin/stats")
    assert r2.status_code == 401
