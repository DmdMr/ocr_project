from pydantic import BaseModel
from datetime import datetime

class DocumentModel(BaseModel):
    filename: str
    path: str
    recognized_text: str
    file_hash: str
    created_at: datetime


