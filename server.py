"""DISHA - Local Services OS backend.

Stack: FastAPI + MongoDB.
Every route uses /api prefix. Responses do not expose MongoDB ObjectId.
"""
from __future__ import annotations

import os
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Literal, Optional

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("disha")

APP_ENV = os.environ.get("APP_ENV", "development").lower().strip()
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    if APP_ENV == "production":
        raise RuntimeError("JWT_SECRET is required when APP_ENV=production")
    JWT_SECRET = "disha-dev-secret-change-me"
    log.warning("JWT_SECRET is missing; using development fallback. Never use this in production.")
JWT_ALG = "HS256"
JWT_TTL = timedelta(days=7)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "disha")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
AUTO_APPROVE_PROVIDERS = os.environ.get("AUTO_APPROVE_PROVIDERS", "false").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:8081,http://localhost:19006,http://localhost:3000"
).split(",") if o.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = ["http://localhost:8081"]
CORS_ALLOW_CREDENTIALS = "*" not in CORS_ORIGINS
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_col = db.users
categories_col = db.categories
providers_col = db.providers
bookings_col = db.bookings
messages_col = db.messages
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="DISHA API")
api = APIRouter(prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now() -> datetime:
    return datetime.now(timezone.utc)

def iso() -> str:
    return now().isoformat()

def uid() -> str:
    return str(uuid.uuid4())

def make_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": now() + JWT_TTL}, JWT_SECRET, algorithm=JWT_ALG)

def safe_user(u: dict) -> dict:
    return {"id": u["id"], "name": u["name"], "email": u.get("email"), "mobile": u.get("mobile"), "purpose": u.get("purpose"), "termsAcceptedAt": u.get("terms_accepted_at")}

async def current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await users_col.find_one({"id": payload.get("sub"), "is_active": True}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User inactive or not found")
    return user

async def admin_required(x_admin_key: Optional[str] = Header(None)) -> bool:
    if not ADMIN_KEY:
        raise HTTPException(503, "Admin key is not configured")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(401, "Invalid admin key")
    return True

Purpose = Literal["TAKER", "PROVIDER", "BOTH"]
BookingStatus = Literal["PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "COMPLETED"]
ProviderModerationStatus = Literal["PENDING", "APPROVED", "REJECTED", "SUSPENDED"]

class RegisterBody(BaseModel):
    name: str = Field(min_length=2)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    password: str = Field(min_length=6)
    purpose: Optional[Purpose] = None
    termsAccepted: bool

    @field_validator("mobile")
    @classmethod
    def valid_mobile(cls, value):
        if value in (None, ""):
            return None
        if not MOBILE_RE.match(value):
            raise ValueError("Invalid mobile")
        return value

    @model_validator(mode="after")
    def valid_identity(self):
        if not (self.email or self.mobile):
            raise ValueError("Email or mobile required")
        if not self.termsAccepted:
            raise ValueError("Terms must be accepted")
        return self

class LoginBody(BaseModel):
    identifier: str = Field(min_length=3)
    password: str = Field(min_length=6)

class PurposeBody(BaseModel):
    purpose: Purpose

class ServiceIn(BaseModel):
    categoryId: str
    title: str = Field(min_length=1)
    price: Optional[str] = ""
    description: Optional[str] = ""

class ProviderIn(BaseModel):
    displayName: str = Field(min_length=2)
    area: str = Field(min_length=2)
    city: str = "Kalna"
    mobile: str
    whatsapp: Optional[str] = ""
    availableTime: Optional[str] = ""
    services: List[ServiceIn] = Field(min_length=1)

    @field_validator("mobile", "whatsapp")
    @classmethod
    def valid_phone(cls, value, info):
        if value in (None, "") and info.field_name == "whatsapp":
            return ""
        if not MOBILE_RE.match(value):
            raise ValueError(f"Valid {info.field_name} required")
        return value

class BookingIn(BaseModel):
    providerId: str
    serviceName: str = Field(min_length=1)
    date: datetime
    note: Optional[str] = ""

class BookingStatusIn(BaseModel):
    status: BookingStatus

class ProviderStatusIn(BaseModel):
    status: ProviderModerationStatus

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    customerId: Optional[str] = None

async def provider_public(p: dict) -> dict:
    return {"id": p["id"], "displayName": p["display_name"], "area": p["area"], "city": p["city"], "mobile": p["mobile"], "whatsapp": p.get("whatsapp") or "", "availableTime": p.get("available_time") or "", "verified": bool(p.get("verified")), "status": p.get("status", "PENDING"), "services": p.get("services", [])}

async def booking_public(b: dict) -> dict:
    return {"id": b["id"], "providerId": b["provider_id"], "providerName": b.get("provider_name"), "serviceName": b["service_name"], "date": b["date"], "note": b.get("note", ""), "status": b["status"], "createdAt": b["created_at"], "userName": b.get("user_name"), "userMobile": b.get("user_mobile")}

@app.on_event("startup")
async def startup():
    await users_col.create_index("id", unique=True)
    await users_col.create_index("email", unique=True, sparse=True)
    await users_col.create_index("mobile", unique=True, sparse=True)
    await categories_col.create_index("id", unique=True)
    await providers_col.create_index("id", unique=True)
    await bookings_col.create_index("id", unique=True)
    await messages_col.create_index("id", unique=True)
    defaults = [
        ("Salon", "সেলুন", "💇"), ("Car Rental", "গাড়ি ভাড়া", "🚕"), ("Courier", "কুরিয়ার", "📦"),
        ("Cyber Cafe", "সাইবার ক্যাফে", "🖨️"), ("Beauty Parlour", "বিউটি পার্লার", "💄"),
        ("Electrician", "ইলেকট্রিশিয়ান", "⚡"), ("Plumber", "প্লাম্বার", "🔧"), ("Tuition", "টিউশন", "📚"),
        ("Grocery", "গ্রোসারি", "🛒"), ("Driver", "ড্রাইভার", "🚗")]
    for name, name_bn, icon in defaults:
        await categories_col.update_one({"name": name}, {"$setOnInsert": {"id": uid(), "name": name, "name_bn": name_bn, "icon": icon, "is_active": True}}, upsert=True)

@api.get("/health")
async def health():
    return {"ok": True, "app": "DISHA API", "company": "ASTRA Technologies", "time": iso()}

@api.post("/auth/register")
async def register(body: RegisterBody):
    checks = []
    if body.email: checks.append({"email": body.email})
    if body.mobile: checks.append({"mobile": body.mobile})
    if checks and await users_col.find_one({"$or": checks}):
        raise HTTPException(409, "Email or mobile already registered")
    u = {"id": uid(), "name": body.name.strip(), "email": body.email, "mobile": body.mobile, "password_hash": pwd.hash(body.password), "purpose": body.purpose, "terms_accepted_at": iso(), "is_active": True, "created_at": iso()}
    await users_col.insert_one(u)
    return {"ok": True, "token": make_token(u["id"]), "user": safe_user(u)}

@api.post("/auth/login")
async def login(body: LoginBody):
    u = await users_col.find_one({"is_active": True, "$or": [{"email": body.identifier}, {"mobile": body.identifier}]}, {"_id": 0})
    if not u or not pwd.verify(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid login")
    return {"ok": True, "token": make_token(u["id"]), "user": safe_user(u)}

@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return {"ok": True, "user": safe_user(user)}

@api.patch("/auth/purpose")
async def set_purpose(body: PurposeBody, user: dict = Depends(current_user)):
    await users_col.update_one({"id": user["id"]}, {"$set": {"purpose": body.purpose}})
    user["purpose"] = body.purpose
    return {"ok": True, "user": safe_user(user)}

@api.delete("/auth/delete-account")
async def delete_account(user: dict = Depends(current_user)):
    await users_col.update_one({"id": user["id"]}, {"$set": {"is_active": False}})
    return {"ok": True, "message": "Account deletion request accepted"}

@api.get("/categories")
async def list_categories():
    data = await categories_col.find({"is_active": True}, {"_id": 0}).sort("name_bn", 1).to_list(200)
    return {"ok": True, "data": data}

@api.get("/providers/me/profile")
async def my_provider_profile(user: dict = Depends(current_user)):
    p = await providers_col.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"ok": True, "data": await provider_public(p) if p else None}

@api.put("/providers/me/profile")
async def upsert_provider_profile(body: ProviderIn, user: dict = Depends(current_user)):
    cat_ids = list({s.categoryId for s in body.services})
    cats = {c["id"]: c async for c in categories_col.find({"id": {"$in": cat_ids}}, {"_id": 0})}
    missing = [cid for cid in cat_ids if cid not in cats]
    if missing:
        raise HTTPException(400, f"Invalid category {missing[0]}")
    services = [{"id": uid(), "categoryId": s.categoryId, "title": s.title.strip(), "price": (s.price or "").strip(), "description": (s.description or "").strip(), "category": cats[s.categoryId]} for s in body.services]
    existing = await providers_col.find_one({"user_id": user["id"]}, {"_id": 0})
    next_status = "APPROVED" if AUTO_APPROVE_PROVIDERS else "PENDING"
    data = {"display_name": body.displayName.strip(), "area": body.area.strip(), "city": body.city.strip(), "mobile": body.mobile, "whatsapp": body.whatsapp or "", "available_time": body.availableTime or "", "services": services, "status": next_status, "verified": AUTO_APPROVE_PROVIDERS, "updated_at": iso()}
    if existing:
        pid = existing["id"]
        await providers_col.update_one({"id": pid}, {"$set": data})
    else:
        pid = uid()
        data.update({"id": pid, "user_id": user["id"], "verified": False, "created_at": iso()})
        await providers_col.insert_one(data)
    await users_col.update_one({"id": user["id"]}, {"$set": {"purpose": "PROVIDER"}})
    p = await providers_col.find_one({"id": pid}, {"_id": 0})
    return {"ok": True, "data": await provider_public(p)}

@api.get("/admin/providers/pending")
async def admin_pending_providers(_: bool = Depends(admin_required)):
    cur = providers_col.find({"status": "PENDING"}, {"_id": 0}).sort("updated_at", -1)
    return {"ok": True, "data": [await provider_public(p) async for p in cur]}

@api.patch("/admin/providers/{provider_id}/status")
async def admin_update_provider_status(provider_id: str, body: ProviderStatusIn, _: bool = Depends(admin_required)):
    p = await providers_col.find_one({"id": provider_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Provider not found")
    await providers_col.update_one(
        {"id": provider_id},
        {"$set": {"status": body.status, "verified": body.status == "APPROVED", "moderated_at": iso()}},
    )
    p = await providers_col.find_one({"id": provider_id}, {"_id": 0})
    return {"ok": True, "data": await provider_public(p)}

@api.get("/providers")
async def list_providers(city: str = "Kalna", q: Optional[str] = None, categoryId: Optional[str] = None, limit: int = Query(20, ge=1, le=50)):
    query = {"status": "APPROVED", "city": city}
    if categoryId:
        query["services.categoryId"] = categoryId
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"display_name": rx}, {"area": rx}, {"services.title": rx}]
    cur = providers_col.find(query, {"_id": 0}).sort([("verified", -1), ("updated_at", -1)]).limit(limit)
    return {"ok": True, "data": [await provider_public(p) async for p in cur]}

@api.get("/providers/{provider_id}")
async def get_provider(provider_id: str):
    p = await providers_col.find_one({"id": provider_id, "status": "APPROVED"}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Provider not found")
    return {"ok": True, "data": await provider_public(p)}

@api.post("/bookings")
async def create_booking(body: BookingIn, user: dict = Depends(current_user)):
    provider = await providers_col.find_one({"id": body.providerId, "status": "APPROVED"}, {"_id": 0})
    if not provider:
        raise HTTPException(404, "Provider not found")
    if body.date < now() - timedelta(minutes=1):
        raise HTTPException(400, "Past date not allowed")
    b = {"id": uid(), "user_id": user["id"], "user_name": user["name"], "user_mobile": user.get("mobile") or "", "provider_id": provider["id"], "provider_name": provider["display_name"], "service_name": body.serviceName.strip(), "date": body.date.isoformat(), "note": (body.note or "").strip(), "status": "PENDING", "created_at": iso()}
    await bookings_col.insert_one(b)
    return {"ok": True, "data": await booking_public(b)}

@api.get("/bookings/me")
async def my_bookings(user: dict = Depends(current_user)):
    cur = bookings_col.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    return {"ok": True, "data": [await booking_public(b) async for b in cur]}

@api.get("/bookings/provider")
async def provider_bookings(user: dict = Depends(current_user)):
    provider = await providers_col.find_one({"user_id": user["id"]}, {"_id": 0})
    if not provider: return {"ok": True, "data": []}
    cur = bookings_col.find({"provider_id": provider["id"]}, {"_id": 0}).sort("created_at", -1)
    return {"ok": True, "data": [await booking_public(b) async for b in cur]}

@api.patch("/bookings/{booking_id}/status")
async def update_booking_status(booking_id: str, body: BookingStatusIn, user: dict = Depends(current_user)):
    b = await bookings_col.find_one({"id": booking_id}, {"_id": 0})
    if not b: raise HTTPException(404, "Booking not found")
    provider = await providers_col.find_one({"id": b["provider_id"]}, {"_id": 0})
    is_customer = b["user_id"] == user["id"]
    is_owner = bool(provider and provider["user_id"] == user["id"])
    if not (is_customer or is_owner): raise HTTPException(403, "Forbidden")
    if body.status == "CANCELLED" and not is_customer: raise HTTPException(403, "Only customer can cancel")
    if body.status in ("ACCEPTED", "REJECTED", "COMPLETED") and not is_owner: raise HTTPException(403, "Only provider can update this status")
    await bookings_col.update_one({"id": booking_id}, {"$set": {"status": body.status}})
    b["status"] = body.status
    return {"ok": True, "data": await booking_public(b)}

@api.get("/chat/summary")
async def chat_summary(user: dict = Depends(current_user)):
    unread = await messages_col.count_documents({"recipient_id": user["id"], "read": False})
    return {"ok": True, "data": {"unread": unread}}

@api.get("/chat/threads")
async def chat_threads(user: dict = Depends(current_user)):
    threads = []
    for pid in await messages_col.distinct("provider_id", {"customer_id": user["id"]}):
        p = await providers_col.find_one({"id": pid}, {"_id": 0})
        last = await messages_col.find_one({"provider_id": pid, "customer_id": user["id"]}, {"_id": 0}, sort=[("created_at", -1)])
        if p:
            threads.append({"providerId": pid, "providerName": p["display_name"], "lastMessage": last["text"] if last else "", "lastAt": last["created_at"] if last else "", "role": "TAKER"})
    my_provider = await providers_col.find_one({"user_id": user["id"]}, {"_id": 0})
    if my_provider:
        for cid in await messages_col.distinct("customer_id", {"provider_id": my_provider["id"]}):
            other = await users_col.find_one({"id": cid}, {"_id": 0})
            last = await messages_col.find_one({"provider_id": my_provider["id"], "customer_id": cid}, {"_id": 0}, sort=[("created_at", -1)])
            if other:
                threads.append({"providerId": my_provider["id"], "providerName": other["name"] + " → " + my_provider["display_name"], "customerId": cid, "lastMessage": last["text"] if last else "", "lastAt": last["created_at"] if last else "", "role": "PROVIDER"})
    threads.sort(key=lambda t: t.get("lastAt", ""), reverse=True)
    return {"ok": True, "data": threads}

@api.get("/chat/{provider_id}")
async def get_messages(provider_id: str, customerId: Optional[str] = None, user: dict = Depends(current_user)):
    provider = await providers_col.find_one({"id": provider_id}, {"_id": 0})
    if not provider: raise HTTPException(404, "Provider not found")
    is_owner = provider["user_id"] == user["id"]
    customer_id = customerId if is_owner and customerId else user["id"]
    if is_owner and not customerId: raise HTTPException(400, "customerId required for provider chat view")
    await messages_col.update_many({"provider_id": provider_id, "customer_id": customer_id, "recipient_id": user["id"], "read": False}, {"$set": {"read": True}})
    cur = messages_col.find({"provider_id": provider_id, "customer_id": customer_id}, {"_id": 0}).sort("created_at", 1)
    data = [{"id": m["id"], "text": m["text"], "senderId": m["sender_id"], "senderName": m.get("sender_name", "User"), "createdAt": m["created_at"], "mine": m["sender_id"] == user["id"]} async for m in cur]
    return {"ok": True, "data": data}

@api.post("/chat/{provider_id}")
async def send_message(provider_id: str, body: MessageIn, user: dict = Depends(current_user)):
    provider = await providers_col.find_one({"id": provider_id}, {"_id": 0})
    if not provider: raise HTTPException(404, "Provider not found")
    is_owner = provider["user_id"] == user["id"]
    if is_owner:
        if not body.customerId: raise HTTPException(400, "customerId required to reply as provider")
        recipient_id = body.customerId
        customer_id = body.customerId
    else:
        recipient_id = provider["user_id"]
        customer_id = user["id"]
    msg = {"id": uid(), "provider_id": provider_id, "customer_id": customer_id, "sender_id": user["id"], "sender_name": user["name"], "recipient_id": recipient_id, "text": body.text.strip(), "read": False, "created_at": iso()}
    await messages_col.insert_one(msg)
    return {"ok": True, "data": {"id": msg["id"], "text": msg["text"], "senderId": msg["sender_id"], "senderName": msg["sender_name"], "createdAt": msg["created_at"], "mine": True}}

@api.get("/legal/privacy-policy")
async def privacy_policy():
    return {"ok": True, "title": "Privacy Policy", "company": "ASTRA Technologies"}

@api.get("/legal/terms")
async def terms():
    return {"ok": True, "title": "Terms & Conditions", "company": "ASTRA Technologies"}

app.include_router(api)
