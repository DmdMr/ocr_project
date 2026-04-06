import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.auth import bootstrap_first_admin
from backend.app.db.database import activity_logs_collection, documents_collection, folders_collection, sessions_collection, users_collection
from backend.app.services.folder_service import ensure_unsorted_folder

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
    await users_collection.create_index("role")
    await sessions_collection.create_index("session_id", unique=True)
    await sessions_collection.create_index("expires_at", expireAfterSeconds=0)
    await activity_logs_collection.create_index("created_at")
    await activity_logs_collection.create_index("action")
    await activity_logs_collection.create_index("actor.user_id")
    await folders_collection.create_index("parent_id")
    await folders_collection.create_index("is_system")
    await folders_collection.create_index("system_key", unique=True, sparse=True)
    await folders_collection.create_index([("parent_id", 1), ("name", 1)])
    await documents_collection.create_index("folder_id")
    await bootstrap_first_admin()
    await ensure_unsorted_folder(folders_collection, documents_collection)


app.include_router(router)
app.mount("/uploads", StaticFiles(directory="backend/uploads"), name="uploads")
