import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.db.database import sessions_collection, users_collection

app = FastAPI()

raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def setup_indexes():
    await users_collection.create_index("username_lower", unique=True)
    await sessions_collection.create_index("session_id", unique=True)
    await sessions_collection.create_index("expires_at", expireAfterSeconds=0)


app.include_router(router)
app.mount("/uploads", StaticFiles(directory="backend/uploads"), name="uploads")
