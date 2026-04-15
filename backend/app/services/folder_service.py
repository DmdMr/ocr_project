from datetime import datetime, timezone

from bson import ObjectId


UNSORTED_FOLDER_NAME = "Unsorted"
UNSORTED_SYSTEM_KEY = "unsorted"


def now_utc():
    return datetime.now(timezone.utc)


async def ensure_unsorted_indexes(folders_collection):
    await folders_collection.create_index([("name", 1), ("parent_id", 1)], unique=True)
    await folders_collection.create_index("parent_id")
    await folders_collection.create_index("is_system")
    await folders_collection.create_index(
        [("is_system", 1), ("name", 1), ("parent_id", 1)],
        unique=True,
        partialFilterExpression={"is_system": True},
    )


async def ensure_unsorted_folder(folders_collection):
    existing = await folders_collection.find_one(
        {"is_system": True, "name": UNSORTED_FOLDER_NAME, "parent_id": None}
    )
    if existing:
        return existing["_id"]

    now = now_utc()
    folder = {
        "_id": ObjectId(),
        "name": UNSORTED_FOLDER_NAME,
        "parent_id": None,
        "is_system": True,
        "created_at": now,
        "updated_at": now,
    }
    await folders_collection.insert_one(folder)
    return folder["_id"]
