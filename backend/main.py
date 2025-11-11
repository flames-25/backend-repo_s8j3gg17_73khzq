from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Database helpers (MongoDB) provided by environment
from database import db, create_document, get_documents

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="Bina Ragam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# Schemas
# ======================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = Field(default="user", regex="^(admin|user)$")

class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DiscountCreate(BaseModel):
    percentage: int = Field(..., ge=0, le=100)
    start_date: datetime
    end_date: datetime
    active: bool = True

class DiscountPublic(DiscountCreate):
    id: str
    created_at: datetime

class ProductCreate(BaseModel):
    name: str
    description: str
    image_url: str
    price: float
    marketplace_link: str
    discount_id: Optional[str] = None
    category: Optional[str] = None

class ProductPublic(ProductCreate):
    id: str
    created_at: datetime

class WishlistCreate(BaseModel):
    product_id: str

# ======================
# Utils
# ======================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    users = await get_documents("user", {"_id": user_id}, limit=1)
    if not users:
        raise credentials_exception
    user = users[0]
    return user

async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

# ======================
# Auth Routes
# ======================
@app.post("/auth/register", response_model=UserPublic)
async def register(payload: UserCreate):
    existing = await get_documents("user", {"email": payload.email}, limit=1)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(payload.password)
    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password": hashed,
        "role": payload.role,
    }
    inserted = await create_document("user", user_doc)
    inserted["id"] = str(inserted.pop("_id"))
    inserted.pop("password", None)
    return inserted

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = await get_documents("user", {"email": form_data.username}, limit=1)
    if not users:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user = users[0]
    if not verify_password(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "user")})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserPublic)
async def me(current=Depends(get_current_user)):
    current["id"] = str(current.pop("_id"))
    current.pop("password", None)
    return current

# ======================
# Product Routes
# ======================
@app.post("/products", response_model=ProductPublic, dependencies=[Depends(require_admin)])
async def create_product(payload: ProductCreate):
    doc = payload.dict()
    inserted = await create_document("product", doc)
    inserted["id"] = str(inserted.pop("_id"))
    return inserted

@app.get("/products", response_model=List[ProductPublic])
async def list_products(q: Optional[str] = None, category: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, limit: int = 100):
    filt = {}
    if q:
        filt["name"] = {"$regex": q, "$options": "i"}
    if category:
        filt["category"] = category
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        filt["price"] = price_filter
    docs = await get_documents("product", filt, limit)
    results = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        results.append(d)
    return results

@app.get("/products/{product_id}", response_model=ProductPublic)
async def get_product(product_id: str):
    docs = await get_documents("product", {"_id": product_id}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = docs[0]
    doc["id"] = str(doc.pop("_id"))
    return doc

@app.put("/products/{product_id}", response_model=ProductPublic, dependencies=[Depends(require_admin)])
async def update_product(product_id: str, payload: ProductCreate):
    # Simple replacement update using create_document helper not provided; so using db directly
    await db["product"].update_one({"_id": product_id}, {"$set": payload.dict()})
    docs = await get_documents("product", {"_id": product_id}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = docs[0]
    doc["id"] = str(doc.pop("_id"))
    return doc

@app.delete("/products/{product_id}", dependencies=[Depends(require_admin)])
async def delete_product(product_id: str):
    res = await db["product"].delete_one({"_id": product_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True}

# ======================
# Discount Routes
# ======================
@app.post("/discounts", response_model=DiscountPublic, dependencies=[Depends(require_admin)])
async def create_discount(payload: DiscountCreate):
    inserted = await create_document("discount", payload.dict())
    inserted["id"] = str(inserted.pop("_id"))
    return inserted

@app.get("/discounts", response_model=List[DiscountPublic], dependencies=[Depends(require_admin)])
async def list_discounts(limit: int = 100):
    docs = await get_documents("discount", {}, limit)
    results = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        results.append(d)
    return results

# ======================
# Users (Admin)
# ======================
@app.get("/users", response_model=List[UserPublic], dependencies=[Depends(require_admin)])
async def list_users(limit: int = 100):
    docs = await get_documents("user", {}, limit)
    results = []
    for u in docs:
        u["id"] = str(u.pop("_id"))
        u.pop("password", None)
        results.append(u)
    return results

@app.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: str):
    res = await db["user"].delete_one({"_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}

# Health / test
@app.get("/test")
async def test():
    # Verify DB connection
    await db["__ping__"].insert_one({"ok": True, "ts": datetime.utcnow()})
    return {"status": "ok"}
