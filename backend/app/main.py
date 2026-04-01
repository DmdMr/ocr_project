from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.config import settings
from backend.app.db.database import sessions_collection, users_collection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
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
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
