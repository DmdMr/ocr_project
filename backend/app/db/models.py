from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.db.database import Base


document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    source_document_id = Column(String(64), nullable=True, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    display_filename = Column(String(255), nullable=False)
    path = Column(String(1024), nullable=False)
    recognized_text = Column(Text, nullable=False, default="")
    boxes_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime, nullable=True)

    tags = relationship("Tag", secondary=document_tags, back_populates="documents")
    custom_fields = relationship(
        "DocumentCustomField",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    attachments = relationship(
        "Attachment",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", secondary=document_tags, back_populates="tags")


class SettingsField(Base):
    __tablename__ = "settings_fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True, index=True)
    field_type = Column(String(32), nullable=False, default="text")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    values = relationship("DocumentCustomField", back_populates="settings_field")


class DocumentCustomField(Base):
    __tablename__ = "document_custom_fields"
    __table_args__ = (
        UniqueConstraint("document_id", "settings_field_id", name="uq_document_settings_field"),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    settings_field_id = Column(Integer, ForeignKey("settings_fields.id", ondelete="CASCADE"), nullable=False)
    value = Column(Text, nullable=True)

    document = relationship("Document", back_populates="custom_fields")
    settings_field = relationship("SettingsField", back_populates="values")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(1024), nullable=False)
    original_name = Column(String(255), nullable=True)
    content_type = Column(String(128), nullable=True)
    size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="attachments")
