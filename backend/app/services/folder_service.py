from datetime import datetime, timedelta, timezone

from bson import ObjectId

UNSORTED_FOLDER_NAME = "Unsorted"
UNSORTED_SYSTEM_KEY = "unsorted"
YEKATERINBURG_TZ = timezone(timedelta(hours=5))


def now_yekaterinburg():
    return datetime.now(YEKATERINBURG_TZ)


async def ensure_unsorted_folder(folders_collection, documents_collection):
    now = now_yekaterinburg()
    unsorted = await folders_collection.find_one({"system_key": UNSORTED_SYSTEM_KEY})

    if not unsorted:
        unsorted = {
            "_id": str(ObjectId()),
            "name": UNSORTED_FOLDER_NAME,
            "parent_id": None,
            "is_system": True,
            "system_key": UNSORTED_SYSTEM_KEY,
            "created_at": now,
            "updated_at": now,
            "created_by_user_id": None,
            "created_by_username": None,
        }
        await folders_collection.insert_one(unsorted)
    else:
        await folders_collection.update_one(
            {"_id": unsorted["_id"]},
            {
                "$set": {
                    "name": UNSORTED_FOLDER_NAME,
                    "parent_id": None,
                    "is_system": True,
                    "system_key": UNSORTED_SYSTEM_KEY,
                    "updated_at": now,
                }
            },
        )
        unsorted = await folders_collection.find_one({"_id": unsorted["_id"]})

    unsorted_id = unsorted["_id"]
    await documents_collection.update_many(
        {
            "$or": [
                {"folder_id": {"$exists": False}},
                {"folder_id": None},
                {"folder_id": ""},
            ]
        },
        {"$set": {"folder_id": unsorted_id}},
    )

    return unsorted
