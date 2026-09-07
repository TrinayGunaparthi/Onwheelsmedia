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
async def player_playlist(dev=Depends(get_current_device)):
    device_id = str(dev["_id"])
    # Find active campaigns targeting this device (or global) whose ad is approved
    today = datetime.now(timezone.utc).date().isoformat()
    campaigns = await db.campaigns.find({
        "status": {"$in": ["Active", "Scheduled"]},
        "$or": [{"target_devices": device_id}, {"target_devices": []}],
        "start_date": {"$lte": today},
        "end_date": {"$gte": today},
    }).to_list(200)
    items = []
    for c in campaigns:
        ad = await db.ads.find_one({"_id": oid(c["ad_id"])}) if c.get("ad_id") else None
        if ad and ad.get("status") == "Approved":
            items.append({
                "type": "ad", "id": str(ad["_id"]), "campaign_id": str(c["_id"]),
                "name": ad["name"], "file_url": ad["file_url"], "file_type": ad["file_type"],
                "duration": ad.get("duration_seconds", 15)
            })
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
    return {"device_code": dev["device_code"], "items": items, "generated_at": now_iso()}

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

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # permissive for kiosk devices; JWT enforces access
    allow_methods=["*"],
    allow_headers=["*"],
)
