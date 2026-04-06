from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FolderModel(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    is_system: bool = False
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str] = None
    created_by_username: Optional[str] = None
