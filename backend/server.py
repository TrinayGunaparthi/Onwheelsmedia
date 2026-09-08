from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
import bcrypt
import jwt
import requests as http_requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form, Query
from fastapi.responses import Response as FastAPIResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

# ---------- setup ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("owm")

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = "HS256"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="On Wheels Media API")
api = APIRouter(prefix="/api")

# ---------- object storage ----------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = "onwheels-media"
_storage_key: Optional[str] = None

def init_storage(force: bool = False) -> Optional[str]:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    if not EMERGENT_KEY:
        logger.warning("EMERGENT_LLM_KEY not set - storage disabled")
        return None
    try:
        r = http_requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        logger.info("Object storage initialized")
        return _storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> Dict[str, Any]:
    key = init_storage()
    if not key:
        raise HTTPException(500, "Storage not available")
    r = http_requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()

def get_object(path: str):
    key = init_storage()
    if not key:
        raise HTTPException(500, "Storage not available")
    r = http_requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")

# ---------- auth helpers ----------
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def create_access_token(user_id: str, email: str, role: str, ver: int = 0) -> str:
    payload = {"sub": user_id, "email": email, "role": role, "ver": ver,
               "exp": datetime.now(timezone.utc) + timedelta(hours=12), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str, ver: int = 0) -> str:
    payload = {"sub": user_id, "ver": ver,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(401, "User not found")
        if payload.get("ver", 0) != user.get("token_version", 0):
            raise HTTPException(401, "Session expired")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

def require_role(*roles):
    async def _guard(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(403, f"Requires role: {roles}")
        return user
    return _guard

def set_auth_cookies(resp: Response, access: str, refresh: str):
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    resp.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=604800, path="/")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(400, "Invalid id")

def serialize(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.pop("password_hash", None)
    return doc

def serialize_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize(d) for d in docs]

async def audit(user: Dict, action: str, entity: str, entity_id: str = "", meta: Dict = None):
    await db.audit_logs.insert_one({
        "user_id": user.get("id"), "user_email": user.get("email"), "role": user.get("role"),
        "action": action, "entity": entity, "entity_id": entity_id, "meta": meta or {}, "at": now_iso()
    })

# ---------- schemas ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    role: str = Field(pattern="^(advertiser|driver)$")
    phone: Optional[str] = None
    company: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class DriverIn(BaseModel):
    full_name: str
    phone: str
    address: str
    city: str
    state: str
    profile_photo_url: Optional[str] = None
    vehicle_reg_no: str
    vehicle_type: str
    manufacturer: str
    model: str
    year: int
    color: str
    operating_area: str
    preferred_routes: Optional[str] = ""
    documents: Optional[List[Dict[str, str]]] = None  # [{type, name, url, path}]

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=6)

class CheckoutIn(BaseModel):
    amount: float = Field(gt=0, le=1000000)
    origin_url: str
    campaign_id: Optional[str] = None

class VehicleUpdate(BaseModel):
    status: Optional[str] = None

class AdvertiserProfileIn(BaseModel):
    company: str
    contact_name: str
    phone: str
    website: Optional[str] = ""
    address: Optional[str] = ""

class AdInput(BaseModel):
    name: str
    description: Optional[str] = ""
    duration_seconds: int = 15
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    file_url: str
    file_type: str  # image|video
    file_path: Optional[str] = ""

class ApprovalIn(BaseModel):
    status: str
    reason: Optional[str] = ""

class CampaignIn(BaseModel):
    name: str
    ad_id: str
    start_date: str
    end_date: str
    start_time: Optional[str] = "00:00"
    end_time: Optional[str] = "23:59"
    budget: float = 0
    target_locations: List[str] = []
    target_devices: List[str] = []
    frequency: int = 3  # times per hour
    objective: str = "Awareness"

class DeviceRegisterIn(BaseModel):
    vehicle_id: str
    android_info: Optional[str] = ""
    app_version: Optional[str] = ""
    screen_info: Optional[str] = ""
    sim_info: Optional[str] = ""

class PlaylistIn(BaseModel):
    name: str
    device_ids: List[str] = []
    items: List[Dict[str, Any]] = []  # {type, ref_id, duration, order}

class NewsIn(BaseModel):
    headline: str
    description: str
    image_url: Optional[str] = ""
    location: Optional[str] = ""
    duration_seconds: int = 10
    active: bool = True

class WeatherConfigIn(BaseModel):
    location: str
    device_ids: List[str] = []
    frequency: int = 4
    duration_seconds: int = 8

class QrCampaignIn(BaseModel):
    name: str
    target_url: str
    campaign_type: str = "Website"
    device_ids: List[str] = []

class PlaybackEventIn(BaseModel):
    device_id: str
    ad_id: Optional[str] = None
    campaign_id: Optional[str] = None
    news_id: Optional[str] = None
    completed: bool = True
    duration_played: int = 0
    timestamp: Optional[str] = None

class DeviceHeartbeatIn(BaseModel):
    device_id: str
    battery: Optional[int] = None
    storage_mb: Optional[int] = None
    network: Optional[str] = ""
    app_version: Optional[str] = ""

# ---------- auth routes ----------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "phone": payload.phone or "",
        "company": payload.company or "",
        "token_version": 0,
        "status": "active",
        "created_at": now_iso(),
    }
    res = await db.users.insert_one(user)
    uid = str(res.inserted_id)
    access = create_access_token(uid, email, payload.role)
    refresh = create_refresh_token(uid)
    set_auth_cookies(response, access, refresh)
    # If advertiser, seed advertiser profile
    if payload.role == "advertiser":
        await db.advertisers.insert_one({
            "user_id": uid, "company": payload.company or payload.name,
            "contact_name": payload.name, "phone": payload.phone or "",
            "website": "", "address": "", "status": "active", "created_at": now_iso()
        })
    return {"id": uid, "email": email, "name": payload.name, "role": payload.role, "access_token": access}

@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    uid = str(user["_id"])
    ver = user.get("token_version", 0)
    access = create_access_token(uid, email, user["role"], ver)
    refresh = create_refresh_token(uid, ver)
    set_auth_cookies(response, access, refresh)
    return {"id": uid, "email": email, "name": user.get("name"), "role": user["role"], "access_token": access}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

# ---------- password reset ----------
import hashlib
import secrets as _secrets

FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")

@api.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordIn):
    email = payload.email.lower()
    now = datetime.now(timezone.utc)
    # rate limit by email (5 per 15 min)
    recent = await db.password_reset_requests.count_documents({"email": email, "created_at": {"$gte": (now - timedelta(minutes=15)).isoformat()}})
    generic = {"message": "If that email is registered, a reset link has been sent."}
    await db.password_reset_requests.insert_one({"email": email, "created_at": now.isoformat()})
    if recent >= 5:
        return generic
    user = await db.users.find_one({"email": email})
    if not user:
        return generic
    token = _secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.password_reset_tokens.insert_one({
        "token_hash": token_hash, "user_id": str(user["_id"]), "email": email,
        "expires_at": (now + timedelta(hours=1)).isoformat(), "used": False
    })
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    logger.info(f"Password reset link for {email}: {link}")
    return generic

@api.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordIn):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    rec = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": token_hash, "used": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True}}
    )
    if not rec:
        raise HTTPException(400, "Invalid or expired reset link")
    await db.users.update_one(
        {"_id": ObjectId(rec["user_id"])},
        {"$set": {"password_hash": hash_password(payload.password)}, "$inc": {"token_version": 1}}
    )
    await db.password_reset_tokens.delete_many({"user_id": rec["user_id"], "used": False})
    await db.login_attempts.delete_many({"email": rec["email"]})
    return {"ok": True}

# ---------- stripe checkout (Flow B, uses emergentintegrations) ----------
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")

try:
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    _STRIPE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Stripe integration unavailable: {e}")
    _STRIPE_AVAILABLE = False

@api.post("/payments/checkout")
async def create_checkout(payload: CheckoutIn, request: Request, user=Depends(require_role("advertiser"))):
    if not _STRIPE_AVAILABLE:
        raise HTTPException(500, "Stripe integration not available")
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    origin = payload.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=float(payload.amount), currency="usd",
        success_url=f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/payment/cancel",
        metadata={"user_id": user["id"], "campaign_id": payload.campaign_id or ""}
    )
    session = await stripe_checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "campaign_id": payload.campaign_id or "",
        "amount": float(payload.amount), "currency": "usd",
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso()
    })
    return {"checkout_url": session.url, "session_id": session.session_id}

@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    record = await db.payment_transactions.find_one({"session_id": session_id})
    if not record:
        raise HTTPException(404, "Transaction not found")
    if record.get("payment_status") != "paid" and _STRIPE_AVAILABLE:
        try:
            sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="unused")
            status = await sc.get_checkout_status(session_id)
            if status.payment_status == "paid":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}}
                )
                # top up campaign budget or create invoice
                if record.get("campaign_id"):
                    await db.invoices.insert_one({
                        "advertiser_id": record["user_id"], "campaign_id": record["campaign_id"],
                        "amount": record["amount"], "currency": "usd", "status": "Paid",
                        "session_id": session_id, "created_at": now_iso()
                    })
                record = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception as e:
            logger.warning(f"stripe status check failed: {e}")
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"], "amount": record.get("amount")}

@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    if not _STRIPE_AVAILABLE:
        return {"ok": False}
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="unused")
        resp = await sc.handle_webhook(body, sig)
        if resp.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"session_id": resp.session_id, "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}}
            )
    except Exception as e:
        logger.error(f"webhook error: {e}")
    return {"ok": True}


# ---------- uploads ----------
@api.post("/uploads")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = (file.filename or "bin").rsplit(".", 1)[-1].lower()
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{user['id']}/{file_id}.{ext}"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    result = put_object(path, data, content_type)
    await db.files.insert_one({
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "user_id": user["id"],
        "is_deleted": False,
        "created_at": now_iso()
    })
    file_type = "image" if content_type.startswith("image/") else ("video" if content_type.startswith("video/") else "other")
    return {"path": result["path"], "url": f"/api/files/{result['path']}", "content_type": content_type, "file_type": file_type, "size": result.get("size", len(data))}

@api.get("/files/{path:path}")
async def get_file(path: str):
    # Public serve — files reachable via API. Access control could be added later.
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(404, "File not found")
    data, ct = get_object(path)
    return FastAPIResponse(content=data, media_type=record.get("content_type", ct))

# ---------- drivers ----------
@api.post("/drivers")
async def create_driver(payload: DriverIn, user=Depends(require_role("driver"))):
    existing = await db.drivers.find_one({"user_id": user["id"]})
    payload_dict = payload.model_dump()
    docs_list = payload_dict.pop("documents", None) or []
    doc = {
        "user_id": user["id"],
        "email": user["email"],
        **payload_dict,
        "status": "Pending",
        "documents": docs_list,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if existing:
        await db.drivers.update_one({"_id": existing["_id"]}, {"$set": doc})
        driver_id = str(existing["_id"])
    else:
        res = await db.drivers.insert_one(doc)
        driver_id = str(res.inserted_id)
        # Create vehicle
        await db.vehicles.insert_one({
            "driver_id": driver_id,
            "reg_no": payload.vehicle_reg_no,
            "vehicle_type": payload.vehicle_type,
            "manufacturer": payload.manufacturer,
            "model": payload.model,
            "year": payload.year,
            "color": payload.color,
            "operating_area": payload.operating_area,
            "status": "Pending",
            "created_at": now_iso()
        })
    await db.notifications.insert_one({"user_id": user["id"], "type": "driver_registration", "message": "Registration received. Under review.", "read": False, "at": now_iso()})
    return {"id": driver_id, "status": "Pending"}

@api.get("/drivers/me")
async def get_my_driver(user=Depends(require_role("driver"))):
    d = await db.drivers.find_one({"user_id": user["id"]})
    if not d:
        return None
    v = await db.vehicles.find_one({"driver_id": str(d["_id"])})
    return {"driver": serialize(d), "vehicle": serialize(v)}

@api.get("/admin/drivers")
async def list_drivers(user=Depends(require_role("admin"))):
    docs = await db.drivers.find().sort("created_at", -1).to_list(1000)
    return serialize_list(docs)

@api.patch("/admin/drivers/{driver_id}")
async def update_driver_status(driver_id: str, payload: ApprovalIn, user=Depends(require_role("admin"))):
    result = await db.drivers.update_one({"_id": oid(driver_id)}, {"$set": {"status": payload.status, "reason": payload.reason, "updated_at": now_iso()}})
    if result.matched_count == 0:
        raise HTTPException(404, "Driver not found")
    d = await db.drivers.find_one({"_id": oid(driver_id)})
    # Also update vehicle
    await db.vehicles.update_many({"driver_id": driver_id}, {"$set": {"status": payload.status}})
    await db.notifications.insert_one({"user_id": d["user_id"], "type": "driver_status", "message": f"Driver status: {payload.status}", "read": False, "at": now_iso()})
    await audit(user, "update_driver_status", "driver", driver_id, {"status": payload.status})
    return serialize(d)

# ---------- vehicles ----------
@api.get("/admin/vehicles")
async def list_vehicles(user=Depends(require_role("admin"))):
    docs = await db.vehicles.find().sort("created_at", -1).to_list(1000)
    # attach driver info
    out = []
    for v in docs:
        item = serialize(v)
        drv = await db.drivers.find_one({"_id": oid(v["driver_id"])}) if v.get("driver_id") else None
        item["driver"] = serialize(drv)
        dev = await db.devices.find_one({"vehicle_id": item["id"]})
        item["device"] = serialize(dev)
        out.append(item)
    return out

@api.patch("/admin/vehicles/{vid}")
async def update_vehicle(vid: str, payload: VehicleUpdate, user=Depends(require_role("admin"))):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await db.vehicles.update_one({"_id": oid(vid)}, {"$set": updates})
    v = await db.vehicles.find_one({"_id": oid(vid)})
    return serialize(v)

# ---------- devices ----------
async def next_device_id() -> str:
    counter = await db.counters.find_one_and_update({"_id": "device"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    seq = counter["seq"] if counter else 1
    return f"OWM-AUTO-{seq:06d}"

@api.post("/devices/register")
async def register_device(payload: DeviceRegisterIn, user=Depends(require_role("driver"))):
    v = await db.vehicles.find_one({"_id": oid(payload.vehicle_id)})
    if not v:
        raise HTTPException(404, "Vehicle not found")
    device_code = await next_device_id()
    activation_code = str(uuid.uuid4())[:8].upper()
    doc = {
        "device_code": device_code,
        "vehicle_id": payload.vehicle_id,
        "driver_id": v["driver_id"],
        "activation_code": activation_code,
        "status": "Pending",
        "android_info": payload.android_info,
        "app_version": payload.app_version,
        "screen_info": payload.screen_info,
        "sim_info": payload.sim_info,
        "last_online": None,
        "battery": None,
        "storage_mb": None,
        "network": "",
        "created_at": now_iso(),
    }
    res = await db.devices.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc

@api.get("/admin/devices")
async def list_devices(user=Depends(require_role("admin"))):
    docs = await db.devices.find().sort("created_at", -1).to_list(1000)
    out = []
    for d in docs:
        item = serialize(d)
        v = await db.vehicles.find_one({"_id": oid(d["vehicle_id"])}) if d.get("vehicle_id") else None
        item["vehicle"] = serialize(v)
        out.append(item)
    return out

@api.patch("/admin/devices/{did}")
async def update_device(did: str, payload: ApprovalIn, user=Depends(require_role("admin"))):
    await db.devices.update_one({"_id": oid(did)}, {"$set": {"status": payload.status, "reason": payload.reason or ""}})
    d = await db.devices.find_one({"_id": oid(did)})
    await audit(user, "update_device_status", "device", did, {"status": payload.status})
    return serialize(d)

@api.get("/devices/mine")
async def my_devices(user=Depends(require_role("driver"))):
    docs = await db.devices.find({"driver_id": {"$in": [str(v["_id"]) async for v in db.vehicles.find({"driver_id": {"$exists": True}}) if False]}}).to_list(0)  # placeholder
    # simpler: fetch by driver from drivers collection
    drv = await db.drivers.find_one({"user_id": user["id"]})
    if not drv:
        return []
    docs = await db.devices.find({"driver_id": str(drv["_id"])}).to_list(100)
    return serialize_list(docs)

# ---------- device runtime (no admin auth - device auth by code) ----------
@api.post("/player/activate")
async def player_activate(body: Dict[str, str]):
    code = body.get("activation_code", "").upper()
    dev = await db.devices.find_one({"activation_code": code})
    if not dev:
        raise HTTPException(404, "Invalid activation code")
    if dev.get("status") not in ("Approved", "Online", "Offline"):
        return {"status": dev.get("status", "Pending"), "device_code": dev.get("device_code"), "approved": False}
    # Issue device token
    token = jwt.encode({"device_id": str(dev["_id"]), "type": "device", "exp": datetime.now(timezone.utc) + timedelta(days=365)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"status": dev["status"], "device_code": dev["device_code"], "approved": True, "device_token": token, "device_id": str(dev["_id"])}

async def get_current_device(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing device token")
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "device":
            raise HTTPException(401, "Bad token type")
        dev = await db.devices.find_one({"_id": oid(payload["device_id"])})
        if not dev:
            raise HTTPException(401, "Device not found")
        return dev
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid device token")

@api.post("/player/heartbeat")
async def heartbeat(payload: DeviceHeartbeatIn, dev=Depends(get_current_device)):
    await db.devices.update_one({"_id": dev["_id"]}, {"$set": {
        "last_online": now_iso(), "status": "Online",
        "battery": payload.battery, "storage_mb": payload.storage_mb,
        "network": payload.network or "", "app_version": payload.app_version or ""
    }})
    return {"ok": True, "server_time": now_iso()}

@api.get("/player/playlist")
async def player_playlist(request: Request, dev=Depends(get_current_device)):
    device_id = str(dev["_id"])
    # Extract audience context from query params (sent by player based on latest audience sample)
    aud_top_age = request.query_params.get("age_group", "")  # e.g. "25-34"
    aud_top_gender = request.query_params.get("gender", "")  # "male"|"female"
    try: aud_attention = int(request.query_params.get("attention", "0"))
    except (ValueError, TypeError): aud_attention = 0
    try: aud_viewers = int(request.query_params.get("viewers", "0"))
    except (ValueError, TypeError): aud_viewers = 0
    now_hour = datetime.now(timezone.utc).hour
    time_slot = "morning" if 5<=now_hour<12 else "afternoon" if 12<=now_hour<17 else "evening" if 17<=now_hour<21 else "night"

    today = datetime.now(timezone.utc).date().isoformat()
    campaigns = await db.campaigns.find({
        "status": {"$in": ["Active", "Scheduled"]},
        "$or": [{"target_devices": device_id}, {"target_devices": []}],
        "start_date": {"$lte": today},
        "end_date": {"$gte": today},
    }).to_list(200)

    def score_campaign(c):
        """Score campaign against audience context. Higher = better match."""
        rules = c.get("targeting_rules", {}) or {}
        score = 1.0  # base
        # time of day
        allowed_slots = rules.get("time_slots") or []
        if allowed_slots:
            score = score * (2.0 if time_slot in allowed_slots else 0.3)
        # age group
        target_ages = rules.get("age_groups") or []
        if target_ages and aud_top_age:
            score = score * (2.5 if aud_top_age in target_ages else 0.4)
        # gender
        target_genders = rules.get("genders") or []
        if target_genders and aud_top_gender:
            score = score * (2.0 if aud_top_gender in target_genders else 0.5)
        # min attention
        min_att = rules.get("min_attention", 0)
        if min_att and aud_attention < min_att:
            score = score * 0.3
        # min viewers
        min_v = rules.get("min_viewers", 0)
        if min_v and aud_viewers < min_v:
            score = score * 0.4
        return score

    scored = []
    for c in campaigns:
        ad = await db.ads.find_one({"_id": oid(c["ad_id"])}) if c.get("ad_id") else None
        if ad and ad.get("status") == "Approved":
            s = score_campaign(c)
            scored.append((s, c, ad))
    # Sort desc; if audience unavailable, order stays base=1.0 for all (natural)
    scored.sort(key=lambda x: x[0], reverse=True)
    items = []
    for s, c, ad in scored:
        item = {
            "type": "ad", "id": str(ad["_id"]), "campaign_id": str(c["_id"]),
            "name": ad["name"], "file_url": ad["file_url"], "file_type": ad["file_type"],
            "duration": ad.get("duration_seconds", 15),
            "targeting_score": round(s, 2),
        }
        # Interactive layer
        inter = c.get("interactive") or {}
        if inter.get("type") == "game" and inter.get("game_id"):
            item["interactive"] = {"type": "game", "game_id": inter["game_id"]}
        elif inter.get("type") == "qr" and inter.get("qr_id"):
            item["interactive"] = {"type": "qr", "qr_id": inter["qr_id"]}
        elif inter.get("type") == "coupon" and inter.get("coupon_code"):
            item["interactive"] = {"type": "coupon", "code": inter["coupon_code"]}
        items.append(item)
    # Active news
    news_list = await db.news.find({"active": True}).sort("created_at", -1).to_list(10)
    for n in news_list:
        items.append({"type": "news", "id": str(n["_id"]), "headline": n["headline"], "description": n["description"], "image_url": n.get("image_url", ""), "duration": n.get("duration_seconds", 10)})
    # QR campaigns for this device
    qrs = await db.qr_campaigns.find({"$or": [{"device_ids": device_id}, {"device_ids": []}], "active": True}).to_list(20)
    for q in qrs:
        items.append({"type": "qr", "id": str(q["_id"]), "name": q["name"], "target_url": q["target_url"], "duration": 8})
    # Weather config
    wcfg = await db.weather_configs.find_one({"$or": [{"device_ids": device_id}, {"device_ids": []}]})
    weather = None
    if wcfg:
        weather = await fetch_weather(wcfg["location"])
        items.append({"type": "weather", "location": wcfg["location"], "data": weather, "duration": wcfg.get("duration_seconds", 8)})
    return {"device_code": dev["device_code"], "items": items, "generated_at": now_iso(), "audience_context": {"age": aud_top_age, "gender": aud_top_gender, "attention": aud_attention, "viewers": aud_viewers, "time_slot": time_slot}}

async def fetch_weather(location: str) -> Dict[str, Any]:
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key:
        return {"location": location, "temp_c": 28, "condition": "Partly Cloudy", "icon": "cloud", "mocked": True}
    try:
        r = http_requests.get("https://api.openweathermap.org/data/2.5/weather", params={"q": location, "appid": key, "units": "metric"}, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {
            "location": d.get("name", location), "temp_c": round(d["main"]["temp"]),
            "condition": d["weather"][0]["main"], "description": d["weather"][0]["description"],
            "icon": d["weather"][0]["icon"], "mocked": False
        }
    except Exception as e:
        logger.warning(f"weather fetch failed: {e}")
        return {"location": location, "temp_c": 28, "condition": "Partly Cloudy", "icon": "cloud", "mocked": True}

@api.post("/player/playback")
async def report_playback(payload: PlaybackEventIn, dev=Depends(get_current_device)):
    doc = payload.model_dump()
    doc["device_id"] = str(dev["_id"])
    doc["timestamp"] = payload.timestamp or now_iso()
    await db.playback_events.insert_one(doc)
    return {"ok": True}

@api.post("/player/playback/batch")
async def report_playback_batch(events: List[PlaybackEventIn], dev=Depends(get_current_device)):
    if not events:
        return {"ok": True, "count": 0}
    docs = []
    for e in events:
        d = e.model_dump()
        d["device_id"] = str(dev["_id"])
        d["timestamp"] = e.timestamp or now_iso()
        docs.append(d)
    await db.playback_events.insert_many(docs)
    return {"ok": True, "count": len(docs)}

# ---------- ads ----------
@api.post("/ads")
async def create_ad(payload: AdInput, user=Depends(require_role("advertiser"))):
    doc = {
        **payload.model_dump(),
        "advertiser_id": user["id"],
        "advertiser_email": user["email"],
        "status": "Submitted",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    res = await db.ads.insert_one(doc)
    await db.notifications.insert_one({"user_id": user["id"], "type": "ad_created", "message": f"Ad '{payload.name}' submitted for review.", "read": False, "at": now_iso()})
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc

@api.get("/ads")
async def list_my_ads(user=Depends(require_role("advertiser"))):
    docs = await db.ads.find({"advertiser_id": user["id"]}).sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.get("/admin/ads")
async def admin_list_ads(user=Depends(require_role("admin"))):
    docs = await db.ads.find().sort("created_at", -1).to_list(500)
    return serialize_list(docs)

@api.patch("/admin/ads/{ad_id}")
async def admin_review_ad(ad_id: str, payload: ApprovalIn, user=Depends(require_role("admin"))):
    result = await db.ads.update_one({"_id": oid(ad_id)}, {"$set": {"status": payload.status, "review_reason": payload.reason or "", "reviewed_at": now_iso()}})
    if result.matched_count == 0:
        raise HTTPException(404, "Ad not found")
    ad = await db.ads.find_one({"_id": oid(ad_id)})
    await db.notifications.insert_one({"user_id": ad["advertiser_id"], "type": "ad_review", "message": f"Ad '{ad['name']}' -> {payload.status}", "read": False, "at": now_iso()})
    await audit(user, "review_ad", "ad", ad_id, {"status": payload.status})
    return serialize(ad)

# ---------- campaigns ----------
@api.post("/campaigns")
async def create_campaign(payload: CampaignIn, user=Depends(require_role("advertiser"))):
    ad = await db.ads.find_one({"_id": oid(payload.ad_id), "advertiser_id": user["id"]})
    if not ad:
        raise HTTPException(404, "Ad not found")
    doc = {**payload.model_dump(), "advertiser_id": user["id"], "status": "Scheduled" if ad.get("status") == "Approved" else "Draft", "created_at": now_iso()}
    res = await db.campaigns.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/campaigns")
async def list_my_campaigns(user=Depends(require_role("advertiser"))):
    docs = await db.campaigns.find({"advertiser_id": user["id"]}).sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.get("/admin/campaigns")
async def admin_list_campaigns(user=Depends(require_role("admin"))):
    docs = await db.campaigns.find().sort("created_at", -1).to_list(500)
    return serialize_list(docs)

@api.patch("/admin/campaigns/{cid}")
async def admin_update_campaign(cid: str, payload: Dict[str, Any], user=Depends(require_role("admin"))):
    allowed = {k: payload[k] for k in ("status", "target_devices", "target_locations", "frequency") if k in payload}
    await db.campaigns.update_one({"_id": oid(cid)}, {"$set": allowed})
    c = await db.campaigns.find_one({"_id": oid(cid)})
    await audit(user, "update_campaign", "campaign", cid, allowed)
    return serialize(c)

# ---------- playlists ----------
@api.post("/admin/playlists")
async def create_playlist(payload: PlaylistIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.playlists.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/admin/playlists")
async def list_playlists(user=Depends(require_role("admin"))):
    docs = await db.playlists.find().sort("created_at", -1).to_list(100)
    return serialize_list(docs)

# ---------- news ----------
@api.post("/admin/news")
async def create_news(payload: NewsIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.news.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/admin/news")
async def list_news(user=Depends(require_role("admin"))):
    docs = await db.news.find().sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.delete("/admin/news/{nid}")
async def delete_news(nid: str, user=Depends(require_role("admin"))):
    await db.news.delete_one({"_id": oid(nid)})
    return {"ok": True}

# ---------- weather ----------
@api.post("/admin/weather")
async def create_weather(payload: WeatherConfigIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.weather_configs.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/admin/weather")
async def list_weather(user=Depends(require_role("admin"))):
    docs = await db.weather_configs.find().to_list(100)
    return serialize_list(docs)

# ---------- QR campaigns ----------
@api.post("/admin/qr")
async def create_qr(payload: QrCampaignIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "active": True, "impressions": 0, "scans": 0, "created_at": now_iso()}
    res = await db.qr_campaigns.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/admin/qr")
async def list_qr(user=Depends(require_role("admin"))):
    docs = await db.qr_campaigns.find().sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.get("/qr/{qr_id}")
async def qr_redirect(qr_id: str, device_id: Optional[str] = None):
    q = await db.qr_campaigns.find_one({"_id": oid(qr_id)})
    if not q:
        raise HTTPException(404, "QR not found")
    await db.qr_campaigns.update_one({"_id": oid(qr_id)}, {"$inc": {"scans": 1}})
    await db.qr_scans.insert_one({"qr_id": qr_id, "device_id": device_id or "", "at": now_iso()})
    return {"target_url": q["target_url"]}

# ---------- notifications ----------
@api.get("/notifications")
async def my_notifications(user=Depends(get_current_user)):
    docs = await db.notifications.find({"user_id": user["id"]}).sort("at", -1).to_list(100)
    return serialize_list(docs)

@api.post("/notifications/{nid}/read")
async def mark_read(nid: str, user=Depends(get_current_user)):
    await db.notifications.update_one({"_id": oid(nid), "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}

# ---------- reports & dashboard stats ----------
@api.get("/admin/stats")
async def admin_stats(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    online_cutoff = (now - timedelta(minutes=5)).isoformat()
    counts = {
        "drivers_total": await db.drivers.count_documents({}),
        "drivers_pending": await db.drivers.count_documents({"status": "Pending"}),
        "vehicles_total": await db.vehicles.count_documents({}),
        "devices_total": await db.devices.count_documents({}),
        "devices_online": await db.devices.count_documents({"last_online": {"$gte": online_cutoff}}),
        "advertisers_total": await db.users.count_documents({"role": "advertiser"}),
        "ads_total": await db.ads.count_documents({}),
        "ads_pending": await db.ads.count_documents({"status": {"$in": ["Submitted", "Under Review"]}}),
        "campaigns_active": await db.campaigns.count_documents({"status": "Active"}),
        "plays_today": await db.playback_events.count_documents({"timestamp": {"$gte": now.date().isoformat()}}),
    }
    return counts

@api.get("/admin/reports/plays")
async def plays_report(days: int = 7, user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc).date()
    result = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).isoformat()
        next_day = (now - timedelta(days=i - 1)).isoformat()
        count = await db.playback_events.count_documents({"timestamp": {"$gte": day, "$lt": next_day}})
        result.append({"date": day, "plays": count})
    return result

@api.get("/advertiser/reports")
async def advertiser_reports(user=Depends(require_role("advertiser"))):
    ads = await db.ads.find({"advertiser_id": user["id"]}).to_list(200)
    ad_ids = [str(a["_id"]) for a in ads]
    total_plays = await db.playback_events.count_documents({"ad_id": {"$in": ad_ids}})
    campaigns = await db.campaigns.find({"advertiser_id": user["id"]}).to_list(200)
    per_campaign = []
    for c in campaigns:
        cnt = await db.playback_events.count_documents({"campaign_id": str(c["_id"])})
        per_campaign.append({"id": str(c["_id"]), "name": c["name"], "plays": cnt})
    # plays by day
    now = datetime.now(timezone.utc).date()
    by_day = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).isoformat()
        next_day = (now - timedelta(days=i - 1)).isoformat()
        count = await db.playback_events.count_documents({"ad_id": {"$in": ad_ids}, "timestamp": {"$gte": day, "$lt": next_day}})
        by_day.append({"date": day, "plays": count})
    return {"total_plays": total_plays, "per_campaign": per_campaign, "by_day": by_day, "ads_count": len(ads), "campaigns_count": len(campaigns)}

# ---------- payments (records only, Stripe modular) ----------
@api.post("/payments/invoice")
async def create_invoice(payload: Dict[str, Any], user=Depends(require_role("advertiser"))):
    amount = float(payload.get("amount", 0))
    campaign_id = payload.get("campaign_id", "")
    doc = {"advertiser_id": user["id"], "campaign_id": campaign_id, "amount": amount, "currency": "INR", "status": "Pending", "created_at": now_iso()}
    res = await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.get("/payments/invoices")
async def my_invoices(user=Depends(require_role("advertiser"))):
    docs = await db.invoices.find({"advertiser_id": user["id"]}).sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.get("/admin/payments/invoices")
async def admin_invoices(user=Depends(require_role("admin"))):
    docs = await db.invoices.find().sort("created_at", -1).to_list(500)
    return serialize_list(docs)

# ---------- audit logs ----------
@api.get("/admin/audit")
async def audit_logs(user=Depends(require_role("admin"))):
    docs = await db.audit_logs.find().sort("at", -1).limit(200).to_list(200)
    return serialize_list(docs)

# ---------- admin advertisers list ----------
@api.get("/admin/advertisers")
async def list_advertisers(user=Depends(require_role("admin"))):
    docs = await db.users.find({"role": "advertiser"}).sort("created_at", -1).to_list(500)
    out = []
    for u in docs:
        item = serialize(u)
        item.pop("password_hash", None)
        prof = await db.advertisers.find_one({"user_id": item["id"]})
        item["profile"] = serialize(prof)
        out.append(item)
    return out

# ---------- startup ----------
@app.on_event("startup")
async def startup():
    # Indexes
    try:
        await db.users.create_index("email", unique=True)
        await db.devices.create_index("device_code", unique=True)
        await db.devices.create_index("activation_code", unique=True)
        await db.playback_events.create_index([("device_id", 1), ("timestamp", -1)])
        await db.playback_events.create_index("ad_id")
        await db.playback_events.create_index("campaign_id")
        await db.notifications.create_index([("user_id", 1), ("at", -1)])
        await db.password_reset_tokens.create_index("token_hash", unique=True)
        await db.password_reset_requests.create_index("email")
    except Exception as e:
        logger.warning(f"index setup: {e}")
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@onwheelsmedia.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email, "password_hash": hash_password(admin_password),
            "name": "Super Admin", "role": "admin", "token_version": 0, "status": "active",
            "created_at": now_iso()
        })
        logger.info(f"Seeded admin: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
    # Init storage
    init_storage()

@app.on_event("shutdown")
async def shutdown():
    client.close()

# ============================================================
# PHASE 2 — AI Audience Analytics & Interactive Advertising
# ============================================================

# ---------- privacy config ----------
class PrivacyConfigIn(BaseModel):
    camera_enabled: bool = True
    face_analysis_enabled: bool = True
    upload_raw_footage: bool = False
    data_retention_days: int = 30
    show_camera_notice: bool = True
    mirror_enabled: bool = True

@api.get("/admin/privacy")
async def get_privacy(user=Depends(require_role("admin"))):
    cfg = await db.privacy_config.find_one({"_id": "singleton"})
    if not cfg:
        default = PrivacyConfigIn().model_dump()
        default["_id"] = "singleton"
        await db.privacy_config.insert_one(default)
        cfg = default
    cfg.pop("_id", None)
    return cfg

@api.patch("/admin/privacy")
async def set_privacy(payload: PrivacyConfigIn, user=Depends(require_role("admin"))):
    doc = payload.model_dump()
    await db.privacy_config.update_one({"_id": "singleton"}, {"$set": doc}, upsert=True)
    await audit(user, "update_privacy", "privacy", "singleton", doc)
    return doc

@api.get("/player/privacy")
async def player_privacy(dev=Depends(get_current_device)):
    cfg = await db.privacy_config.find_one({"_id": "singleton"}) or PrivacyConfigIn().model_dump()
    cfg.pop("_id", None)
    return cfg

# ---------- audience samples (anonymous, aggregated) ----------
class AudienceSampleIn(BaseModel):
    viewers: int = 0
    people_present: bool = False
    age_distribution: Dict[str, int] = {}   # {"18-24": 1, "25-34": 2}
    gender_distribution: Dict[str, int] = {}   # {"male": 1, "female": 2}
    attention_score: int = 0  # 0-100
    looking_at_screen: int = 0
    avg_view_duration_sec: float = 0.0
    source: str = "simulator"  # or "face_api" | "mediapipe"

@api.post("/player/audience")
async def report_audience(payload: AudienceSampleIn, dev=Depends(get_current_device)):
    cfg = await db.privacy_config.find_one({"_id": "singleton"}) or {}
    if cfg.get("camera_enabled", True) == False:
        return {"ok": False, "reason": "camera disabled by admin"}
    doc = payload.model_dump()
    doc["device_id"] = str(dev["_id"])
    doc["device_code"] = dev.get("device_code")
    doc["at"] = now_iso()
    await db.audience_samples.insert_one(doc)
    return {"ok": True}

@api.get("/admin/audience")
async def admin_audience(hours: int = 24, device_id: Optional[str] = None, user=Depends(require_role("admin"))):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    q = {"at": {"$gte": since}}
    if device_id:
        q["device_id"] = device_id
    docs = await db.audience_samples.find(q).sort("at", -1).to_list(2000)
    if not docs:
        return {"samples_count": 0, "estimated_viewers": 0, "avg_attention": 0, "age_distribution": {}, "gender_distribution": {}, "by_hour": []}
    total_viewers = sum(d.get("viewers", 0) for d in docs)
    avg_att = round(sum(d.get("attention_score", 0) for d in docs) / len(docs))
    age_agg, gen_agg = {}, {}
    for d in docs:
        for k, v in (d.get("age_distribution") or {}).items():
            age_agg[k] = age_agg.get(k, 0) + v
        for k, v in (d.get("gender_distribution") or {}).items():
            gen_agg[k] = gen_agg.get(k, 0) + v
    # Aggregate hourly
    by_hour = {}
    for d in docs:
        try:
            hr = d["at"][:13]
        except Exception:
            continue
        e = by_hour.setdefault(hr, {"hour": hr, "viewers": 0, "attention_sum": 0, "n": 0})
        e["viewers"] += d.get("viewers", 0)
        e["attention_sum"] += d.get("attention_score", 0)
        e["n"] += 1
    hourly = sorted([{"hour": e["hour"], "viewers": e["viewers"], "avg_attention": round(e["attention_sum"]/max(e["n"],1))} for e in by_hour.values()], key=lambda x: x["hour"])
    return {
        "samples_count": len(docs), "estimated_viewers": total_viewers, "avg_attention": avg_att,
        "age_distribution": age_agg, "gender_distribution": gen_agg, "by_hour": hourly
    }

# ---------- mini games ----------
class GameIn(BaseModel):
    name: str
    game_type: str  # quiz|spin|memory|reaction|brand
    config: Dict[str, Any] = {}  # {questions: [...], segments: [...], etc.}
    active: bool = True

@api.get("/admin/games")
async def list_games(user=Depends(require_role("admin"))):
    docs = await db.games.find().sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.post("/admin/games")
async def create_game(payload: GameIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso(), "plays": 0, "completions": 0}
    res = await db.games.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "id": str(res.inserted_id)}

@api.delete("/admin/games/{gid}")
async def delete_game(gid: str, user=Depends(require_role("admin"))):
    await db.games.delete_one({"_id": oid(gid)})
    return {"ok": True}

@api.get("/games/list")
async def public_games_for_advertiser(user=Depends(get_current_user)):
    docs = await db.games.find({"active": True}).to_list(200)
    return serialize_list(docs)

# QR game session flow
class GameSessionInitIn(BaseModel):
    game_id: str
    campaign_id: Optional[str] = None
    device_id: Optional[str] = None

@api.post("/games/session")
async def start_game_session(payload: GameSessionInitIn):
    game = await db.games.find_one({"_id": oid(payload.game_id)})
    if not game:
        raise HTTPException(404, "Game not found")
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id, "game_id": payload.game_id, "campaign_id": payload.campaign_id,
        "device_id": payload.device_id, "started_at": now_iso(), "completed_at": None,
        "score": None, "status": "started"
    }
    await db.game_sessions.insert_one(session)
    await db.games.update_one({"_id": oid(payload.game_id)}, {"$inc": {"plays": 1}})
    return {"session_id": session_id, "game": serialize(game)}

class GameSessionCompleteIn(BaseModel):
    session_id: str
    score: int = 0
    result: Dict[str, Any] = {}

@api.post("/games/complete")
async def complete_game_session(payload: GameSessionCompleteIn):
    sess = await db.game_sessions.find_one({"session_id": payload.session_id})
    if not sess:
        raise HTTPException(404, "Session not found")
    await db.game_sessions.update_one({"session_id": payload.session_id},
        {"$set": {"completed_at": now_iso(), "score": payload.score, "result": payload.result, "status": "completed"}})
    await db.games.update_one({"_id": oid(sess["game_id"])}, {"$inc": {"completions": 1}})
    return {"ok": True}

@api.get("/games/session/{session_id}")
async def get_game_session(session_id: str):
    sess = await db.game_sessions.find_one({"session_id": session_id})
    if not sess:
        raise HTTPException(404, "Session not found")
    game = await db.games.find_one({"_id": oid(sess["game_id"])})
    return {"session": serialize(sess), "game": serialize(game)}

# ---------- screen mirroring ----------
@api.post("/mirror/init")
async def mirror_init(body: Dict[str, str], dev=Depends(get_current_device)):
    cfg = await db.privacy_config.find_one({"_id": "singleton"}) or {}
    if not cfg.get("mirror_enabled", True):
        raise HTTPException(403, "Mirror disabled by admin")
    token = str(uuid.uuid4())
    session = {
        "token": token, "device_id": str(dev["_id"]), "device_code": dev.get("device_code"),
        "created_at": now_iso(), "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "authorized": False, "content": None
    }
    await db.mirror_sessions.insert_one(session)
    return {"token": token, "expires_in": 300}

@api.post("/mirror/authorize")
async def mirror_authorize(body: Dict[str, Any]):
    token = body.get("token", "")
    content = body.get("content", {})  # {type: "text"|"image_url", value: "..."}
    sess = await db.mirror_sessions.find_one({"token": token})
    if not sess:
        raise HTTPException(404, "Invalid token")
    if datetime.now(timezone.utc).isoformat() > sess.get("expires_at", ""):
        raise HTTPException(400, "Session expired")
    # Whitelist safe content types only
    if content.get("type") not in ("text", "image_url"):
        raise HTTPException(400, "Unsupported content type")
    await db.mirror_sessions.update_one({"token": token}, {"$set": {"authorized": True, "content": content, "authorized_at": now_iso()}})
    return {"ok": True}

@api.get("/mirror/poll/{token}")
async def mirror_poll(token: str, dev=Depends(get_current_device)):
    sess = await db.mirror_sessions.find_one({"token": token, "device_id": str(dev["_id"])})
    if not sess:
        raise HTTPException(404, "Not found")
    return {"authorized": sess.get("authorized", False), "content": sess.get("content"), "expired": datetime.now(timezone.utc).isoformat() > sess.get("expires_at", "")}

# ---------- advanced analytics ----------
@api.get("/admin/analytics/engagement")
async def engagement_analytics(hours: int = 24, user=Depends(require_role("admin"))):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    qr_scans = await db.qr_scans.count_documents({"at": {"$gte": since}})
    game_starts = await db.game_sessions.count_documents({"started_at": {"$gte": since}})
    game_completes = await db.game_sessions.count_documents({"completed_at": {"$gte": since}})
    mirror_sess = await db.mirror_sessions.count_documents({"created_at": {"$gte": since}})
    mirror_auth = await db.mirror_sessions.count_documents({"authorized": True, "created_at": {"$gte": since}})
    return {
        "qr_scans": qr_scans, "game_starts": game_starts, "game_completions": game_completes,
        "mirror_sessions": mirror_sess, "mirror_authorized": mirror_auth,
        "completion_rate": round(100*game_completes/game_starts) if game_starts else 0
    }

@api.get("/advertiser/analytics")
async def advertiser_analytics(user=Depends(require_role("advertiser"))):
    campaigns = await db.campaigns.find({"advertiser_id": user["id"]}).to_list(200)
    camp_ids = [str(c["_id"]) for c in campaigns]
    plays = await db.playback_events.count_documents({"campaign_id": {"$in": camp_ids}})
    # audience while our ads played (device-level rough estimate)
    device_ids = list({d for c in campaigns for d in c.get("target_devices", [])}) or []
    if device_ids:
        aud = await db.audience_samples.find({"device_id": {"$in": device_ids}}).to_list(1000)
    else:
        aud = await db.audience_samples.find().to_list(1000)
    est_viewers = sum(a.get("viewers", 0) for a in aud)
    avg_att = round(sum(a.get("attention_score", 0) for a in aud) / len(aud)) if aud else 0
    age_agg, gen_agg = {}, {}
    for d in aud:
        for k, v in (d.get("age_distribution") or {}).items(): age_agg[k] = age_agg.get(k, 0) + v
        for k, v in (d.get("gender_distribution") or {}).items(): gen_agg[k] = gen_agg.get(k, 0) + v
    # game / qr engagement for this advertiser's campaigns
    game_starts = await db.game_sessions.count_documents({"campaign_id": {"$in": camp_ids}})
    game_completes = await db.game_sessions.count_documents({"campaign_id": {"$in": camp_ids}, "status": "completed"})
    # per campaign perf
    per_camp = []
    for c in campaigns:
        cid = str(c["_id"])
        cplays = await db.playback_events.count_documents({"campaign_id": cid})
        gstarts = await db.game_sessions.count_documents({"campaign_id": cid})
        per_camp.append({"id": cid, "name": c["name"], "plays": cplays, "game_starts": gstarts})
    return {
        "estimated_impressions": plays, "estimated_audience": est_viewers, "avg_attention": avg_att,
        "age_distribution": age_agg, "gender_distribution": gen_agg,
        "game_starts": game_starts, "game_completions": game_completes,
        "per_campaign": per_camp
    }

# ---------- reports export (CSV/PDF) — see phase-3 export_report_v2 below ----------
import io
import csv
from fastapi.responses import StreamingResponse

# ---------- campaign targeting update ----------
class CampaignRulesIn(BaseModel):
    targeting_rules: Optional[Dict[str, Any]] = None
    interactive: Optional[Dict[str, Any]] = None

@api.patch("/campaigns/{cid}/rules")
async def update_campaign_rules(cid: str, payload: CampaignRulesIn, user=Depends(require_role("advertiser"))):
    c = await db.campaigns.find_one({"_id": oid(cid), "advertiser_id": user["id"]})
    if not c:
        raise HTTPException(404, "Not found")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await db.campaigns.update_one({"_id": oid(cid)}, {"$set": updates})
    c = await db.campaigns.find_one({"_id": oid(cid)})
    return serialize(c)

# ---------- bulk driver CSV import ----------
@api.post("/admin/drivers/bulk")
async def bulk_import_drivers(file: UploadFile = File(...), user=Depends(require_role("admin"))):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    content = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    failed = []
    for i, row in enumerate(reader, start=2):
        try:
            email = (row.get("email") or "").strip().lower()
            if not email:
                failed.append({"row": i, "reason": "missing email"}); continue
            existing_user = await db.users.find_one({"email": email})
            if existing_user:
                uid = str(existing_user["_id"])
            else:
                default_pw = row.get("password") or "Owm@12345"
                res = await db.users.insert_one({
                    "email": email, "password_hash": hash_password(default_pw),
                    "name": row.get("full_name") or "Driver",
                    "role": "driver", "phone": row.get("phone") or "",
                    "token_version": 0, "status": "active", "created_at": now_iso()
                })
                uid = str(res.inserted_id)
            # upsert driver
            driver_doc = {
                "user_id": uid, "email": email,
                "full_name": row.get("full_name") or "",
                "phone": row.get("phone") or "",
                "address": row.get("address") or "",
                "city": row.get("city") or "", "state": row.get("state") or "",
                "vehicle_reg_no": row.get("vehicle_reg_no") or "",
                "vehicle_type": row.get("vehicle_type") or "Auto Rickshaw",
                "manufacturer": row.get("manufacturer") or "",
                "model": row.get("model") or "",
                "year": int(row.get("year") or 2022),
                "color": row.get("color") or "",
                "operating_area": row.get("operating_area") or "",
                "preferred_routes": row.get("preferred_routes") or "",
                "documents": [], "status": "Pending",
                "created_at": now_iso(), "updated_at": now_iso()
            }
            existing_d = await db.drivers.find_one({"user_id": uid})
            if existing_d:
                await db.drivers.update_one({"_id": existing_d["_id"]}, {"$set": driver_doc})
                driver_id = str(existing_d["_id"])
            else:
                r = await db.drivers.insert_one(driver_doc)
                driver_id = str(r.inserted_id)
                await db.vehicles.insert_one({
                    "driver_id": driver_id, "reg_no": driver_doc["vehicle_reg_no"],
                    "vehicle_type": driver_doc["vehicle_type"], "manufacturer": driver_doc["manufacturer"],
                    "model": driver_doc["model"], "year": driver_doc["year"], "color": driver_doc["color"],
                    "operating_area": driver_doc["operating_area"], "status": "Pending", "created_at": now_iso()
                })
            imported += 1
        except Exception as e:
            failed.append({"row": i, "reason": str(e)[:120]})
    await audit(user, "bulk_import_drivers", "driver", "", {"imported": imported, "failed": len(failed)})
    return {"imported": imported, "failed_count": len(failed), "failed": failed[:20]}


# ============================================================
# PHASE 3 — Enterprise DOOH platform
# ============================================================

# ---------- cities / areas / groups ----------
class CityIn(BaseModel):
    name: str
    state: str = ""
    areas: List[str] = []
    lat: float = 0.0
    lng: float = 0.0

@api.get("/admin/cities")
async def list_cities(user=Depends(require_role("admin"))):
    docs = await db.cities.find().sort("name", 1).to_list(200)
    return serialize_list(docs)

@api.post("/admin/cities")
async def create_city(payload: CityIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.cities.insert_one(doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.delete("/admin/cities/{cid}")
async def delete_city(cid: str, user=Depends(require_role("admin"))):
    await db.cities.delete_one({"_id": oid(cid)})
    return {"ok": True}

class GroupIn(BaseModel):
    name: str
    kind: str = Field(pattern="^(device|vehicle|route|city|campaign)$")
    member_ids: List[str] = []
    description: Optional[str] = ""

@api.get("/admin/groups")
async def list_groups(kind: Optional[str] = None, user=Depends(require_role("admin"))):
    q = {"kind": kind} if kind else {}
    docs = await db.groups.find(q).sort("created_at", -1).to_list(500)
    return serialize_list(docs)

@api.post("/admin/groups")
async def create_group(payload: GroupIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.groups.insert_one(doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.patch("/admin/groups/{gid}")
async def update_group(gid: str, payload: GroupIn, user=Depends(require_role("admin"))):
    await db.groups.update_one({"_id": oid(gid)}, {"$set": payload.model_dump()})
    return serialize(await db.groups.find_one({"_id": oid(gid)}))

@api.delete("/admin/groups/{gid}")
async def delete_group(gid: str, user=Depends(require_role("admin"))):
    await db.groups.delete_one({"_id": oid(gid)})
    return {"ok": True}

# ---------- bulk device operations ----------
class BulkDeviceOpIn(BaseModel):
    device_ids: List[str]
    action: str  # suspend|activate|sync|assign_campaign|remote_command
    payload: Dict[str, Any] = {}

@api.post("/admin/devices/bulk-op")
async def bulk_device_op(body: BulkDeviceOpIn, user=Depends(require_role("admin"))):
    action = body.action
    ids = [oid(x) for x in body.device_ids]
    if action == "suspend":
        await db.devices.update_many({"_id": {"$in": ids}}, {"$set": {"status": "Suspended"}})
    elif action == "activate":
        await db.devices.update_many({"_id": {"$in": ids}}, {"$set": {"status": "Approved"}})
    elif action == "sync":
        # queue a "refresh_playlist" command for each device
        for d in body.device_ids:
            await db.device_commands.insert_one({"device_id": d, "command": "refresh_playlist", "payload": {}, "at": now_iso(), "consumed": False})
    elif action == "assign_campaign":
        cid = body.payload.get("campaign_id")
        if not cid: raise HTTPException(400, "campaign_id required")
        camp = await db.campaigns.find_one({"_id": oid(cid)})
        if not camp: raise HTTPException(404, "Campaign not found")
        await db.campaigns.update_one({"_id": oid(cid)}, {"$addToSet": {"target_devices": {"$each": body.device_ids}}})
    elif action == "remote_command":
        cmd = body.payload.get("command", "")
        if cmd not in ("restart_player", "refresh_playlist", "clear_cache", "reload_config"):
            raise HTTPException(400, "Unsupported command")
        for d in body.device_ids:
            await db.device_commands.insert_one({"device_id": d, "command": cmd, "payload": body.payload, "at": now_iso(), "consumed": False})
    else:
        raise HTTPException(400, "Unknown action")
    await audit(user, f"bulk_{action}", "device", ",".join(body.device_ids[:5])+("…" if len(body.device_ids)>5 else ""), {"count": len(body.device_ids), "payload": body.payload})
    return {"ok": True, "affected": len(body.device_ids)}

# ---------- remote device commands (per device) ----------
@api.post("/admin/devices/{did}/command")
async def send_device_command(did: str, body: Dict[str, Any], user=Depends(require_role("admin"))):
    cmd = body.get("command", "")
    if cmd not in ("restart_player", "refresh_playlist", "clear_cache", "reload_config", "disable", "enable"):
        raise HTTPException(400, "Unsupported command")
    await db.device_commands.insert_one({"device_id": did, "command": cmd, "payload": body, "at": now_iso(), "consumed": False})
    await audit(user, "device_command", "device", did, {"command": cmd})
    return {"ok": True}

@api.get("/player/commands")
async def poll_commands(dev=Depends(get_current_device)):
    did = str(dev["_id"])
    cmds = await db.device_commands.find({"device_id": did, "consumed": False}).sort("at", 1).to_list(20)
    if cmds:
        await db.device_commands.update_many({"_id": {"$in": [c["_id"] for c in cmds]}}, {"$set": {"consumed": True, "consumed_at": now_iso()}})
    return {"commands": [{"command": c["command"], "payload": c.get("payload", {}), "at": c.get("at")} for c in cmds]}

# ---------- advanced device health (extends heartbeat) ----------
class DeviceHealthIn(BaseModel):
    cpu_pct: Optional[float] = None
    ram_pct: Optional[float] = None
    storage_pct: Optional[float] = None
    temperature_c: Optional[float] = None
    battery: Optional[int] = None
    charging: Optional[bool] = None
    network: Optional[str] = ""
    app_version: Optional[str] = ""
    camera_ok: Optional[bool] = None
    ai_ok: Optional[bool] = None

@api.post("/player/health")
async def report_health(payload: DeviceHealthIn, dev=Depends(get_current_device)):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["last_online"] = now_iso()
    updates["status"] = "Online"
    await db.devices.update_one({"_id": dev["_id"]}, {"$set": updates})
    # Auto alerts
    dcode = dev.get("device_code")
    if payload.storage_pct is not None and payload.storage_pct > 90:
        await create_alert("storage_full", f"Storage almost full on {dcode} ({payload.storage_pct}%)", severity="high", device_id=str(dev["_id"]))
    if payload.battery is not None and payload.battery < 15 and payload.charging == False:
        await create_alert("battery_low", f"Battery low on {dcode} ({payload.battery}%)", severity="medium", device_id=str(dev["_id"]))
    if payload.temperature_c is not None and payload.temperature_c > 60:
        await create_alert("temp_high", f"High temperature on {dcode} ({payload.temperature_c}°C)", severity="high", device_id=str(dev["_id"]))
    if payload.camera_ok == False:
        await create_alert("camera_fail", f"Camera unavailable on {dcode}", severity="medium", device_id=str(dev["_id"]))
    return {"ok": True}

# ---------- alerts ----------
async def create_alert(kind: str, message: str, severity: str = "info", device_id: str = "", meta: Dict = None):
    # dedupe: don't insert same open alert twice within 15 min for same kind+device
    recent = await db.alerts.find_one({"kind": kind, "device_id": device_id, "resolved": False,
                                         "at": {"$gte": (datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat()}})
    if recent:
        return
    await db.alerts.insert_one({"kind": kind, "message": message, "severity": severity,
                                 "device_id": device_id, "meta": meta or {}, "at": now_iso(), "resolved": False})

@api.get("/admin/alerts")
async def list_alerts(resolved: bool = False, user=Depends(require_role("admin"))):
    docs = await db.alerts.find({"resolved": resolved}).sort("at", -1).limit(200).to_list(200)
    return serialize_list(docs)

@api.post("/admin/alerts/{aid}/resolve")
async def resolve_alert(aid: str, user=Depends(require_role("admin"))):
    await db.alerts.update_one({"_id": oid(aid)}, {"$set": {"resolved": True, "resolved_at": now_iso(), "resolved_by": user["email"]}})
    return {"ok": True}

# Background offline scan — expose as an admin trigger; production would run via crons
@api.post("/admin/alerts/scan-offline")
async def scan_offline(user=Depends(require_role("admin"))):
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    offline = await db.devices.find({"last_online": {"$lt": cutoff}, "status": {"$in": ["Online", "Approved"]}}).to_list(500)
    n = 0
    for d in offline:
        await create_alert("device_offline", f"Device {d.get('device_code')} offline (last seen {d.get('last_online')})", severity="medium", device_id=str(d["_id"]))
        n += 1
    return {"scanned": len(offline), "alerts_created": n}

# ---------- pricing engine ----------
class PricingIn(BaseModel):
    name: str
    kind: str  # base|city|time|advertiser|agency
    conditions: Dict[str, Any] = {}  # {city_id, hours_range, advertiser_id, ...}
    unit: str = "per_day_per_device"  # per_play|per_day_per_device|per_impression|flat
    amount: float = 0
    currency: str = "usd"
    active: bool = True

@api.get("/admin/pricing")
async def list_pricing(user=Depends(require_role("admin"))):
    docs = await db.pricing.find().sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.post("/admin/pricing")
async def create_pricing(payload: PricingIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.pricing.insert_one(doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.delete("/admin/pricing/{pid}")
async def delete_pricing(pid: str, user=Depends(require_role("admin"))):
    await db.pricing.delete_one({"_id": oid(pid)})
    return {"ok": True}

# ---------- revenue rollups ----------
@api.get("/admin/revenue/summary")
async def revenue_summary(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    month_start = now.replace(day=1).date().isoformat()
    paid_q = {"payment_status": "paid"}
    total = await db.payment_transactions.aggregate([{"$match": paid_q}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    today_total = await db.payment_transactions.aggregate([{"$match": {**paid_q, "updated_at": {"$gte": today}}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    month_total = await db.payment_transactions.aggregate([{"$match": {**paid_q, "updated_at": {"$gte": month_start}}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    pending = await db.invoices.aggregate([{"$match": {"status": "Pending"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    return {
        "total_revenue": (total[0]["s"] if total else 0),
        "today_revenue": (today_total[0]["s"] if today_total else 0),
        "month_revenue": (month_total[0]["s"] if month_total else 0),
        "pending_payments": (pending[0]["s"] if pending else 0),
        "advertisers_count": await db.users.count_documents({"role": "advertiser"}),
        "campaigns_active": await db.campaigns.count_documents({"status": "Active"}),
    }

@api.get("/admin/revenue/by-advertiser")
async def revenue_by_advertiser(user=Depends(require_role("admin"))):
    pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": "$user_id", "spend": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"spend": -1}},
        {"$limit": 100}
    ]
    rows = await db.payment_transactions.aggregate(pipeline).to_list(100)
    out = []
    for r in rows:
        u = await db.users.find_one({"_id": oid(r["_id"])}) if r["_id"] else None
        out.append({"advertiser_id": r["_id"], "email": u.get("email", "unknown") if u else "unknown", "name": u.get("name", "") if u else "", "spend": r["spend"], "count": r["count"]})
    return out

# ---------- driver earnings ----------
def compute_earnings_per_day() -> float:
    return float(os.environ.get("DRIVER_DAILY_RATE", "50"))  # $50/day default

@api.get("/admin/earnings")
async def list_earnings(user=Depends(require_role("admin"))):
    devices = await db.devices.find({"status": {"$in": ["Approved", "Online"]}}).to_list(1000)
    per_day = compute_earnings_per_day()
    out = []
    for d in devices:
        drv = await db.drivers.find_one({"_id": oid(d["driver_id"])}) if d.get("driver_id") else None
        if not drv: continue
        active_days = 1
        try:
            active_days = max(1, (datetime.now(timezone.utc) - datetime.fromisoformat(d.get("created_at").replace("Z","+00:00")) if d.get("created_at") else timedelta(days=1)).days or 1)
        except Exception:
            active_days = 1
        paid = await db.driver_payouts.aggregate([{"$match": {"driver_id": str(drv["_id"]), "status": "Paid"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
        paid_sum = paid[0]["s"] if paid else 0
        earnings = active_days * per_day
        out.append({
            "driver_id": str(drv["_id"]),
            "driver_name": drv.get("full_name"),
            "email": drv.get("email"),
            "device_code": d.get("device_code"),
            "active_days": active_days,
            "earnings_total": round(earnings, 2),
            "paid": paid_sum,
            "pending": round(earnings - paid_sum, 2),
        })
    return {"per_day_rate": per_day, "drivers": out}

@api.get("/driver/earnings")
async def my_earnings(user=Depends(require_role("driver"))):
    drv = await db.drivers.find_one({"user_id": user["id"]})
    if not drv: return {"earnings_total": 0, "paid": 0, "pending": 0, "payouts": []}
    devices = await db.devices.find({"driver_id": str(drv["_id"])}).to_list(20)
    per_day = compute_earnings_per_day()
    earnings = sum(max(1, (datetime.now(timezone.utc) - datetime.fromisoformat(d["created_at"].replace("Z","+00:00")) ).days or 1) * per_day for d in devices if d.get("created_at"))
    paid = await db.driver_payouts.aggregate([{"$match": {"driver_id": str(drv["_id"]), "status": "Paid"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    paid_sum = paid[0]["s"] if paid else 0
    payouts = await db.driver_payouts.find({"driver_id": str(drv["_id"])}).sort("at", -1).to_list(50)
    return {"per_day_rate": per_day, "earnings_total": round(earnings, 2), "paid": paid_sum, "pending": round(earnings - paid_sum, 2), "payouts": serialize_list(payouts)}

class PayoutIn(BaseModel):
    driver_id: str
    amount: float
    note: Optional[str] = ""

@api.post("/admin/earnings/payout")
async def create_payout(payload: PayoutIn, user=Depends(require_role("admin"))):
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    drv = await db.drivers.find_one({"_id": oid(payload.driver_id)})
    if not drv:
        raise HTTPException(404, "Driver not found")
    doc = {"driver_id": payload.driver_id, "amount": payload.amount, "note": payload.note, "status": "Paid", "at": now_iso(), "by": user["email"]}
    res = await db.driver_payouts.insert_one(doc)
    await audit(user, "payout", "driver", payload.driver_id, {"amount": payload.amount})
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

# ---------- agency role ----------
class AgencyLinkIn(BaseModel):
    advertiser_id: str  # user id

@api.post("/agency/link")
async def link_advertiser(payload: AgencyLinkIn, user=Depends(require_role("agency"))):
    adv = await db.users.find_one({"_id": oid(payload.advertiser_id), "role": "advertiser"})
    if not adv: raise HTTPException(404, "Advertiser not found")
    await db.agency_links.update_one({"agency_id": user["id"], "advertiser_id": payload.advertiser_id},
                                       {"$set": {"agency_id": user["id"], "advertiser_id": payload.advertiser_id, "at": now_iso()}}, upsert=True)
    return {"ok": True}

@api.get("/agency/advertisers")
async def agency_advertisers(user=Depends(require_role("agency"))):
    links = await db.agency_links.find({"agency_id": user["id"]}).to_list(200)
    adv_ids = [l["advertiser_id"] for l in links]
    out = []
    for aid in adv_ids:
        u = await db.users.find_one({"_id": oid(aid)})
        if not u: continue
        cnt = await db.campaigns.count_documents({"advertiser_id": aid})
        spend = await db.payment_transactions.aggregate([{"$match": {"user_id": aid, "payment_status": "paid"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
        out.append({"id": aid, "email": u["email"], "name": u.get("name"), "company": u.get("company"), "campaigns": cnt, "spend": spend[0]["s"] if spend else 0})
    return out

@api.get("/agency/summary")
async def agency_summary(user=Depends(require_role("agency"))):
    links = await db.agency_links.find({"agency_id": user["id"]}).to_list(200)
    adv_ids = [l["advertiser_id"] for l in links]
    return {
        "advertisers": len(adv_ids),
        "campaigns": await db.campaigns.count_documents({"advertiser_id": {"$in": adv_ids}}),
        "total_spend": (await db.payment_transactions.aggregate([{"$match": {"user_id": {"$in": adv_ids}, "payment_status": "paid"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1) or [{}])[0].get("s", 0),
    }

# Allow agency registration by relaxing RegisterIn's regex — actually already limited to advertiser|driver.
# Register agencies via admin:
class AdminUserCreateIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = Field(pattern="^(agency|admin|advertiser|driver)$")
    permissions: List[str] = []

@api.post("/admin/users")
async def admin_create_user(payload: AdminUserCreateIn, user=Depends(require_role("admin"))):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already exists")
    doc = {"email": email, "password_hash": hash_password(payload.password), "name": payload.name,
           "role": payload.role, "permissions": payload.permissions, "token_version": 0,
           "status": "active", "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    await audit(user, "create_user", "user", str(res.inserted_id), {"role": payload.role})
    return {"id": str(res.inserted_id), "email": email, "role": payload.role}

@api.get("/admin/users")
async def admin_list_users(user=Depends(require_role("admin"))):
    docs = await db.users.find({"role": {"$in": ["admin", "agency"]}}).sort("created_at", -1).to_list(500)
    return serialize_list(docs)

class PermsPatch(BaseModel):
    permissions: List[str]
    role: Optional[str] = Field(default=None, pattern="^(agency|admin|advertiser|driver)$")

@api.patch("/admin/users/{uid}/permissions")
async def update_perms(uid: str, payload: PermsPatch, user=Depends(require_role("admin"))):
    updates = {"permissions": payload.permissions}
    if payload.role: updates["role"] = payload.role
    await db.users.update_one({"_id": oid(uid)}, {"$set": updates})
    return serialize(await db.users.find_one({"_id": oid(uid)}))

# ---------- API keys / external platform ----------
import secrets as _sec

class ApiKeyIn(BaseModel):
    name: str
    scopes: List[str] = ["read:campaigns", "read:analytics"]

@api.post("/admin/api-keys")
async def create_api_key(payload: ApiKeyIn, user=Depends(require_role("admin"))):
    raw = "owm_" + _sec.token_urlsafe(28)
    khash = hashlib.sha256(raw.encode()).hexdigest()
    await db.api_keys.insert_one({"name": payload.name, "scopes": payload.scopes, "key_hash": khash,
                                    "prefix": raw[:12], "created_by": user["email"], "created_at": now_iso(), "revoked": False, "last_used": None})
    return {"api_key": raw, "prefix": raw[:12], "message": "Store this key securely — it will not be shown again."}

@api.get("/admin/api-keys")
async def list_api_keys(user=Depends(require_role("admin"))):
    docs = await db.api_keys.find({"revoked": False}).sort("created_at", -1).to_list(200)
    for d in docs:
        d.pop("key_hash", None)
    return serialize_list(docs)

@api.delete("/admin/api-keys/{kid}")
async def revoke_api_key(kid: str, user=Depends(require_role("admin"))):
    await db.api_keys.update_one({"_id": oid(kid)}, {"$set": {"revoked": True, "revoked_at": now_iso()}})
    return {"ok": True}

async def verify_api_key(request: Request, required_scope: str):
    key = request.headers.get("X-API-Key", "")
    if not key:
        raise HTTPException(401, "Missing X-API-Key")
    khash = hashlib.sha256(key.encode()).hexdigest()
    rec = await db.api_keys.find_one({"key_hash": khash, "revoked": False})
    if not rec:
        raise HTTPException(401, "Invalid API key")
    if required_scope not in rec.get("scopes", []):
        raise HTTPException(403, f"Missing scope: {required_scope}")
    await db.api_keys.update_one({"_id": rec["_id"]}, {"$set": {"last_used": now_iso()}})
    return rec

# External API endpoints (v1)
@api.get("/external/v1/campaigns")
async def ext_campaigns(request: Request):
    await verify_api_key(request, "read:campaigns")
    docs = await db.campaigns.find().limit(500).to_list(500)
    return {"data": serialize_list(docs)}

@api.get("/external/v1/analytics/summary")
async def ext_analytics(request: Request):
    await verify_api_key(request, "read:analytics")
    return {
        "plays": await db.playback_events.count_documents({}),
        "devices_online": await db.devices.count_documents({"status": "Online"}),
        "campaigns_active": await db.campaigns.count_documents({"status": "Active"}),
        "audience_samples": await db.audience_samples.count_documents({}),
    }

# ---------- BI / executive dashboard ----------
@api.get("/admin/bi/summary")
async def bi_summary(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    online_cutoff = (now - timedelta(minutes=5)).isoformat()
    day_iso = now.date().isoformat()
    month_iso = now.replace(day=1).date().isoformat()
    paid_q = {"payment_status": "paid"}
    day_rev = await db.payment_transactions.aggregate([{"$match": {**paid_q, "updated_at": {"$gte": day_iso}}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    month_rev = await db.payment_transactions.aggregate([{"$match": {**paid_q, "updated_at": {"$gte": month_iso}}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    pending = await db.invoices.aggregate([{"$match": {"status": "Pending"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    # Top campaigns
    top_campaigns_agg = await db.playback_events.aggregate([{"$group": {"_id": "$campaign_id", "plays": {"$sum": 1}}}, {"$sort": {"plays": -1}}, {"$limit": 5}]).to_list(5)
    top_camps = []
    for row in top_campaigns_agg:
        if not row["_id"]: continue
        c = await db.campaigns.find_one({"_id": oid(row["_id"])})
        if c: top_camps.append({"id": row["_id"], "name": c["name"], "plays": row["plays"]})
    # Top devices
    top_devs_agg = await db.playback_events.aggregate([{"$group": {"_id": "$device_id", "plays": {"$sum": 1}}}, {"$sort": {"plays": -1}}, {"$limit": 5}]).to_list(5)
    top_devs = []
    for row in top_devs_agg:
        if not row["_id"]: continue
        d = await db.devices.find_one({"_id": oid(row["_id"])})
        if d: top_devs.append({"id": row["_id"], "device_code": d.get("device_code"), "plays": row["plays"]})
    return {
        "network": {
            "cities": await db.cities.count_documents({}),
            "devices_total": await db.devices.count_documents({}),
            "devices_online": await db.devices.count_documents({"last_online": {"$gte": online_cutoff}}),
            "devices_offline": await db.devices.count_documents({"last_online": {"$lt": online_cutoff}}),
            "vehicles": await db.vehicles.count_documents({}),
        },
        "advertising": {
            "campaigns_active": await db.campaigns.count_documents({"status": "Active"}),
            "ads_total": await db.ads.count_documents({}),
            "plays": await db.playback_events.count_documents({}),
            "estimated_audience": (await db.audience_samples.aggregate([{"$group": {"_id": None, "s": {"$sum": "$viewers"}}}]).to_list(1) or [{}])[0].get("s", 0),
        },
        "revenue": {
            "today": day_rev[0]["s"] if day_rev else 0,
            "month": month_rev[0]["s"] if month_rev else 0,
            "pending": pending[0]["s"] if pending else 0,
        },
        "top_campaigns": top_camps,
        "top_devices": top_devs,
        "alerts_open": await db.alerts.count_documents({"resolved": False}),
    }

@api.get("/admin/bi/heatmap")
async def bi_heatmap(user=Depends(require_role("admin"))):
    """City-level device + play counts for map view."""
    cities = await db.cities.find().to_list(200)
    out = []
    for c in cities:
        # vehicles in this city -> devices -> plays
        vehicles = await db.vehicles.find({"operating_area": {"$regex": c["name"], "$options": "i"}}).to_list(500)
        v_ids = [str(v["_id"]) for v in vehicles]
        devices_n = await db.devices.count_documents({"vehicle_id": {"$in": v_ids}}) if v_ids else 0
        plays_n = 0
        if v_ids:
            d_ids = [str(x["_id"]) async for x in db.devices.find({"vehicle_id": {"$in": v_ids}})]
            plays_n = await db.playback_events.count_documents({"device_id": {"$in": d_ids}}) if d_ids else 0
        out.append({"city": c["name"], "state": c.get("state", ""), "lat": c.get("lat", 0), "lng": c.get("lng", 0), "devices": devices_n, "plays": plays_n})
    return out

# ---------- extend campaign targeting for cities ----------
class CampaignAreasIn(BaseModel):
    target_cities: List[str] = []
    target_groups: List[str] = []

@api.patch("/campaigns/{cid}/areas")
async def update_campaign_areas(cid: str, payload: CampaignAreasIn, user=Depends(require_role("advertiser"))):
    c = await db.campaigns.find_one({"_id": oid(cid), "advertiser_id": user["id"]})
    if not c: raise HTTPException(404, "Not found")
    await db.campaigns.update_one({"_id": oid(cid)}, {"$set": payload.model_dump()})
    return serialize(await db.campaigns.find_one({"_id": oid(cid)}))

# ---------- extended reports ----------
@api.get("/admin/reports/export")
async def export_report_v2(kind: str = "campaigns", fmt: str = "csv", days: int = 30, user=Depends(require_role("admin"))):
    """Overrides the phase-2 export with additional kinds: drivers, network, revenue."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if kind == "drivers":
        rows = await db.drivers.find().to_list(1000)
        headers = ["full_name", "email", "phone", "city", "state", "vehicle_reg_no", "status", "created_at"]
        data = [[r.get(h, "") for h in headers] for r in rows]
    elif kind == "network":
        # per device rollup
        rows = await db.devices.find().to_list(2000)
        headers = ["device_code", "status", "last_online", "app_version"]
        # Add plays_count per device
        data = []
        for r in rows:
            plays = await db.playback_events.count_documents({"device_id": str(r["_id"])})
            data.append([r.get("device_code",""), r.get("status",""), r.get("last_online",""), r.get("app_version",""), plays])
        headers.append("plays")
    elif kind == "revenue":
        rows = await db.payment_transactions.find({"payment_status": "paid"}).to_list(2000)
        headers = ["session_id", "user_id", "amount", "currency", "updated_at"]
        data = [[r.get(h, "") for h in headers] for r in rows]
    elif kind == "campaigns":
        rows = await db.campaigns.find().to_list(1000)
        headers = ["name", "advertiser_id", "start_date", "end_date", "status", "budget", "objective"]
        data = [[r.get(h, "") for h in headers] for r in rows]
    elif kind == "devices":
        rows = await db.devices.find().to_list(2000)
        headers = ["device_code", "status", "last_online", "app_version", "network"]
        data = [[r.get(h, "") for h in headers] for r in rows]
    elif kind == "audience":
        rows = await db.audience_samples.find({"at": {"$gte": since}}).to_list(5000)
        headers = ["at", "device_code", "viewers", "attention_score", "age_distribution", "gender_distribution"]
        data = [[r.get(h, "") if h not in ("age_distribution","gender_distribution") else str(r.get(h, {})) for h in headers] for r in rows]
    elif kind == "engagement":
        rows = await db.game_sessions.find({"started_at": {"$gte": since}}).to_list(5000)
        headers = ["session_id", "game_id", "campaign_id", "device_id", "started_at", "completed_at", "score", "status"]
        data = [[r.get(h, "") for h in headers] for r in rows]
    else:
        raise HTTPException(400, "Unknown report kind")

    if fmt == "csv":
        buf = io.StringIO(); w = csv.writer(buf); w.writerow(headers); w.writerows(data); buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{kind}_{days}d.csv"'})
    elif fmt == "pdf":
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=32, bottomMargin=24)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"On Wheels Media — {kind.title()} Report ({days} days)", styles["Title"]), Spacer(1, 12)]
        t = Table([headers] + [[str(x)[:60] for x in row] for row in data[:500]], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#facc15")),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.25,colors.grey)]))
        story.append(t); doc.build(story); buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{kind}_{days}d.pdf"'})
    else:
        raise HTTPException(400, "fmt must be csv or pdf")

# ============================================================
# PRICING & BILLING (INR) — Admin-controlled, campaign snapshot on purchase
# ============================================================

class PlanIn(BaseModel):
    name: str
    autos: int = Field(ge=1)
    duration_days: int = Field(ge=1)
    price_inr: float = Field(ge=0)
    estimated_reach: Optional[int] = 0
    features: List[str] = []
    pricing_model: str = "per_campaign"  # per_auto|per_day|per_campaign|cpm|auto_duration|auto_impressions|custom_quote
    is_custom: bool = False
    active: bool = True
    sort_order: int = 0

async def log_price_change(user, entity: str, entity_id: str, old: Any, new: Any, reason: str = ""):
    await db.pricing_history.insert_one({
        "entity": entity, "entity_id": entity_id, "old": old, "new": new,
        "changed_by": user.get("email"), "reason": reason, "at": now_iso()
    })

@api.get("/admin/plans")
async def list_plans(user=Depends(require_role("admin"))):
    docs = await db.plans.find().sort([("sort_order", 1), ("autos", 1)]).to_list(200)
    return serialize_list(docs)

@api.get("/plans/public")
async def public_plans():
    docs = await db.plans.find({"active": True}).sort([("sort_order", 1), ("autos", 1)]).to_list(200)
    return serialize_list(docs)

@api.post("/admin/plans")
async def create_plan(payload: PlanIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso(), "updated_at": now_iso()}
    res = await db.plans.insert_one(doc)
    await log_price_change(user, "plan_create", str(res.inserted_id), None, doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.patch("/admin/plans/{pid}")
async def update_plan(pid: str, payload: PlanIn, user=Depends(require_role("admin"))):
    old = await db.plans.find_one({"_id": oid(pid)})
    if not old: raise HTTPException(404, "Plan not found")
    updates = {**payload.model_dump(), "updated_at": now_iso()}
    await db.plans.update_one({"_id": oid(pid)}, {"$set": updates})
    await log_price_change(user, "plan_update", pid, {"price_inr": old.get("price_inr"), "autos": old.get("autos"), "duration_days": old.get("duration_days")}, {"price_inr": updates["price_inr"], "autos": updates["autos"], "duration_days": updates["duration_days"]})
    doc = await db.plans.find_one({"_id": oid(pid)})
    return serialize(doc)

@api.post("/admin/plans/{pid}/duplicate")
async def duplicate_plan(pid: str, user=Depends(require_role("admin"))):
    orig = await db.plans.find_one({"_id": oid(pid)})
    if not orig: raise HTTPException(404, "Not found")
    orig.pop("_id", None)
    orig["name"] = f"{orig.get('name','')} (copy)"
    orig["active"] = False
    orig["created_at"] = now_iso()
    res = await db.plans.insert_one(orig)
    doc = await db.plans.find_one({"_id": res.inserted_id})
    return serialize(doc)

@api.delete("/admin/plans/{pid}")
async def delete_plan(pid: str, user=Depends(require_role("admin"))):
    old = await db.plans.find_one({"_id": oid(pid)})
    await db.plans.delete_one({"_id": oid(pid)})
    if old:
        await log_price_change(user, "plan_delete", pid, old, None)
    return {"ok": True}

# --- CPM tiers ---
class CpmTierIn(BaseModel):
    views: int = Field(ge=1)
    price_inr: float = Field(ge=0)
    active: bool = True
    sort_order: int = 0

@api.get("/admin/cpm-tiers")
async def list_cpm(user=Depends(require_role("admin"))):
    docs = await db.cpm_tiers.find().sort([("views", 1)]).to_list(200)
    return serialize_list(docs)

@api.get("/cpm-tiers/public")
async def public_cpm():
    docs = await db.cpm_tiers.find({"active": True}).sort([("views", 1)]).to_list(200)
    return serialize_list(docs)

@api.post("/admin/cpm-tiers")
async def create_cpm(payload: CpmTierIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.cpm_tiers.insert_one(doc)
    await log_price_change(user, "cpm_create", str(res.inserted_id), None, doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.patch("/admin/cpm-tiers/{tid}")
async def update_cpm(tid: str, payload: CpmTierIn, user=Depends(require_role("admin"))):
    old = await db.cpm_tiers.find_one({"_id": oid(tid)})
    if not old: raise HTTPException(404, "Not found")
    await db.cpm_tiers.update_one({"_id": oid(tid)}, {"$set": payload.model_dump()})
    await log_price_change(user, "cpm_update", tid, {"views": old["views"], "price_inr": old["price_inr"]}, {"views": payload.views, "price_inr": payload.price_inr})
    return serialize(await db.cpm_tiers.find_one({"_id": oid(tid)}))

@api.delete("/admin/cpm-tiers/{tid}")
async def delete_cpm(tid: str, user=Depends(require_role("admin"))):
    old = await db.cpm_tiers.find_one({"_id": oid(tid)})
    await db.cpm_tiers.delete_one({"_id": oid(tid)})
    if old: await log_price_change(user, "cpm_delete", tid, old, None)
    return {"ok": True}

# --- Duration presets ---
class DurationIn(BaseModel):
    days: int = Field(ge=1)
    label: str = ""
    active: bool = True

@api.get("/admin/duration-options")
async def list_durations(user=Depends(require_role("admin"))):
    docs = await db.duration_options.find().sort("days", 1).to_list(50)
    return serialize_list(docs)

@api.get("/duration-options/public")
async def public_durations():
    docs = await db.duration_options.find({"active": True}).sort("days", 1).to_list(50)
    return serialize_list(docs)

@api.post("/admin/duration-options")
async def create_duration(payload: DurationIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "created_at": now_iso()}
    res = await db.duration_options.insert_one(doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.delete("/admin/duration-options/{did}")
async def delete_duration(did: str, user=Depends(require_role("admin"))):
    await db.duration_options.delete_one({"_id": oid(did)})
    return {"ok": True}

# --- Discounts ---
class DiscountIn(BaseModel):
    code: str
    kind: str = Field(pattern="^(percent|fixed)$")
    value: float = Field(ge=0)
    description: Optional[str] = ""
    min_amount_inr: float = 0
    active: bool = True

@api.get("/admin/discounts")
async def list_discounts(user=Depends(require_role("admin"))):
    docs = await db.discounts.find().sort("created_at", -1).to_list(200)
    return serialize_list(docs)

@api.post("/admin/discounts")
async def create_discount(payload: DiscountIn, user=Depends(require_role("admin"))):
    doc = {**payload.model_dump(), "code": payload.code.upper(), "created_at": now_iso()}
    if await db.discounts.find_one({"code": doc["code"]}):
        raise HTTPException(400, "Discount code already exists")
    res = await db.discounts.insert_one(doc)
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.patch("/admin/discounts/{did}")
async def update_discount(did: str, payload: DiscountIn, user=Depends(require_role("admin"))):
    await db.discounts.update_one({"_id": oid(did)}, {"$set": {**payload.model_dump(), "code": payload.code.upper()}})
    return serialize(await db.discounts.find_one({"_id": oid(did)}))

@api.delete("/admin/discounts/{did}")
async def delete_discount(did: str, user=Depends(require_role("admin"))):
    await db.discounts.delete_one({"_id": oid(did)})
    return {"ok": True}

@api.get("/discounts/validate/{code}")
async def validate_discount(code: str, user=Depends(require_role("advertiser"))):
    d = await db.discounts.find_one({"code": code.upper(), "active": True})
    if not d: raise HTTPException(404, "Invalid or expired code")
    return serialize(d)

# --- Pricing settings (currency + GST) ---
class PricingSettingsIn(BaseModel):
    currency_code: str = "INR"
    currency_symbol: str = "₹"
    gst_enabled: bool = True
    gst_percentage: float = 18.0

@api.get("/admin/pricing-settings")
async def get_pricing_settings(user=Depends(require_role("admin"))):
    cfg = await db.pricing_settings.find_one({"_id": "singleton"})
    if not cfg:
        default = PricingSettingsIn().model_dump()
        default["_id"] = "singleton"
        await db.pricing_settings.insert_one(default)
        cfg = default
    cfg.pop("_id", None)
    return cfg

@api.get("/pricing-settings/public")
async def public_pricing_settings():
    cfg = await db.pricing_settings.find_one({"_id": "singleton"})
    if not cfg:
        cfg = PricingSettingsIn().model_dump()
    else:
        cfg.pop("_id", None)
    return cfg

@api.patch("/admin/pricing-settings")
async def update_pricing_settings(payload: PricingSettingsIn, user=Depends(require_role("admin"))):
    old = await db.pricing_settings.find_one({"_id": "singleton"}) or {}
    doc = payload.model_dump()
    await db.pricing_settings.update_one({"_id": "singleton"}, {"$set": doc}, upsert=True)
    await log_price_change(user, "settings_update", "singleton", {k: old.get(k) for k in doc.keys()}, doc, reason="Settings changed")
    return doc

# --- Price history ---
@api.get("/admin/pricing-history")
async def pricing_history(limit: int = 200, user=Depends(require_role("admin"))):
    docs = await db.pricing_history.find().sort("at", -1).limit(limit).to_list(limit)
    return serialize_list(docs)

# --- Custom quote requests ---
class QuoteRequestIn(BaseModel):
    autos: int = Field(ge=1)
    target_city: str = ""
    duration_days: int = Field(ge=1)
    estimated_views: int = 0
    ad_format: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    special_requirements: Optional[str] = ""
    contact_name: Optional[str] = ""
    contact_phone: Optional[str] = ""

@api.post("/quotes/request")
async def create_quote_request(payload: QuoteRequestIn, user=Depends(require_role("advertiser"))):
    doc = {**payload.model_dump(),
           "advertiser_id": user["id"], "advertiser_email": user["email"],
           "status": "pending", "admin_price_inr": None, "admin_notes": "",
           "created_at": now_iso()}
    res = await db.quote_requests.insert_one(doc)
    await db.notifications.insert_one({"user_id": user["id"], "type": "quote_requested",
                                         "message": "Your custom quote request has been received.",
                                         "read": False, "at": now_iso()})
    doc.pop("_id", None); doc["id"] = str(res.inserted_id)
    return doc

@api.get("/quotes/mine")
async def list_my_quotes(user=Depends(require_role("advertiser"))):
    docs = await db.quote_requests.find({"advertiser_id": user["id"]}).sort("created_at", -1).to_list(100)
    return serialize_list(docs)

@api.get("/admin/quotes")
async def admin_list_quotes(status: Optional[str] = None, user=Depends(require_role("admin"))):
    q = {"status": status} if status else {}
    docs = await db.quote_requests.find(q).sort("created_at", -1).to_list(500)
    return serialize_list(docs)

class QuoteReplyIn(BaseModel):
    status: str = Field(pattern="^(quoted|approved|rejected)$")
    admin_price_inr: Optional[float] = None
    admin_notes: Optional[str] = ""

@api.patch("/admin/quotes/{qid}")
async def admin_reply_quote(qid: str, payload: QuoteReplyIn, user=Depends(require_role("admin"))):
    q = await db.quote_requests.find_one({"_id": oid(qid)})
    if not q: raise HTTPException(404, "Not found")
    updates = {"status": payload.status, "admin_notes": payload.admin_notes or "", "replied_at": now_iso(), "replied_by": user["email"]}
    if payload.admin_price_inr is not None:
        updates["admin_price_inr"] = float(payload.admin_price_inr)
    await db.quote_requests.update_one({"_id": oid(qid)}, {"$set": updates})
    await db.notifications.insert_one({"user_id": q["advertiser_id"], "type": "quote_reply",
                                         "message": f"Your custom quote is now {payload.status}. Price: ₹{payload.admin_price_inr or ''}",
                                         "read": False, "at": now_iso()})
    await audit(user, "reply_quote", "quote", qid, updates)
    return serialize(await db.quote_requests.find_one({"_id": oid(qid)}))

# --- Price calculator ---
class CalcIn(BaseModel):
    autos: int = Field(ge=1)
    duration_days: int = Field(ge=1)
    estimated_impressions: int = 0
    pricing_model: str = "per_auto"  # per_auto|per_day|per_campaign|cpm|auto_duration|auto_impressions
    plan_id: Optional[str] = None
    discount_code: Optional[str] = None

async def _find_cpm_price(views: int) -> Optional[float]:
    tiers = await db.cpm_tiers.find({"active": True, "views": {"$lte": views}}).sort("views", -1).to_list(1)
    if tiers:
        return float(tiers[0]["price_inr"]) / max(1, tiers[0]["views"]) * views
    # else use smallest available tier as unit price
    smallest = await db.cpm_tiers.find({"active": True}).sort("views", 1).to_list(1)
    if smallest:
        unit = float(smallest[0]["price_inr"]) / max(1, smallest[0]["views"])
        return unit * views
    return None

async def _plan_unit_price(plan) -> float:
    return float(plan.get("price_inr", 0))

async def _get_price_and_settings():
    settings = await db.pricing_settings.find_one({"_id": "singleton"}) or PricingSettingsIn().model_dump()
    settings.pop("_id", None)
    return settings

@api.post("/pricing/calculate")
async def calc_price(payload: CalcIn):
    settings = await _get_price_and_settings()
    subtotal = 0.0
    model = payload.pricing_model
    breakdown = []

    if payload.plan_id:
        plan = await db.plans.find_one({"_id": oid(payload.plan_id), "active": True})
        if not plan: raise HTTPException(404, "Plan not found or inactive")
        pmodel = plan.get("pricing_model", "per_campaign")
        base = float(plan.get("price_inr", 0))
        if pmodel == "per_auto":
            subtotal = base * payload.autos
            breakdown.append({"label": f"{plan['name']} · ₹{base}/auto × {payload.autos} autos", "amount": subtotal})
        elif pmodel == "per_day":
            subtotal = base * payload.duration_days
            breakdown.append({"label": f"{plan['name']} · ₹{base}/day × {payload.duration_days} days", "amount": subtotal})
        elif pmodel == "auto_duration":
            per_auto_per_day = base / max(1, plan.get("autos", 1)) / max(1, plan.get("duration_days", 1))
            subtotal = per_auto_per_day * payload.autos * payload.duration_days
            breakdown.append({"label": f"{plan['name']} · {payload.autos} autos × {payload.duration_days} days", "amount": subtotal})
        else:  # per_campaign default
            subtotal = base
            breakdown.append({"label": plan["name"], "amount": subtotal})
    else:
        if model == "per_auto":
            base = float((await db.plans.find_one({"pricing_model": "per_auto", "active": True}) or {}).get("price_inr", 0))
            subtotal = base * payload.autos * payload.duration_days
            breakdown.append({"label": f"₹{base}/auto/day × {payload.autos} × {payload.duration_days}", "amount": subtotal})
        elif model == "per_day":
            base = float((await db.plans.find_one({"pricing_model": "per_day", "active": True}) or {}).get("price_inr", 0))
            subtotal = base * payload.duration_days
            breakdown.append({"label": f"₹{base}/day × {payload.duration_days} days", "amount": subtotal})
        elif model == "cpm":
            price = await _find_cpm_price(payload.estimated_impressions or 0)
            subtotal = price or 0.0
            breakdown.append({"label": f"CPM · {payload.estimated_impressions:,} impressions", "amount": subtotal})
        elif model == "auto_impressions":
            per_auto = float((await db.plans.find_one({"pricing_model": "per_auto", "active": True}) or {}).get("price_inr", 0))
            cpm = await _find_cpm_price(payload.estimated_impressions or 0) or 0
            subtotal = per_auto * payload.autos * payload.duration_days + cpm
            breakdown.append({"label": f"Auto+Impressions", "amount": subtotal})
        elif model == "auto_duration":
            per_auto = float((await db.plans.find_one({"pricing_model": "per_auto", "active": True}) or {}).get("price_inr", 0))
            subtotal = per_auto * payload.autos * payload.duration_days
            breakdown.append({"label": f"Autos × Duration", "amount": subtotal})
        else:
            subtotal = 0.0
            breakdown.append({"label": "Custom quote", "amount": 0.0})

    # discount
    discount_amount = 0.0
    discount_info = None
    if payload.discount_code:
        d = await db.discounts.find_one({"code": payload.discount_code.upper(), "active": True})
        if d and subtotal >= float(d.get("min_amount_inr", 0)):
            if d["kind"] == "percent":
                discount_amount = subtotal * float(d["value"]) / 100.0
            else:
                discount_amount = min(subtotal, float(d["value"]))
            discount_info = {"code": d["code"], "kind": d["kind"], "value": d["value"]}

    after_discount = max(0, subtotal - discount_amount)
    gst_amount = 0.0
    if settings.get("gst_enabled"):
        gst_amount = after_discount * float(settings.get("gst_percentage", 18.0)) / 100.0
    total = after_discount + gst_amount
    return {
        "currency": settings.get("currency_code", "INR"),
        "symbol": settings.get("currency_symbol", "₹"),
        "subtotal": round(subtotal, 2),
        "discount": round(discount_amount, 2),
        "discount_info": discount_info,
        "gst_enabled": settings.get("gst_enabled", True),
        "gst_percentage": settings.get("gst_percentage", 18.0),
        "gst_amount": round(gst_amount, 2),
        "total": round(total, 2),
        "breakdown": breakdown,
        "model": payload.pricing_model,
    }

# --- Purchase: create campaign with pricing snapshot + Stripe checkout in INR ---
class PurchaseIn(BaseModel):
    plan_id: Optional[str] = None
    autos: int = Field(ge=1)
    duration_days: int = Field(ge=1)
    estimated_impressions: int = 0
    pricing_model: str = "per_auto"
    discount_code: Optional[str] = None
    ad_id: Optional[str] = None
    campaign_name: str
    target_city: str = ""
    origin_url: str

@api.post("/pricing/purchase")
async def purchase_campaign(payload: PurchaseIn, request: Request, user=Depends(require_role("advertiser"))):
    # Compute price
    calc = await calc_price(CalcIn(
        autos=payload.autos, duration_days=payload.duration_days,
        estimated_impressions=payload.estimated_impressions,
        pricing_model=payload.pricing_model, plan_id=payload.plan_id,
        discount_code=payload.discount_code
    ))
    if calc["total"] <= 0:
        raise HTTPException(400, "Price calculation yielded 0 — check pricing config.")

    # Snapshot on campaign
    start = datetime.now(timezone.utc).date()
    end = start + timedelta(days=payload.duration_days)
    campaign_doc = {
        "name": payload.campaign_name, "advertiser_id": user["id"],
        "ad_id": payload.ad_id or "", "start_date": start.isoformat(), "end_date": end.isoformat(),
        "start_time": "00:00", "end_time": "23:59", "budget": calc["total"],
        "objective": "Awareness", "target_locations": [payload.target_city] if payload.target_city else [],
        "target_cities": [payload.target_city] if payload.target_city else [],
        "target_devices": [], "frequency": 3, "status": "Draft",
        "pricing_snapshot": {
            "plan_id": payload.plan_id, "autos": payload.autos, "duration_days": payload.duration_days,
            "estimated_impressions": payload.estimated_impressions,
            "pricing_model": payload.pricing_model, "discount_code": payload.discount_code,
            "subtotal": calc["subtotal"], "discount": calc["discount"],
            "gst_percentage": calc["gst_percentage"], "gst_amount": calc["gst_amount"],
            "total_inr": calc["total"], "currency": "INR", "at": now_iso()
        },
        "created_at": now_iso()
    }
    c_res = await db.campaigns.insert_one(campaign_doc)
    campaign_id = str(c_res.inserted_id)

    # Stripe checkout in INR
    if not _STRIPE_AVAILABLE:
        raise HTTPException(500, "Stripe not available")
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    origin = payload.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=float(calc["total"]), currency="inr",
        success_url=f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/payment/cancel",
        metadata={"user_id": user["id"], "campaign_id": campaign_id, "kind": "campaign_purchase"}
    )
    session = await stripe_checkout.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "campaign_id": campaign_id,
        "amount": float(calc["total"]), "currency": "inr",
        "status": "initiated", "payment_status": "pending",
        "snapshot": campaign_doc["pricing_snapshot"], "campaign_name": payload.campaign_name,
        "created_at": now_iso(), "updated_at": now_iso()
    })
    return {"checkout_url": session.url, "session_id": session.session_id, "campaign_id": campaign_id, "amount_inr": calc["total"]}

@api.get("/invoices/{session_id}")
async def get_invoice(session_id: str, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx: raise HTTPException(404, "Invoice not found")
    if user["role"] != "admin" and tx.get("user_id") != user["id"]:
        raise HTTPException(403, "Not your invoice")
    campaign = None
    if tx.get("campaign_id"):
        c = await db.campaigns.find_one({"_id": oid(tx["campaign_id"])})
        campaign = serialize(c)
    return {"transaction": serialize(tx), "campaign": campaign, "invoice_number": f"OWM-{tx['created_at'][:10].replace('-','')}-{session_id[-6:].upper()}"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # permissive for kiosk devices; JWT enforces access
    allow_methods=["*"],
    allow_headers=["*"],
)
