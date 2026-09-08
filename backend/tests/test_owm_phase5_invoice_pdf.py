"""Phase 5 backend tests: Invoice meta CRUD + Invoice PDF download.

Approach:
- Verify GET/PATCH /api/admin/invoice-meta defaults, updates, and non-admin 403.
- For PDF: create an advertiser + a paid campaign session by:
  1) calling /api/pricing/purchase (creates campaign + pending payment_transactions row)
  2) directly patching payment_status='paid' in Mongo via motor (skips real Stripe redirect)
- Assert PDF returns application/pdf, %PDF magic bytes, size > 1500, filename contains OWM-.
- Auth matrix: unauth 401, other-adv 403, admin 200, unknown 404.
"""
import os
import uuid
import asyncio
import pytest
import requests

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


# ============ Setup: admin + two advertisers ============
def test_p5_00_setup():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    S["admin_tok"] = r.json()["access_token"]

    for k in ("adv1", "adv2"):
        email = f"TEST_p5{k}_{uuid.uuid4().hex[:8]}@ex.com"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Passw0rd!", "name": f"AdvP5-{k}",
            "role": "advertiser", "company": "P5"
        })
        assert r.status_code == 200, r.text
        S[f"{k}_tok"] = r.json()["access_token"]
        me = requests.get(f"{API}/auth/me", headers=_auth(S[f"{k}_tok"])).json()
        S[f"{k}_id"] = me["id"]


# ============ Invoice Meta ============
def test_p5_01_invoice_meta_defaults():
    r = requests.get(f"{API}/admin/invoice-meta", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    d = r.json()
    # gstin may be "" default; if previously set by another run, allow non-default but assert keys
    assert "gstin" in d
    assert d.get("hsn_code") == "998365" or "hsn_code" in d
    assert "company_name" in d and d["company_name"]
    assert "company_address" in d and d["company_address"]


def test_p5_02_invoice_meta_patch_updates():
    payload = {
        "gstin": "29ABCDE1234F1Z5",
        "hsn_code": "998365",
        "company_address": "On Wheels Media, HSR Layout, Bengaluru, KA, India",
        "company_name": "On Wheels Media Pvt Ltd",
    }
    r = requests.patch(f"{API}/admin/invoice-meta", json=payload, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    # Read back
    r2 = requests.get(f"{API}/admin/invoice-meta", headers=_auth(S["admin_tok"]))
    assert r2.status_code == 200
    d = r2.json()
    assert d["gstin"] == payload["gstin"]
    assert d["hsn_code"] == payload["hsn_code"]
    assert d["company_address"] == payload["company_address"]
    assert d["company_name"] == payload["company_name"]


def test_p5_03_invoice_meta_non_admin_403():
    r = requests.patch(f"{API}/admin/invoice-meta",
                       json={"gstin": "X", "hsn_code": "998365",
                             "company_address": "y", "company_name": "z"},
                       headers=_auth(S["adv1_tok"]))
    assert r.status_code == 403, r.status_code
    # GET is also admin-only
    r2 = requests.get(f"{API}/admin/invoice-meta", headers=_auth(S["adv1_tok"]))
    assert r2.status_code == 403


# ============ Create a paid tx via /pricing/purchase + Mongo patch ============
def _ensure_plan():
    """Ensure there is at least one active plan; create one as admin if needed."""
    r = requests.get(f"{API}/admin/plans", headers=_auth(S["admin_tok"]))
    plans = r.json() if r.status_code == 200 else []
    active = [p for p in plans if p.get("active")]
    if active:
        return active[0]["id"]
    # create one
    r = requests.post(f"{API}/admin/plans", json={
        "name": "P5 Basic", "autos": 5, "duration_days": 7,
        "estimated_impressions": 5000, "pricing_model": "package",
        "base_price_inr": 5000.0, "active": True, "sort_order": 1
    }, headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_p5_10_create_purchase_and_mark_paid():
    plan_id = _ensure_plan()
    S["plan_id"] = plan_id
    r = requests.post(f"{API}/pricing/purchase", json={
        "plan_id": plan_id, "autos": 5, "duration_days": 7,
        "estimated_impressions": 5000, "pricing_model": "package",
        "campaign_name": "TEST_P5_Campaign",
        "target_city": "Bengaluru",
        "origin_url": BASE_URL
    }, headers=_auth(S["adv1_tok"]))
    assert r.status_code == 200, r.text
    body = r.json()
    S["session_id"] = body["session_id"]
    S["campaign_id"] = body["campaign_id"]
    assert body["amount_inr"] > 0

    # Directly mark paid in Mongo (skip real Stripe redirect)
    async def _mark_paid():
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "onwheels_media")
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        res = await db.payment_transactions.update_one(
            {"session_id": S["session_id"]},
            {"$set": {"payment_status": "paid", "status": "complete"}}
        )
        client.close()
        return res.modified_count

    modified = asyncio.get_event_loop().run_until_complete(_mark_paid()) \
        if False else asyncio.new_event_loop().run_until_complete(_mark_paid())
    assert modified == 1


# ============ PDF Download tests ============
def test_p5_20_pdf_owner_success():
    r = requests.get(f"{API}/invoices/{S['session_id']}/pdf", headers=_auth(S["adv1_tok"]))
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert "OWM-" in cd, cd
    body = r.content
    assert body[:5] == b"%PDF-", body[:20]
    assert len(body) > 1500, f"pdf too small: {len(body)} bytes"


def test_p5_21_pdf_admin_success():
    r = requests.get(f"{API}/invoices/{S['session_id']}/pdf", headers=_auth(S["admin_tok"]))
    assert r.status_code == 200, r.text
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 1500


def test_p5_22_pdf_other_advertiser_403():
    r = requests.get(f"{API}/invoices/{S['session_id']}/pdf", headers=_auth(S["adv2_tok"]))
    assert r.status_code == 403, r.status_code


def test_p5_23_pdf_unknown_session_404():
    r = requests.get(f"{API}/invoices/nonexistent-{uuid.uuid4().hex}/pdf",
                     headers=_auth(S["admin_tok"]))
    assert r.status_code == 404, r.status_code


def test_p5_24_pdf_no_auth_401():
    r = requests.get(f"{API}/invoices/{S['session_id']}/pdf")
    assert r.status_code == 401, r.status_code


# ============ Cleanup ============
def test_p5_99_cleanup():
    # remove test campaign + tx + plan if we created one
    async def _cleanup():
        from motor.motor_asyncio import AsyncIOMotorClient
        from bson import ObjectId
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = client[os.environ.get("DB_NAME", "onwheels_media")]
        await db.payment_transactions.delete_many({"session_id": S.get("session_id")})
        if S.get("campaign_id"):
            try:
                await db.campaigns.delete_one({"_id": ObjectId(S["campaign_id"])})
            except Exception:
                pass
        client.close()
    asyncio.new_event_loop().run_until_complete(_cleanup())
