import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.getenv("SQLITE_DB_PATH", "backend/app/data/ocr_app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Document(Base):
    __tablename__ = "documents"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Tag(Base):
    __tablename__ = "tags"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Folder(Base):
    __tablename__ = "folders"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Settings(Base):
    __tablename__ = "app_settings"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class SessionRecord(Base):
    __tablename__ = "sessions"
    _id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


MODEL_MAP = {
    "users": User,
    "documents": Document,
    "tags": Tag,
    "folders": Folder,
    "app_settings": Settings,
    "activity_logs": ActivityLog,
    "sessions": SessionRecord,
}


def _match(document: dict, query: dict) -> bool:
    if not query:
        return True
    for k, v in query.items():
        if k == "$or":
            if not any(_match(document, q) for q in v):
                return False
            continue
        current = document.get(k)
        if isinstance(v, dict):
            if "$gt" in v and not (current is not None and current > v["$gt"]):
                return False
            if "$in" in v and current not in v["$in"]:
                return False
            if "$exists" in v:
                exists = k in document
                if bool(v["$exists"]) != exists:
                    return False
            if "$ne" in v and current == v["$ne"]:
                return False
        elif current != v:
            return False
    return True


@dataclass
class InsertOneResult:
    inserted_id: str


class Cursor:
    def __init__(self, docs: list[dict]):
        self.docs = docs

    def sort(self, key, direction=None):
        if isinstance(key, list):
            for k, d in reversed(key):
                self.docs.sort(key=lambda x: x.get(k), reverse=d == -1)
        else:
            self.docs.sort(key=lambda x: x.get(key), reverse=direction == -1)
        return self

    def limit(self, n: int):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self.docs):
            raise StopAsyncIteration
        d = self.docs[self._i]
        self._i += 1
        return d


class SQLiteCollection:
    def __init__(self, name: str):
        self.model = MODEL_MAP[name]

    async def create_index(self, *args, **kwargs):
        return None

    async def find_one(self, query: dict, projection: Optional[dict] = None):
        with SessionLocal() as s:
            rows = s.execute(select(self.model)).scalars().all()
            for r in rows:
                d = {"_id": r._id, **(r.data or {})}
                if _match(d, query):
                    return d
        return None

    def find(self, query: Optional[dict] = None, projection: Optional[dict] = None):
        with SessionLocal() as s:
            rows = s.execute(select(self.model)).scalars().all()
            docs = []
            for r in rows:
                d = {"_id": r._id, **(r.data or {})}
                if _match(d, query or {}):
                    docs.append(d)
        return Cursor(docs)

    async def insert_one(self, doc: dict):
        payload = dict(doc)
        _id = str(payload.pop("_id", uuid.uuid4().hex))
        with SessionLocal() as s:
            s.add(self.model(_id=_id, data=payload))
            s.commit()
        return InsertOneResult(inserted_id=_id)

    async def update_one(self, query: dict, update: dict):
        return await self._update(query, update, multi=False)

    async def update_many(self, query: dict, update: dict):
        return await self._update(query, update, multi=True)

    async def _update(self, query: dict, update: dict, multi: bool):
        with SessionLocal() as s:
            rows = s.execute(select(self.model)).scalars().all()
            for r in rows:
                d = {"_id": r._id, **(r.data or {})}
                if _match(d, query):
                    if "$set" in update:
                        d.update(update["$set"])
                    if "$pull" in update:
                        for key, value in update["$pull"].items():
                            arr = d.get(key, [])
                            d[key] = [x for x in arr if x != value]
                    r.data = {k: v for k, v in d.items() if k != "_id"}
                    if not multi:
                        s.commit(); return
            s.commit()

    async def delete_one(self, query: dict):
        with SessionLocal() as s:
            rows = s.execute(select(self.model)).scalars().all()
            for r in rows:
                d = {"_id": r._id, **(r.data or {})}
                if _match(d, query):
                    s.delete(r)
                    s.commit()
                    return

    async def count_documents(self, query: dict, limit: Optional[int] = None):
        count = 0
        async for _ in self.find(query):
            count += 1
            if limit and count >= limit:
                break
        return count


def init_db():
    Base.metadata.create_all(bind=engine)


documents_collection = SQLiteCollection("documents")
tags_collection = SQLiteCollection("tags")
app_settings_collection = SQLiteCollection("app_settings")
users_collection = SQLiteCollection("users")
sessions_collection = SQLiteCollection("sessions")
activity_logs_collection = SQLiteCollection("activity_logs")
folders_collection = SQLiteCollection("folders")
