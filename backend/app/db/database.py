from motor.motor_asyncio import AsyncIOMotorClient

from backend.app.config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db_name]

documents_collection = db["documents"]
tags_collection = db["tags"]
app_settings_collection = db["app_settings"]
users_collection = db["users"]
sessions_collection = db["sessions"]



