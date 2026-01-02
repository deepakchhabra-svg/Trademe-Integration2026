from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    utc: datetime
    db: str | None = None
    db_error: str | None = None

class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
