from pydantic import BaseModel, Field
from datetime import datetime

class DocumentModel(BaseModel):
    filename: str
    path: str
    recognized_text: str
    file_hash: str
    folder_id: str
    created_at: datetime
    custom_fields: dict = Field(default_factory=dict)
