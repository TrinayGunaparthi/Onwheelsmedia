"""Phase 2 backend tests: password reset, driver documents, Stripe checkout.

Extends /app/backend/tests/test_owm_backend.py. Reuses the same BASE_URL and
admin credentials. Prior tests remain untouched.
"""
import os
import re
import time
import uuid
import subprocess
import requests
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onwheelsmedia.com"
ADMIN_PASSWORD = "Admin@12345"

BACKEND_LOG = "/var/log/supervisor/backend.err.log"
BACKEND_OUT_LOG = "/var/log/supervisor/backend.out.log"

STATE = {}


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _tail_logs(pattern, since_marker=None, files=None, lines=800):
    """Search recent backend logs for pattern; returns match text or None."""
    files = files or [BACKEND_LOG, BACKEND_OUT_LOG]
    combined = ""
    for f in files:
        if os.path.exists(f):
            try:
                out = subprocess.check_output(["tail", "-n", str(lines), f], text=True)
                combined += out
            except Exception:
                pass
    if since_marker and since_marker in combined:
        combined = combined.split(since_marker, 1)[1]
    m = re.findall(pattern, combined)
    return m


# ============ Password Reset ============

def test_p2_register_user_for_reset():
    email = f"TEST_reset_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "OldPass1!", "name": "Reset User",
        "role": "advertiser", "company": "Co"
    })
    assert r.status_code == 200, r.text
    STATE["reset_email"] = email
    STATE["reset_old_token"] = r.json()["access_token"]


def test_p2_forgot_password_registered_writes_log_link():
    email = STATE["reset_email"].lower()
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    assert "message" in r.json()
    generic_msg = r.json()["message"]
    STATE["generic_msg"] = generic_msg

    time.sleep(0.5)
    # find reset link in logs
    matches = _tail_logs(rf"Password reset link for {re.escape(email)}: (\S+)")
    assert matches, f"no reset link logged for {email}"
    link = matches[-1]
    assert "token=" in link
    token = link.split("token=", 1)[1]
    STATE["reset_token"] = token


def test_p2_forgot_password_unregistered_no_token_created():
    fake_email = f"TEST_nope_{uuid.uuid4().hex[:8]}@ex.com"
    # count before
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "onwheels_media")

    async def _run():
        c = AsyncIOMotorClient(mongo_url)
        db = c[db_name]
        before = await db.password_reset_tokens.count_documents({"email": fake_email})
        c.close()
        return before

    before = asyncio.get_event_loop().run_until_complete(_run())

    r = requests.post(f"{API}/auth/forgot-password", json={"email": fake_email})
    assert r.status_code == 200
    # response must be identical to registered
    assert r.json()["message"] == STATE.get("generic_msg", r.json()["message"])

    async def _after():
        c = AsyncIOMotorClient(mongo_url)
        db = c[db_name]
        after = await db.password_reset_tokens.count_documents({"email": fake_email})
        c.close()
        return after

    after = asyncio.get_event_loop().run_until_complete(_after())
    assert after == before == 0, "no reset token doc should be created for unregistered email"


def test_p2_forgot_password_rate_limit():
    # unique registered email
    email = f"TEST_rl_{uuid.uuid4().hex[:8]}@ex.com".lower()
    reg = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "OldPass1!", "name": "RL User",
        "role": "advertiser"
    })
    assert reg.status_code == 200

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "onwheels_media")

    responses = []
    for _ in range(6):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        responses.append(r)
    for r in responses:
        assert r.status_code == 200
        assert "message" in r.json()
    # all 6 same generic response
    msgs = {r.json()["message"] for r in responses}
    assert len(msgs) == 1, f"responses must be identical: {msgs}"

    async def _count():
        c = AsyncIOMotorClient(mongo_url)
        db = c[db_name]
        n = await db.password_reset_tokens.count_documents({"email": email})
        c.close()
        return n

    total = asyncio.get_event_loop().run_until_complete(_count())
    assert total == 5, f"expected exactly 5 tokens created (rate-limited), got {total}"


def test_p2_reset_password_bogus_token():
    r = requests.post(f"{API}/auth/reset-password", json={
        "token": "bogus-token-xxx", "password": "NewPass1!"
    })
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "Invalid" in detail or "expired" in detail.lower()


def test_p2_reset_password_success_and_invalidations():
    token = STATE["reset_token"]
    email = STATE["reset_email"]
    new_pw = "NewPass1!"
    r = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": new_pw})
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # same token cannot be reused
    r2 = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": new_pw})
    assert r2.status_code == 400

    # new password login works
    lg = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pw})
    assert lg.status_code == 200, lg.text
    STATE["reset_new_token"] = lg.json()["access_token"]

    # old password fails
    lg_old = requests.post(f"{API}/auth/login", json={"email": email, "password": "OldPass1!"})
    assert lg_old.status_code == 401

    # old JWT invalidated by token_version bump
    me = requests.get(f"{API}/auth/me", headers=_auth(STATE["reset_old_token"]))
    assert me.status_code == 401


# ============ Driver Documents ============

def test_p2_driver_docs_stored_and_returned():
    # create fresh driver
    email = f"TEST_drvdoc_{uuid.uuid4().hex[:8]}@ex.com"
    reg = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Doc Driver", "role": "driver"
    })
    assert reg.status_code == 200
    tok = reg.json()["access_token"]

    docs = [
        {"type": "rc_book", "name": "rc.pdf", "url": "/api/files/x/rc.pdf", "path": "x/rc.pdf"},
        {"type": "driver_license", "name": "dl.jpg", "url": "/api/files/x/dl.jpg", "path": "x/dl.jpg"},
        {"type": "insurance", "name": "ins.pdf", "url": "/api/files/x/ins.pdf", "path": "x/ins.pdf"},
        {"type": "profile_photo", "name": "me.jpg", "url": "/api/files/x/me.jpg", "path": "x/me.jpg"},
    ]
    payload = {
        "full_name": "Doc Driver", "phone": "9000000000", "address": "1 Rd",
        "city": "Blr", "state": "KA", "vehicle_reg_no": f"KA-99-{uuid.uuid4().hex[:4].upper()}",
        "vehicle_type": "Auto", "manufacturer": "Bajaj", "model": "RE",
        "year": 2023, "color": "Yellow", "operating_area": "HSR",
        "documents": docs,
    }
    r = requests.post(f"{API}/drivers", json=payload, headers=_auth(tok))
    assert r.status_code == 200, r.text
    driver_id = r.json()["id"]

    me = requests.get(f"{API}/drivers/me", headers=_auth(tok))
    assert me.status_code == 200
    drv = me.json()["driver"]
    assert isinstance(drv.get("documents"), list)
    assert len(drv["documents"]) == 4
    types = {d["type"] for d in drv["documents"]}
    assert types == {"rc_book", "driver_license", "insurance", "profile_photo"}

    # admin list must also carry documents
    lg = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    admin_tok = lg.json()["access_token"]
    lst = requests.get(f"{API}/admin/drivers", headers=_auth(admin_tok))
    assert lst.status_code == 200
    found = next((d for d in lst.json() if d["id"] == driver_id), None)
    assert found is not None
    assert isinstance(found.get("documents"), list) and len(found["documents"]) == 4


# ============ Stripe Checkout ============

def _get_advertiser_token():
    if "adv_tok" in STATE:
        return STATE["adv_tok"]
    email = f"TEST_pay_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Pay Adv", "role": "advertiser"
    })
    assert r.status_code == 200
    STATE["adv_tok"] = r.json()["access_token"]
    STATE["adv_email"] = email
    return STATE["adv_tok"]


def test_p2_payments_checkout_unauth_401():
    r = requests.post(f"{API}/payments/checkout", json={"amount": 10, "origin_url": BASE_URL})
    assert r.status_code == 401


def test_p2_payments_checkout_admin_403():
    lg = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    admin_tok = lg.json()["access_token"]
    r = requests.post(f"{API}/payments/checkout",
                      json={"amount": 10, "origin_url": BASE_URL},
                      headers=_auth(admin_tok))
    assert r.status_code == 403


def test_p2_payments_checkout_driver_403():
    email = f"TEST_drvpay_{uuid.uuid4().hex[:8]}@ex.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "D", "role": "driver"
    })
    tok = r.json()["access_token"]
    r2 = requests.post(f"{API}/payments/checkout",
                       json={"amount": 10, "origin_url": BASE_URL},
                       headers=_auth(tok))
    assert r2.status_code == 403


def test_p2_payments_checkout_success():
    tok = _get_advertiser_token()
    r = requests.post(f"{API}/payments/checkout",
                      json={"amount": 25.5, "origin_url": BASE_URL},
                      headers=_auth(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "checkout_url" in data and data["checkout_url"].startswith("http")
    assert "session_id" in data and data["session_id"]
    STATE["session_id"] = data["session_id"]

    # verify DB record
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "onwheels_media")

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        db = c[db_name]
        rec = await db.payment_transactions.find_one({"session_id": data["session_id"]})
        c.close()
        return rec

    rec = asyncio.get_event_loop().run_until_complete(_check())
    assert rec is not None
    assert rec["status"] == "initiated"
    assert rec["payment_status"] == "pending"
    assert float(rec["amount"]) == 25.5


def test_p2_payments_status_unauth_allowed():
    sid = STATE.get("session_id")
    assert sid, "prior test must run"
    r = requests.get(f"{API}/payments/status/{sid}")
    assert r.status_code == 200
    data = r.json()
    # only these fields should be returned
    assert set(data.keys()) <= {"session_id", "status", "payment_status", "amount"}
    assert data["session_id"] == sid


def test_p2_webhook_stripe_no_signature_no_500():
    r = requests.post(f"{API}/webhook/stripe", data=b"{}",
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "ok" in j
    assert isinstance(j["ok"], bool)


# ============ Regression ============

def test_p2_regression_admin_login_still_works():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    tok = r.json()["access_token"]
    for path in ("/admin/drivers", "/admin/ads", "/admin/stats", "/admin/campaigns"):
        rr = requests.get(f"{API}{path}", headers=_auth(tok))
        assert rr.status_code == 200, f"{path} -> {rr.status_code}"
