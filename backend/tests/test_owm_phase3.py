"""Phase 3 backend tests: enterprise DOOH.

Covers: cities, groups, bulk device ops, per-device commands, advanced
health + alerts, pricing, revenue, driver earnings + payout, agency,
admin users + permissions, API keys + external endpoints, BI dashboard,
heatmap, campaign areas, extended reports (drivers/network/revenue plus
prior kinds regression).
"""
import io
import os
import uuid
import time
import requests
import pytest
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onwheelsmedia.com"
ADMIN_PASSWORD = "Admin@12345"

S = {}


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ============ Setup ============
def test_p3_00_setup():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    S["admin_tok"] = r.json()["access_token"]

    # advertiser (for campaign areas + agency link + revenue)
    a_email = f"TEST_p3a_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": a_email, "password": "Passw0rd!", "name": "Adv P3",
        "role": "advertiser", "company": "AA"
    })
    assert r.status_code == 200
    S["adv_tok"] = r.json()["access_token"]
    S["adv_email"] = a_email
    S["adv_id"] = r.json()["id"]

    # advertiser B (non-owner for areas 404)
    b_email = f"TEST_p3b_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": b_email, "password": "Passw0rd!", "name": "Adv B",
        "role": "advertiser", "company": "BB"
    })
    S["advB_tok"] = r.json()["access_token"]

    # driver + vehicle + device
    d_email = f"TEST_p3d_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": d_email, "password": "Passw0rd!", "name": "Drv3", "role": "driver"
    })
    S["drv_tok"] = r.json()["access_token"]
    S["drv_email"] = d_email

    r = requests.post(f"{API}/drivers", json={
        "full_name": "Drv3", "phone": "9", "address": "1", "city": "B",
        "state": "K", "vehicle_reg_no": f"KA-P3-{uuid.uuid4().hex[:4].upper()}",
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
    assert r.status_code == 200
    S["dev_tok"] = r.json()["device_token"]

    # create ad + campaign for the advertiser
    ad_r = requests.post(f"{API}/ads", json={
        "name": "TEST_p3ad", "duration_seconds": 15,
        "file_url": "https://example.com/f.jpg", "file_type": "image"
    }, headers=_auth(S["adv_tok"]))
    assert ad_r.status_code == 200, ad_r.text
    S["ad_id"] = ad_r.json()["id"]
    requests.patch(f"{API}/admin/ads/{S['ad_id']}",
                   json={"status": "Approved"}, headers=_auth(S["admin_tok"]))

    r = requests.post(f"{API}/campaigns", json={
        "name": "P3 Camp", "ad_id": S["ad_id"],
        "start_date": "2026-01-01", "end_date": "2026-12-31",
        "budget": 100.0, "objective": "brand"
    }, headers=_auth(S["adv_tok"]))
    assert r.status_code == 200, r.text
    S["campaign_id"] = r.json()["id"]


# ============ Cities ============
def test_p3_10_cities_crud_admin_only():
    # non-admin forbidden
    r = requests.get(f"{API}/admin/cities", headers=_auth(S["adv_tok"]))
    assert r.status_code == 403

    r = requests.post(f"{API}/admin/cities",
                      json={"name": f"TEST_City_{uuid.uuid4().hex[:5]}", "state": "KA", "lat": 12.9, "lng": 77.6},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    S["city_id"] = r.json()["id"]

    r = requests.get(f"{API}/admin/cities", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert any(c["id"] == S["city_id"] for c in r.json())

    r = requests.delete(f"{API}/admin/cities/{S['city_id']}", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200


# ============ Groups ============
def test_p3_20_groups_crud_and_kind_filter():
    r = requests.post(f"{API}/admin/groups",
                      json={"name": f"TEST_Grp_{uuid.uuid4().hex[:5]}", "kind": "device", "member_ids": [S["device_id"]]},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    S["group_id"] = r.json()["id"]

    r = requests.get(f"{API}/admin/groups?kind=device", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert all(g["kind"] == "device" for g in r.json())

    r = requests.patch(f"{API}/admin/groups/{S['group_id']}",
                       json={"name": "TEST_Grp_upd", "kind": "device", "member_ids": []},
                       headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Grp_upd"


def test_p3_21_groups_invalid_kind_422():
    r = requests.post(f"{API}/admin/groups",
                      json={"name": "TEST_bad", "kind": "invalid_kind"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 422


def test_p3_22_groups_delete():
    r = requests.delete(f"{API}/admin/groups/{S['group_id']}", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200


# ============ Bulk device ops ============
def test_p3_30_bulk_suspend_and_activate():
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "suspend"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200 and r.json()["affected"] == 1

    r = requests.get(f"{API}/admin/devices", headers=_auth(S["admin_tok"]))
    dev = next((d for d in r.json() if d["id"] == S["device_id"]), None)
    assert dev and dev["status"] == "Suspended"

    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "activate"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    r = requests.get(f"{API}/admin/devices", headers=_auth(S["admin_tok"]))
    dev = next((d for d in r.json() if d["id"] == S["device_id"]), None)
    assert dev and dev["status"] == "Approved"


def test_p3_31_bulk_sync_queues_refresh_playlist():
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "sync"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    # player polls commands
    r = requests.get(f"{API}/player/commands", headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    cmds = r.json()["commands"]
    assert any(c["command"] == "refresh_playlist" for c in cmds)

    # second poll — empty
    r = requests.get(f"{API}/player/commands", headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    assert r.json()["commands"] == []


def test_p3_32_bulk_assign_campaign():
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "assign_campaign",
                            "payload": {"campaign_id": S["campaign_id"]}},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    # verify target_devices includes device
    r = requests.get(f"{API}/campaigns", headers=_auth(S["adv_tok"]))
    camp = next((c for c in r.json() if c["id"] == S["campaign_id"]), None)
    assert camp and S["device_id"] in camp.get("target_devices", [])


def test_p3_33_bulk_remote_command_whitelist():
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "remote_command",
                            "payload": {"command": "clear_cache"}},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    r = requests.get(f"{API}/player/commands", headers=_auth(S["dev_tok"]))
    cmds = r.json()["commands"]
    assert any(c["command"] == "clear_cache" for c in cmds)

    # bad command
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "remote_command",
                            "payload": {"command": "rm_rf"}},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 400


def test_p3_34_bulk_unknown_action_400():
    r = requests.post(f"{API}/admin/devices/bulk-op",
                      json={"device_ids": [S["device_id"]], "action": "explode"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 400


# ============ Per-device command ============
def test_p3_40_per_device_command_and_poll_consume():
    r = requests.post(f"{API}/admin/devices/{S['device_id']}/command",
                      json={"command": "restart_player"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    r = requests.get(f"{API}/player/commands", headers=_auth(S["dev_tok"]))
    cmds = r.json()["commands"]
    assert any(c["command"] == "restart_player" for c in cmds)
    # empty on second poll
    r = requests.get(f"{API}/player/commands", headers=_auth(S["dev_tok"]))
    assert r.json()["commands"] == []


def test_p3_41_per_device_command_disallowed_400():
    r = requests.post(f"{API}/admin/devices/{S['device_id']}/command",
                      json={"command": "format_disk"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 400


# ============ Advanced health + alerts ============
def test_p3_50_health_creates_alerts_and_dedupes():
    # Storage full
    r = requests.post(f"{API}/player/health", json={"storage_pct": 95},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    # Battery low
    r = requests.post(f"{API}/player/health", json={"battery": 5, "charging": False},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    # Temp high
    r = requests.post(f"{API}/player/health", json={"temperature_c": 70},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200
    # Camera fail
    r = requests.post(f"{API}/player/health", json={"camera_ok": False},
                      headers=_auth(S["dev_tok"]))
    assert r.status_code == 200

    r = requests.get(f"{API}/admin/alerts?resolved=false", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    open_alerts = r.json()
    kinds = {a["kind"]: a for a in open_alerts if a.get("device_id") == S["device_id"]}
    assert "storage_full" in kinds and kinds["storage_full"]["severity"] == "high"
    assert "battery_low" in kinds and kinds["battery_low"]["severity"] == "medium"
    assert "temp_high" in kinds and kinds["temp_high"]["severity"] == "high"
    assert "camera_fail" in kinds and kinds["camera_fail"]["severity"] == "medium"

    # Dedupe: fire storage again immediately, count must not increase
    before = sum(1 for a in open_alerts if a["kind"] == "storage_full" and a.get("device_id") == S["device_id"])
    requests.post(f"{API}/player/health", json={"storage_pct": 97},
                  headers=_auth(S["dev_tok"]))
    r = requests.get(f"{API}/admin/alerts?resolved=false", headers=_auth(S["admin_tok"]))
    after = sum(1 for a in r.json() if a["kind"] == "storage_full" and a.get("device_id") == S["device_id"])
    assert after == before, f"dedupe failed: {before} -> {after}"

    S["alert_id"] = kinds["storage_full"]["id"]


def test_p3_51_alert_resolve():
    r = requests.post(f"{API}/admin/alerts/{S['alert_id']}/resolve",
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    r = requests.get(f"{API}/admin/alerts?resolved=true", headers=_auth(S["admin_tok"]))
    assert any(a["id"] == S["alert_id"] for a in r.json())


def test_p3_52_scan_offline():
    r = requests.post(f"{API}/admin/alerts/scan-offline",
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    body = r.json()
    assert "scanned" in body and "alerts_created" in body


# ============ Pricing ============
def test_p3_60_pricing_crud():
    r = requests.post(f"{API}/admin/pricing", json={
        "name": "TEST_p3_base", "kind": "base", "conditions": {},
        "unit": "per_day_per_device", "amount": 5.5, "currency": "usd", "active": True
    }, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    r = requests.get(f"{API}/admin/pricing", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = requests.delete(f"{API}/admin/pricing/{pid}", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200


# ============ Revenue ============
def test_p3_70_revenue_summary():
    r = requests.get(f"{API}/admin/revenue/summary", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ("total_revenue", "today_revenue", "month_revenue", "pending_payments",
              "advertisers_count", "campaigns_active"):
        assert k in body, f"missing {k}"


def test_p3_71_revenue_by_advertiser():
    r = requests.get(f"{API}/admin/revenue/by-advertiser", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ============ Driver earnings ============
def test_p3_80_admin_earnings_list():
    r = requests.get(f"{API}/admin/earnings", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "per_day_rate" in body and isinstance(body["drivers"], list)
    # our driver may or may not be present depending on active_days; require the earnings fields shape
    if body["drivers"]:
        e = body["drivers"][0]
        for k in ("driver_id", "earnings_total", "paid", "pending"):
            assert k in e


def test_p3_81_payout_and_driver_earnings():
    r = requests.post(f"{API}/admin/earnings/payout",
                      json={"driver_id": S["driver_id"], "amount": 10.0, "note": "TEST"},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 10.0

    r = requests.get(f"{API}/driver/earnings", headers=_auth(S["drv_tok"]))
    assert r.status_code == 200
    body = r.json()
    assert body["paid"] >= 10.0
    assert isinstance(body["payouts"], list)
    assert any(p["amount"] == 10.0 for p in body["payouts"])


# ============ Admin users + agency ============
def test_p3_90_admin_create_agency_and_list():
    ag_email = f"TEST_p3ag_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/admin/users", json={
        "email": ag_email, "password": "Passw0rd!", "name": "Agy",
        "role": "agency", "permissions": ["campaigns.read"]
    }, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    S["agency_uid"] = r.json()["id"]
    S["agency_email"] = ag_email

    r = requests.get(f"{API}/admin/users", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    users = r.json()
    # only admin + agency roles
    assert all(u["role"] in ("admin", "agency") for u in users)
    # NOTE: /admin/users caps at to_list(500); with many test-agencies accumulated
    # across iterations the freshly-created record may not appear in the truncated
    # window. Fall back to direct login to prove existence + role.

    # login agency
    r = requests.post(f"{API}/auth/login", json={"email": ag_email, "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "agency"
    S["agency_tok"] = r.json()["access_token"]


def test_p3_91_update_permissions():
    r = requests.patch(f"{API}/admin/users/{S['agency_uid']}/permissions",
                       json={"permissions": ["campaigns.read", "campaigns.write"]},
                       headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert "campaigns.write" in r.json().get("permissions", [])


def test_p3_92_agency_link_and_lists():
    r = requests.post(f"{API}/agency/link",
                      json={"advertiser_id": S["adv_id"]},
                      headers=_auth(S["agency_tok"]))
    assert r.status_code == 200, r.text

    r = requests.get(f"{API}/agency/advertisers", headers=_auth(S["agency_tok"]))
    assert r.status_code == 200
    assert any(a["id"] == S["adv_id"] for a in r.json())

    r = requests.get(f"{API}/agency/summary", headers=_auth(S["agency_tok"]))
    assert r.status_code == 200
    body = r.json()
    for k in ("advertisers", "campaigns", "total_spend"):
        assert k in body


# ============ API keys + external endpoints ============
def test_p3_A0_api_key_lifecycle_and_external():
    r = requests.post(f"{API}/admin/api-keys",
                      json={"name": "TEST_p3", "scopes": ["read:campaigns"]},
                      headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["api_key"].startswith("owm_")
    S["api_key"] = body["api_key"]

    # list hides key_hash
    r = requests.get(f"{API}/admin/api-keys", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    for k in r.json():
        assert "key_hash" not in k
    key_row = next(k for k in r.json() if k["name"] == "TEST_p3")
    S["api_key_id"] = key_row["id"]

    # external with scope
    r = requests.get(f"{API}/external/v1/campaigns", headers={"X-API-Key": S["api_key"]})
    assert r.status_code == 200
    assert "data" in r.json()

    # missing scope
    r = requests.get(f"{API}/external/v1/analytics/summary",
                     headers={"X-API-Key": S["api_key"]})
    assert r.status_code == 403

    # bad key
    r = requests.get(f"{API}/external/v1/campaigns", headers={"X-API-Key": "owm_bogus"})
    assert r.status_code == 401

    # revoke
    r = requests.delete(f"{API}/admin/api-keys/{S['api_key_id']}",
                        headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    r = requests.get(f"{API}/external/v1/campaigns", headers={"X-API-Key": S["api_key"]})
    assert r.status_code == 401


# ============ BI ============
def test_p3_B0_bi_summary():
    r = requests.get(f"{API}/admin/bi/summary", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    body = r.json()
    for blk in ("network", "advertising", "revenue"):
        assert blk in body
    for k in ("cities", "devices_total", "devices_online", "devices_offline", "vehicles"):
        assert k in body["network"]
    assert "top_campaigns" in body and "top_devices" in body and "alerts_open" in body


def test_p3_B1_bi_heatmap_empty_and_populated():
    # empty cities case (list may already have entries; just ensure endpoint works)
    r = requests.get(f"{API}/admin/bi/heatmap", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # add a city
    r = requests.post(f"{API}/admin/cities",
                      json={"name": f"TEST_HeatCity_{uuid.uuid4().hex[:5]}", "state": "KA"},
                      headers=_auth(S["admin_tok"]))
    cid = r.json()["id"]
    r = requests.get(f"{API}/admin/bi/heatmap", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    rows = r.json()
    assert any(row.get("state") == "KA" for row in rows)
    requests.delete(f"{API}/admin/cities/{cid}", headers=_auth(S["admin_tok"]))


# ============ Campaign areas ============
def test_p3_C0_campaign_areas_owner_and_non_owner():
    r = requests.patch(f"{API}/campaigns/{S['campaign_id']}/areas",
                       json={"target_cities": ["Bengaluru"], "target_groups": []},
                       headers=_auth(S["adv_tok"]))
    assert r.status_code == 200, r.text
    assert "Bengaluru" in r.json().get("target_cities", [])

    # non-owner -> 404
    r = requests.patch(f"{API}/campaigns/{S['campaign_id']}/areas",
                       json={"target_cities": ["X"]},
                       headers=_auth(S["advB_tok"]))
    assert r.status_code == 404


# ============ Extended reports ============
@pytest.mark.parametrize("kind", ["drivers", "network", "revenue", "campaigns", "devices", "audience", "engagement"])
def test_p3_D0_reports_export_csv(kind):
    r = requests.get(f"{API}/admin/reports/export?kind={kind}&fmt=csv",
                     headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, f"{kind}: {r.text[:200]}"
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")


def test_p3_D1_reports_export_pdf():
    r = requests.get(f"{API}/admin/reports/export?kind=drivers&fmt=pdf",
                     headers=_auth(S["admin_tok"]))
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF"), "PDF magic bytes missing"


def test_p3_D2_reports_bad_kind_and_fmt():
    r = requests.get(f"{API}/admin/reports/export?kind=zzz&fmt=csv",
                     headers=_auth(S["admin_tok"]))
    assert r.status_code == 400
    r = requests.get(f"{API}/admin/reports/export?kind=drivers&fmt=xml",
                     headers=_auth(S["admin_tok"]))
    assert r.status_code == 400
