from datetime import datetime, UTC
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel, field_validator
from sqlmodel import Field, Relationship, SQLModel

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
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", gt=0)
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    recurrence_rule: Optional[str] = Field(default=None, description="Recurrence rule (e.g., 'daily', 'monthly', 'yearly')")
    recurrence_start_date: Optional[datetime] = Field(default=None, description="Start date for recurrence")



class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

    owner: Optional[User] = Relationship(back_populates="expenses")


class ExpenseCreate(ExpenseBase):
    pass
    @field_validator('recurrence_rule')
    def recurrence_rule_validation(cls, value: Optional[str]):
        if value not in [None, 'daily', 'weekly', 'monthly', 'yearly']:
           raise ValueError("recurrence_rule must be one of: 'daily', 'weekly', 'monthly', 'yearly', or None")
        return value
    @field_validator('recurrence_start_date')
    def recurrence_start_date_required(cls, recurrence_start_date: Optional[datetime], values):
        if values.get('recurrence_rule') is not None and recurrence_start_date is None:
            raise ValueError("recurrence_start_date required when rec rule is set")
 


class ExpenseRead(ExpenseBase):
    id: int
    owner_id: int

class CategoryBase(SQLModel):
    description: str = Field(..., min_length=3, max_length=255)

class Category(CategoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int

# Authentication models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
