import os
from datetime import datetime, timedelta, timezone
from typing import Iterable


def get_document_filenames(document: dict) -> list[str]:
    gallery_images = document.get("gallery_images") or []
    gallery_filenames = [item.get("filename") for item in gallery_images if item.get("filename")]
    attachments = document.get("attachments") or []
    attachment_filenames = [item.get("filename") for item in attachments if item.get("filename")]

    filenames = set(gallery_filenames + attachment_filenames)
    if document.get("filename"):
        filenames.add(document.get("filename"))

    return sorted(filenames)


def remove_files_from_disk(filenames: Iterable[str], upload_dir: str) -> list[str]:
    removed_files: list[str] = []
    for filename in filenames:
        file_path = os.path.join(upload_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            removed_files.append(filename)
    return removed_files


async def permanently_delete_document(document: dict, documents_collection, upload_dir: str):
    filenames_to_delete = get_document_filenames(document)
    removed_files = remove_files_from_disk(filenames_to_delete, upload_dir)
    await documents_collection.delete_one({"_id": document["_id"]})
    return removed_files


def archive_cutoff_utc(retention_days: int = 30):
    return datetime.now(timezone.utc) - timedelta(days=retention_days)


async def cleanup_expired_archived_documents(documents_collection, upload_dir: str, retention_days: int = 30):
    cutoff = archive_cutoff_utc(retention_days=retention_days)
    removed_count = 0

    cursor = documents_collection.find(
        {
            "is_archived": True,
            "archived_at": {"$ne": None, "$lte": cutoff},
        }
    )
    async for document in cursor:
        await permanently_delete_document(document, documents_collection, upload_dir)
        removed_count += 1

    return removed_count
