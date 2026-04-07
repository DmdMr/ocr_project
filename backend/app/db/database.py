from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"

client = AsyncIOMotorClient(MONGO_URL)
db = client["ocr_database"]

documents_collection = db["documents"]
tags_collection = db["tags"]
app_settings_collection = db["app_settings"]
users_collection = db["users"]
sessions_collection = db["sessions"]
activity_logs_collection = db["activity_logs"]
folders_collection = db["folders"]


