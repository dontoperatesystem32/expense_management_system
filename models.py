from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid

# Expense Model
class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Auto-generate unique ID
    amount: float = Field(..., gt=0, description="Expense amount")
    description: str = Field(..., min_length=3, max_length=255, description="Expense description")
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 formatted date")
    category: str = Field(..., min_length=3, max_length=100, description="Expense category")
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Last updated timestamp")


# in-memory storage
expenses_db = []