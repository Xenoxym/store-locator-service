from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine

from app.models import Store, StoreService, User, Role, Permission, RolePermission, RefreshToken
from app.api.stores import router as stores_router
from app.api.auth import router as auth_router
from app.api.admin_stores import router as admin_stores_router
from app.core.redis_client import check_redis_connection


# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Store Locator Service",
    description="Final Project: Store search and store management API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Demo setting. For production, restrict to your frontend domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stores_router)
app.include_router(auth_router)
app.include_router(admin_stores_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "redis": "ok" if check_redis_connection() else "unavailable",
    }


@app.get("/")
def root():
    return {
        "message": "Store Locator Service API",
        "docs": "/docs",
        "health": "/health",
    }