from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from backend.app.db import models


def get_document(db: Session, document_id: int) -> Optional[models.Document]:
    return db.query(models.Document).filter(models.Document.id == document_id).first()


def get_tag_by_name(db: Session, name: str) -> Optional[models.Tag]:
    return db.query(models.Tag).filter(models.Tag.name == name).first()


def get_settings_field_by_name(db: Session, name: str) -> Optional[models.SettingsField]:
    return db.query(models.SettingsField).filter(models.SettingsField.name == name).first()


def list_settings_fields(db: Session) -> List[models.SettingsField]:
    return db.query(models.SettingsField).order_by(models.SettingsField.created_at.asc(), models.SettingsField.id.asc()).all()


def create_settings_field(db: Session, *, name: str, field_type: str) -> models.SettingsField:
    field = models.SettingsField(name=name, field_type=field_type)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def delete_settings_field(db: Session, *, name: str) -> bool:
    field = get_settings_field_by_name(db, name)
    if not field:
        return False
    db.delete(field)
    db.commit()
    return True


def list_tags(db: Session) -> List[models.Tag]:
    return db.query(models.Tag).order_by(models.Tag.created_at.desc(), models.Tag.id.desc()).all()


def create_tag(db: Session, *, name: str) -> models.Tag:
    tag = models.Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, *, name: str) -> bool:
    tag = get_tag_by_name(db, name)
    if not tag:
        return False
    db.delete(tag)
    db.commit()
    return True


def ensure_shadow_document(db: Session, *, source_document_id: str, fallback_filename: str, fallback_path: str) -> models.Document:
    shadow = (
        db.query(models.Document)
        .options(joinedload(models.Document.custom_fields).joinedload(models.DocumentCustomField.settings_field))
        .filter(models.Document.source_document_id == source_document_id)
        .first()
    )
    if shadow:
        return shadow

    shadow = models.Document(
        source_document_id=source_document_id,
        filename=fallback_filename or source_document_id,
        display_filename=fallback_filename or source_document_id,
        path=fallback_path or "",
        recognized_text="",
        boxes_json="[]",
        created_at=datetime.utcnow(),
        is_archived=False,
        archived_at=None,
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)
    return shadow


def get_document_custom_fields_map(db: Session, *, source_document_id: str) -> Dict[str, object]:
    shadow = (
        db.query(models.Document)
        .options(joinedload(models.Document.custom_fields).joinedload(models.DocumentCustomField.settings_field))
        .filter(models.Document.source_document_id == source_document_id)
        .first()
    )
    if not shadow:
        return {}

    values: Dict[str, object] = {}
    for item in shadow.custom_fields:
        if not item.settings_field or not item.settings_field.name:
            continue
        name = item.settings_field.name
        if item.settings_field.field_type == "number":
            try:
                values[name] = float(item.value) if item.value is not None else None
            except (TypeError, ValueError):
                values[name] = None
        else:
            values[name] = item.value
    return values


def set_document_custom_fields(
    db: Session,
    *,
    source_document_id: str,
    fallback_filename: str,
    fallback_path: str,
    values: Dict[str, object],
) -> Dict[str, object]:
    shadow = ensure_shadow_document(
        db,
        source_document_id=source_document_id,
        fallback_filename=fallback_filename,
        fallback_path=fallback_path,
    )

    settings_fields = {field.name: field for field in list_settings_fields(db)}
    existing_items = {
        item.settings_field.name: item
        for item in db.query(models.DocumentCustomField)
        .options(joinedload(models.DocumentCustomField.settings_field))
        .filter(models.DocumentCustomField.document_id == shadow.id)
        .all()
        if item.settings_field and item.settings_field.name
    }

    for field_name, field in settings_fields.items():
        raw_value = values.get(field_name)
        if raw_value is None:
            serialized_value = None
        elif field.field_type == "number":
            serialized_value = str(raw_value)
        else:
            serialized_value = str(raw_value)

        existing = existing_items.get(field_name)
        if existing:
            existing.value = serialized_value
            continue

        db.add(
            models.DocumentCustomField(
                document_id=shadow.id,
                settings_field_id=field.id,
                value=serialized_value,
            )
        )

    db.commit()
    return get_document_custom_fields_map(db, source_document_id=source_document_id)


def build_settings_payload(db: Session) -> Dict[str, List[Dict[str, object]]]:
    fields = list_settings_fields(db)
    return {
        "fields_for_cards": [
            {
                "name": field.name,
                "type": field.field_type,
                "created_at": field.created_at,
            }
            for field in fields
        ]
    }


def merge_custom_fields_for_document(
    db: Session,
    *,
    source_document_id: str,
    existing_custom_fields: Optional[Dict[str, object]],
) -> Dict[str, object]:
    settings = list_settings_fields(db)
    sqlite_values = get_document_custom_fields_map(db, source_document_id=source_document_id)
    merged: Dict[str, object] = dict(existing_custom_fields or {})

    for field in settings:
        if field.name not in merged:
            merged[field.name] = None
    merged.update(sqlite_values)
    return merged


def merge_custom_fields_for_documents(
    db: Session,
    docs: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    for doc in docs:
        source_document_id = doc.get("_id")
        if not source_document_id:
            continue
        doc["custom_fields"] = merge_custom_fields_for_document(
            db,
            source_document_id=source_document_id,
            existing_custom_fields=doc.get("custom_fields") if isinstance(doc.get("custom_fields"), dict) else {},
        )
    return docs


def remove_tag_from_shadow_documents(db: Session, *, tag_name: str) -> None:
    shadow_docs = db.query(models.Document).options(joinedload(models.Document.tags)).all()
    for doc in shadow_docs:
        doc.tags = [tag for tag in doc.tags if tag.name != tag_name]
    db.commit()
