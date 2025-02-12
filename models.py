from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid
from passlib.context import CryptContext


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None



# Expense Model
class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0, description="Expense amount")
    description: str = Field(..., min_length=3, max_length=255, description="Expense description")
    category: str = Field(..., min_length=3, max_length=100, description="Expense category")

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    owner: str  # Add owner field


class User(BaseModel):
    username: str
    disabled: bool | None = None
    hashed_password: str


class UserInDB(User):
    hashed_password: str

class UserDTO(BaseModel):
    username: str
    password: str


#test user

# salam = User(username="salam", disabled = False, hashed_password = "$2b$12$pljfyPgewC.eA8QneDpwI.K4FOTuRpxPFq142A5O7ccBfBFSQV1rK")


# in-memory storage
expenses_db = []
users_db = []