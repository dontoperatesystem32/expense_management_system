from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from passlib.context import CryptContext
from pydantic import BaseModel

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Base SQL Model
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    disabled: bool = False

# Database model
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

    expenses: list["Expense"] = Relationship(back_populates="owner")

# Pydantic model for API responses
class UserRead(UserBase):
    id: int

# Model for creating new users
class UserCreate(SQLModel):
    username: str
    password: str

# Expense models
class ExpenseBase(SQLModel):
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=3, max_length=255)
    category: str = Field(..., min_length=3, max_length=100)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    owner: Optional[User] = Relationship(back_populates="expenses")

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseRead(ExpenseBase):
    id: int
    owner_id: int

# Authentication models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None